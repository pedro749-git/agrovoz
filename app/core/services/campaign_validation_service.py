"""FLUJO C — campaign validation (M7, Phase 5).

The advisor signs their conformity over a holding's interventions, mandatory
twice per campaign (MID_CYCLE mid-cycle + FINAL at the close). Pure orchestration
over the Repository port; RAISES typed domain errors and RETURNS the saved
Validation — the inbound adapter decides how to surface that.

Named ``campaign_validation_service`` (not ``validation_service``, which the spec
suggests) because that name is already the LEGAL validation of the pipeline
(dose/area); see the decisions log.
"""

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
from app.core.domain.models import Validation, ValidationType
from app.core.ports.repository import Repository

logger = logging.getLogger(__name__)


class CampaignValidationService:
    """Signs a holding's campaign validation (Phase 5)."""

    def __init__(self, repository: Repository) -> None:
        self._repo = repository

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

        # 6. Build and persist the signed record.
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
        return await self._repo.save_validation(validation)
