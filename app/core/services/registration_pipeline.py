"""FLUJO A — registration pipeline (M2; split into preview/commit in M8).

Audio -> transcription -> extracted JSON -> legal validation -> Supabase row.
Depends only on ports (Transcriber, Extractor, Repository), so it is transport
agnostic: the PWA REST API calls these same methods.

Split into two phases so the advisor REVIEWS the extracted fields before they
reach the legal record (hard rule 4 — LLM output is untrusted):
- ``preview``: transcribe + extract, NO DB write. Returns the fields to edit.
- ``commit``: resolve + VALIDATE (on the edited fields) + build + PDF + persist.

The pipeline RAISES typed domain errors and RETURNS the persisted intervention;
the inbound adapter decides how to surface that (an HTTP 422 JSON for the PWA).
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.core.domain.calculations import earliest_harvest_date
from app.core.domain.errors import (
    DomainError,
    EquipmentNotFoundError,
    MissingFieldError,
    PlotNotFoundError,
    ProductError,
)
from app.core.domain.models import Advisor, Equipment, Intervention, Plot, Product
from app.core.domain.schemas import ExtractedFields
from app.core.domain.states import LifecycleState, validate_transition
from app.core.ports.extractor import Extractor
from app.core.ports.pdf_generator import PdfGenerator
from app.core.ports.repository import Repository
from app.core.ports.storage import Storage
from app.core.ports.transcriber import Transcriber
from app.core.services.timing import timed
from app.core.services.validation_service import validate_registration

logger = logging.getLogger(__name__)

# The LLM classifies the audio; we map its type to the lifecycle state.
# A direct EXECUTION collapses PRESCRIBED+EXECUTED into one stored EXECUTED row.
_RECORD_TYPE_TO_STATE = {
    "OBSERVATION": LifecycleState.OBSERVATION,
    "PRESCRIPTION": LifecycleState.PRESCRIBED,
    "EXECUTION": LifecycleState.EXECUTED,
}


@dataclass(frozen=True)
class PreviewResult:
    """What ``preview`` hands back for the advisor to review before committing:
    the raw transcription (shown as "lo que dictaste") and the extracted fields
    (prefilled into the editable form). Nothing is persisted yet."""

    transcription: str
    fields: ExtractedFields


class RegistrationPipeline:
    def __init__(
        self,
        transcriber: Transcriber,
        extractor: Extractor,
        repository: Repository,
        pdf_generator: PdfGenerator,
        storage: Storage,
    ) -> None:
        self._transcriber = transcriber
        self._extractor = extractor
        self._repo = repository
        self._pdf = pdf_generator
        self._storage = storage

    async def preview(
        self, *, audio: bytes, advisor_id: UUID
    ) -> PreviewResult:
        """Phase 1: transcribe + extract, NO DB write. Returns the fields for the
        advisor to review/correct before ``commit`` persists them (hard rule 4)."""
        with timed("FLUJO A: preview (total)"):
            return await self._preview(audio=audio, advisor_id=advisor_id)

    async def _preview(
        self, *, audio: bytes, advisor_id: UUID
    ) -> PreviewResult:
        # The advisor must exist and be ACTIVE (FLUJO A step 2) — fail fast before
        # paying for transcription.
        advisor = await self._repo.get_advisor(advisor_id)
        if advisor is None or advisor.account_status != "ACTIVE":
            raise DomainError("La cuenta del asesor no está activa.")

        # Transcribe + extract (LLM output validated by ExtractedFields).
        # The two Qwen round-trips are the usual latency hot spot -> timed.
        with timed("FLUJO A: transcribe (Qwen audio)"):
            transcription = await self._transcriber.transcribe(audio)
        with timed("FLUJO A: extract (Qwen instruct)"):
            fields = await self._extractor.extract(transcription)

        return PreviewResult(transcription=transcription, fields=fields)

    async def commit(
        self,
        *,
        fields: ExtractedFields,
        advisor_id: UUID,
        transaction_id: UUID,
        device_timestamp: datetime,
        transcription: str,
    ) -> Intervention:
        """Phase 2: resolve + VALIDATE (on the advisor-edited fields) + build +
        PDF + persist. ``fields`` is untrusted client input (edited by hand after
        the preview), so it still passes ExtractedFields and the legal validation
        (hard rules 4/5). ``transcription`` is the ORIGINAL audio transcription,
        stored as the audit trail regardless of what the advisor edited."""
        with timed("FLUJO A: commit (total)"):
            return await self._commit(
                fields=fields,
                advisor_id=advisor_id,
                transaction_id=transaction_id,
                device_timestamp=device_timestamp,
                transcription=transcription,
            )

    async def _commit(
        self,
        *,
        fields: ExtractedFields,
        advisor_id: UUID,
        transaction_id: UUID,
        device_timestamp: datetime,
        transcription: str,
    ) -> Intervention:
        # 1. Idempotency (hard rule 3): a retry returns the existing row.
        existing = await self._repo.get_intervention_by_transaction_id(transaction_id)
        if existing is not None:
            return existing

        # 2. The advisor must exist and be ACTIVE. Re-checked here (not only in
        #    preview): commit is a separate request and is also needed for the PDF.
        advisor = await self._repo.get_advisor(advisor_id)
        if advisor is None or advisor.account_status != "ACTIVE":
            raise DomainError("La cuenta del asesor no está activa.")

        # 4. Resolve the plot (always mandatory).
        plot = await self._repo.get_plot_by_alias(advisor_id, fields.plot_alias)
        if plot is None:
            raise PlotNotFoundError(f"No encuentro la parcela «{fields.plot_alias}».")

        # 5. Resolve product + equipment for PRESCRIPTION/EXECUTION.
        product: Product | None = None
        equipment: Equipment | None = None
        if fields.record_type != "OBSERVATION":
            self._require_treatment_fields(fields)
            product = await self._repo.get_product_by_name(fields.product_name)
            if product is None:
                raise ProductError(
                    f"No encuentro el producto «{fields.product_name}» en el vademécum."
                )
            # Scoped to the plot's holding, not the advisor: the dictated plot
            # already pins the holding, so two holdings' "tractor" don't collide.
            equipment = await self._repo.get_equipment_by_alias(
                plot.holding_id, fields.equipment_alias
            )
            if equipment is None:
                raise EquipmentNotFoundError(
                    f"No encuentro el equipo «{fields.equipment_alias}»."
                )

        # 6. Legal validation BEFORE persisting (hard rule 5).
        validate_registration(fields, plot, product)

        # 7. Build the domain entity and persist it.
        intervention = self._build_intervention(
            fields=fields,
            advisor_id=advisor_id,
            plot=plot,
            product=product,
            equipment=equipment,
            transaction_id=transaction_id,
            device_timestamp=device_timestamp,
            transcription=transcription,
        )
        validate_transition(None, intervention.lifecycle_state)

        # 8. PRESCRIPTION only (spec FLUJO A): render the legal PDF and store it
        #    in OSS, keyed by transaction_id — known before the INSERT, so it is
        #    a single DB write and a retry overwrites the same object. The key is
        #    set on the entity, then persisted in one go.
        if intervention.lifecycle_state is LifecycleState.PRESCRIBED:
            intervention.prescription_pdf_key = await self._store_prescription_pdf(
                intervention=intervention,
                advisor=advisor,
                plot=plot,
                product=product,  # never None for PRESCRIPTION (step 5)
                equipment=equipment,
                transaction_id=transaction_id,
            )

        return await self._repo.save_intervention(intervention)

    async def _store_prescription_pdf(
        self,
        *,
        intervention: Intervention,
        advisor: Advisor,
        plot: Plot,
        product: Product,
        equipment: Equipment | None,
        transaction_id: UUID,
    ) -> str | None:
        """Build the prescription PDF and upload it to OSS; return its key.

        Best-effort: NEITHER a storage failure NOR a PDF-rendering bug may
        block the legal record (same principle as hard rule 8 for AEMET). The
        PDF is deterministic, so it can be regenerated from the persisted row
        later — on ANY failure we log the traceback, return None and the
        intervention is saved without a PDF key.
        """
        try:
            holding = await self._repo.get_holding(plot.holding_id)
            if holding is None:
                logger.warning(
                    "Holding %s not found; saving prescription without PDF",
                    plot.holding_id,
                )
                return None
            # PDF building is pure CPU (no I/O) -> run off the event loop.
            with timed("FLUJO A: render prescription PDF"):
                pdf = await asyncio.to_thread(
                    self._pdf.generate_prescription,
                    intervention=intervention,
                    advisor=advisor,
                    holding=holding,
                    plot=plot,
                    product=product,
                    equipment=equipment,
                )
            key = f"prescriptions/{transaction_id}.pdf"
            with timed("FLUJO A: upload prescription PDF (OSS)"):
                await self._storage.upload(
                    data=pdf, key=key, content_type="application/pdf"
                )
            return key
        except Exception:
            # PDF render OR OSS upload failed: save the record anyway. The
            # traceback tells you which (StorageError = OSS, otherwise a render
            # bug); the PDF can be regenerated from the row later.
            logger.exception("Prescription PDF render/upload failed; saving without PDF")
            return None

    @staticmethod
    def _require_treatment_fields(fields: ExtractedFields) -> None:
        """PRESCRIPTION/EXECUTION need product, dose, pest and equipment."""
        missing = [
            name
            for name, value in (
                ("product_name", fields.product_name),
                ("dose", fields.dose),
                ("target_pest", fields.target_pest),
                ("equipment_alias", fields.equipment_alias),
            )
            if value is None
        ]
        if missing:
            raise MissingFieldError(
                "Faltan datos obligatorios en el audio: " + ", ".join(missing) + "."
            )

    def _build_intervention(
        self,
        *,
        fields: ExtractedFields,
        advisor_id: UUID,
        plot: Plot,
        product: Product | None,
        equipment: Equipment | None,
        transaction_id: UUID,
        device_timestamp: datetime,
        transcription: str,
    ) -> Intervention:
        state = _RECORD_TYPE_TO_STATE[fields.record_type]

        intervention = Intervention(
            transaction_id=transaction_id,
            lifecycle_state=state,
            advisor_id=advisor_id,
            holding_id=plot.holding_id,  # records belong to the HOLDING (rule 6)
            plot_id=plot.id,
            raw_transcription=transcription,
            prompt_version=self._extractor.prompt_version,
            audit_state="VALID",
        )

        if state is LifecycleState.OBSERVATION:
            intervention.observation = fields.observation
            return intervention

        # Common to PRESCRIPTION and EXECUTION.
        intervention.product_registration_number = product.registration_number
        intervention.equipment_id = equipment.id
        intervention.target_pest = fields.target_pest
        intervention.dose_unit = fields.dose_unit or product.dose_unit
        intervention.justification = fields.justification

        if state is LifecycleState.PRESCRIBED:
            intervention.prescription_date = device_timestamp
            intervention.prescribed_dose = fields.dose
            return intervention

        # EXECUTION: the treatment is already done -> real treatment_date.
        intervention.prescription_date = device_timestamp
        intervention.prescribed_dose = fields.dose
        intervention.treatment_date = device_timestamp
        intervention.applied_dose = fields.dose
        intervention.treated_area_ha = fields.treated_area_ha
        intervention.spray_volume_l_ha = fields.spray_volume_l_ha
        intervention.operator_name = fields.operator_name
        intervention.operator_ropo = fields.operator_ropo
        intervention.earliest_harvest_date = earliest_harvest_date(
            device_timestamp, product.pre_harvest_interval_days
        )
        return intervention
