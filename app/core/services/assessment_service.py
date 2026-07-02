"""FLUJO C — effectiveness assessment (M6, Phase 4).

An EXECUTED intervention -> ASSESSED with how well the treatment worked, the
date the advisor judged it, and an optional dictated reason. Pure orchestration
over the Repository port; mirrors ExecutionService (FLUJO B). It RAISES typed
domain errors and RETURNS the updated intervention; the inbound adapter decides
how to surface that.
"""

import logging
from datetime import date
from uuid import UUID

from app.core.domain.errors import InterventionNotFoundError
from app.core.domain.models import Effectiveness, Intervention
from app.core.domain.states import LifecycleState, transition
from app.core.ports.repository import Repository

logger = logging.getLogger(__name__)


class AssessmentService:
    """Records a treatment's effectiveness (Phase 4)."""

    def __init__(self, repository: Repository) -> None:
        self._repo = repository

    async def assess(
        self,
        *,
        intervention_id: UUID,
        advisor_id: UUID,
        effectiveness: Effectiveness,
        effectiveness_date: date,
        effectiveness_notes: str | None = None,
    ) -> Intervention:
        """Assess an EXECUTED intervention's effectiveness -> ASSESSED.

        ``effectiveness_date`` is when the advisor judged the result — the PWA
        prefills it with the device date (editable), never the server clock (the
        assessment happens days after the treatment). ``effectiveness_notes`` is
        an optional free-text reason the advisor dictates by voice.
        """
        # Load scoped to the advisor: requesting someone else's record is an
        # indistinguishable 404 (you cannot probe what is not yours).
        intervention = await self._repo.get_intervention(intervention_id, advisor_id)
        if intervention is None:
            raise InterventionNotFoundError("No encuentro ese registro.")

        # State gate: only EXECUTED -> ASSESSED. Anything else (still prescribed,
        # already assessed, an observation) raises StateTransitionError -> 422.
        # A double assess is therefore rejected here, no idempotency key needed.
        transition(intervention, LifecycleState.ASSESSED)

        intervention.effectiveness = effectiveness
        intervention.effectiveness_date = effectiveness_date
        # A blank/whitespace reason is not a real note -> store NULL, not "".
        intervention.effectiveness_notes = (effectiveness_notes or "").strip() or None
        return await self._repo.update_intervention(intervention)
