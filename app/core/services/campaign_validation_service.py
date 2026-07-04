"""FLUJO C — campaign validation (M7, Phase 5).

The advisor signs their conformity over a holding's interventions, mandatory
twice per campaign (MID_CYCLE mid-cycle + FINAL at the close). Pure orchestration
over the Repository port; RAISES typed domain errors and RETURNS the saved
Validation — the inbound adapter decides how to surface that.

Named ``campaign_validation_service`` (not ``validation_service``, which the spec
suggests) because that name is already the LEGAL validation of the pipeline
(dose/area); see the decisions log.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from uuid import UUID

from app.core.domain.calculations import campaign_start
from app.core.domain.errors import (
    HoldingNotFoundError,
    InvalidCampaignError,
    RemarksRequiredError,
    ValidationExistsError,
)
from app.core.domain.models import Advisor, Holding, Validation, ValidationType
from app.core.ports.pdf_generator import PdfGenerator
from app.core.ports.repository import Repository
from app.core.ports.storage import Storage

logger = logging.getLogger(__name__)


class CampaignValidationService:
    """Signs a holding's campaign validation (Phase 5)."""

    def __init__(
        self,
        repository: Repository,
        pdf_generator: PdfGenerator,
        storage: Storage,
    ) -> None:
        self._repo = repository
        self._pdf = pdf_generator
        self._storage = storage

    async def validate_campaign(
        self,
        *,
        holding_id: UUID,
        advisor_id: UUID,
        campaign: str,
        validation_type: ValidationType,
        conformity: bool,
        validation_date: datetime,
        remarks: str | None = None,
    ) -> Validation:
        """Sign a campaign validation over a holding's interventions.

        ``validation_date`` is the device timestamp (the advisor may sign
        offline). The period covered runs from the campaign start (or the day
        after the previous validation) up to that date; the service counts the
        interventions in it and stores the count on the record.
        """
        # 1. Authorization: the holding must be managed by this advisor. A holding
        # that is not yours is an indistinguishable 404 (you cannot probe it).
        holding = await self._repo.get_holding(holding_id)
        if holding is None or holding.advisor_id != advisor_id:
            raise HoldingNotFoundError("No encuentro esa explotación.")

        # 2. A non-conform validation must explain why.
        remarks = (remarks or "").strip() or None
        if not conformity and remarks is None:
            raise RemarksRequiredError(
                "Una validación no conforme debe indicar el motivo."
            )

        # 3. Reject a duplicate type — a campaign is signed once per type
        # (DB backs it with UNIQUE(holding, campaign, type)).
        existing = await self._repo.list_validations(holding_id, campaign)
        if any(v.type == validation_type for v in existing):
            raise ValidationExistsError(
                f"Esta campaña ya tiene una validación «{validation_type.value}»."
            )

        # 4. Period covered: from the day after the latest previous validation,
        # or from the campaign start if this is the first one. The end is the
        # signing date (civil day).
        if existing:
            period_start = max(v.period_end for v in existing) + timedelta(days=1)
        else:
            try:
                period_start = campaign_start(campaign)
            except ValueError as exc:
                raise InvalidCampaignError(
                    f"Campaña «{campaign}» no válida (se espera un año, p. ej. 2026)."
                ) from exc
        period_end = validation_date.date()

        # 5. Count the interventions the validation covers.
        interventions = await self._repo.list_interventions_in_period(
            holding_id, start=period_start, end=period_end
        )

        # 6. Build the signed record.
        validation = Validation(
            advisor_id=advisor_id,
            holding_id=holding_id,
            campaign=campaign,
            type=validation_type,
            validation_date=validation_date,
            conformity=conformity,
            period_start=period_start,
            period_end=period_end,
            intervention_count=len(interventions),
            remarks=remarks,
        )

        # 7. Render the signed PDF and upload it, so the key is set on the single
        # INSERT. Best-effort: a render/OSS failure must NOT block the signing —
        # the PDF is deterministic and can be regenerated from the row later.
        advisor = await self._repo.get_advisor(advisor_id)
        validation.validation_pdf_key = await self._store_validation_pdf(
            validation, advisor, holding
        )
        return await self._repo.save_validation(validation)

    async def _store_validation_pdf(
        self, validation: Validation, advisor: Advisor | None, holding: Holding
    ) -> str | None:
        """Build the validation PDF and upload it to OSS; return its key (or None
        on any failure — best-effort, mirrors the prescription PDF in the pipeline).

        The key is deterministic and known before the INSERT
        (``validations/{holding}_{campaign}_{type}.pdf``); it is unique because
        the DB enforces UNIQUE(holding, campaign, type). That lets us set the key
        on the single INSERT instead of saving then updating.
        """
        if advisor is None:
            # The advisor is authenticated and owns the holding, so this should
            # not happen; if it does, sign without a PDF rather than block.
            logger.warning(
                "Advisor %s not found; saving validation without PDF", validation.advisor_id
            )
            return None
        try:
            # PDF building is pure CPU (no I/O) -> run off the event loop.
            pdf = await asyncio.to_thread(
                self._pdf.generate_validation,
                validation=validation,
                advisor=advisor,
                holding=holding,
            )
            key = (
                f"validations/{validation.holding_id}_"
                f"{validation.campaign}_{validation.type.value}.pdf"
            )
            await self._storage.upload(data=pdf, key=key, content_type="application/pdf")
            return key
        except Exception:
            # PDF render OR OSS upload failed: sign the record anyway. The
            # traceback tells you which; the PDF can be regenerated from the row.
            logger.exception("Validation PDF render/upload failed; saving without PDF")
            return None
