"""FLUJO A — registration pipeline (M2).

Audio -> transcription -> extracted JSON -> legal validation -> Supabase row.
Depends only on ports (Transcriber, Extractor, Repository), so it is transport
agnostic: the Telegram webhook today and the PWA tomorrow call the same method.

Notification is intentionally NOT done here — how to answer is transport
specific (a Telegram message vs an HTTP 422 JSON). The pipeline RAISES typed
domain errors and RETURNS the persisted intervention; the inbound adapter
decides how to surface that.
"""

from datetime import datetime, timedelta
from uuid import UUID

from app.core.domain.errors import (
    DomainError,
    EquipmentNotFoundError,
    MissingFieldError,
    PlotNotFoundError,
    ProductError,
)
from app.core.domain.models import Equipment, Intervention, Plot, Product
from app.core.domain.schemas import ExtractedFields
from app.core.domain.states import LifecycleState, validate_transition
from app.core.ports.extractor import Extractor
from app.core.ports.repository import Repository
from app.core.ports.transcriber import Transcriber
from app.core.services.validation_service import validate_registration

# The LLM classifies the audio; we map its type to the lifecycle state.
# A direct EXECUTION collapses PRESCRIBED+EXECUTED into one stored EXECUTED row.
_RECORD_TYPE_TO_STATE = {
    "OBSERVATION": LifecycleState.OBSERVATION,
    "PRESCRIPTION": LifecycleState.PRESCRIBED,
    "EXECUTION": LifecycleState.EXECUTED,
}


class RegistrationPipeline:
    def __init__(
        self,
        transcriber: Transcriber,
        extractor: Extractor,
        repository: Repository,
    ) -> None:
        self._transcriber = transcriber
        self._extractor = extractor
        self._repo = repository

    async def register(
        self,
        *,
        audio: bytes,
        advisor_id: UUID,
        transaction_id: UUID,
        device_timestamp: datetime,
    ) -> Intervention:
        # 1. Idempotency (hard rule 3): a retry returns the existing row.
        existing = await self._repo.get_intervention_by_transaction_id(transaction_id)
        if existing is not None:
            return existing

        # 2. The advisor must exist and be ACTIVE (FLUJO A step 2).
        advisor = await self._repo.get_advisor(advisor_id)
        if advisor is None or advisor.account_status != "ACTIVE":
            raise DomainError("La cuenta del asesor no está activa.")

        # 3. Transcribe + extract (LLM output validated by ExtractedFields).
        transcription = await self._transcriber.transcribe(audio)
        fields = await self._extractor.extract(transcription)

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
            equipment = await self._repo.get_equipment_by_alias(
                advisor_id, fields.equipment_alias
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
        return await self._repo.save_intervention(intervention)

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
        if product.pre_harvest_interval_days is not None:
            intervention.earliest_harvest_date = device_timestamp.date() + timedelta(
                days=product.pre_harvest_interval_days
            )
        return intervention
