"""AssessmentService tests (M6) — one per FLUJO C edge case.

In-memory fake repository, so it never touches Supabase. Async bodies run via
asyncio.run (no pytest-asyncio, matching the other service tests).
Run:
    uv run pytest tests/test_assessment_service.py
"""

import asyncio
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.core.domain.errors import (
    InterventionNotFoundError,
    StateTransitionError,
)
from app.core.domain.models import Effectiveness, Intervention
from app.core.domain.states import LifecycleState
from app.core.services.assessment_service import AssessmentService

ADV = UUID("11111111-1111-1111-1111-111111111111")
HOLD, PLOT, IVID = uuid4(), uuid4(), uuid4()
TREATED_AT = datetime(2026, 6, 15, 7, 30, tzinfo=timezone.utc)
ASSESSED_ON = date(2026, 6, 29)


def _executed(**overrides) -> Intervention:
    base = dict(
        transaction_id=uuid4(),
        lifecycle_state=LifecycleState.EXECUTED,
        advisor_id=ADV,
        holding_id=HOLD,
        plot_id=PLOT,
        product_registration_number="ES-1",
        treatment_date=TREATED_AT,
        applied_dose=1.0,
        target_pest="araña roja",
        id=IVID,
    )
    base.update(overrides)
    return Intervention(**base)


class FakeRepo:
    """Only the methods AssessmentService.assess touches."""

    def __init__(self, intervention: Intervention | None):
        self._intervention = intervention
        self.updated: Intervention | None = None

    async def get_intervention(self, intervention_id, advisor_id):
        return self._intervention

    async def update_intervention(self, intervention):
        self.updated = intervention
        return intervention


def _assess(repo, *, effectiveness=Effectiveness.GOOD, notes=None, **kwargs):
    service = AssessmentService(repo)
    return asyncio.run(
        service.assess(
            intervention_id=IVID,
            advisor_id=ADV,
            effectiveness=effectiveness,
            effectiveness_date=ASSESSED_ON,
            effectiveness_notes=notes,
            **kwargs,
        )
    )


def test_assess_promotes_executed_to_assessed():
    repo = FakeRepo(_executed())
    result = _assess(repo, effectiveness=Effectiveness.GOOD, notes="La plaga remitió")

    assert result.lifecycle_state is LifecycleState.ASSESSED
    assert result.effectiveness is Effectiveness.GOOD
    assert result.effectiveness_date == ASSESSED_ON
    assert result.effectiveness_notes == "La plaga remitió"
    assert repo.updated is result  # persisted via update_intervention


def test_assess_blank_notes_stored_as_none():
    # An empty/whitespace reason is not a real note -> normalised to None.
    repo = FakeRepo(_executed())
    result = _assess(repo, notes="   ")
    assert result.effectiveness_notes is None


def test_assess_rejects_non_executed_state():
    # A prescription cannot be assessed before it is executed (no skipping).
    repo = FakeRepo(_executed(lifecycle_state=LifecycleState.PRESCRIBED))
    with pytest.raises(StateTransitionError):
        _assess(repo)
    assert repo.updated is None  # nothing persisted


def test_assess_rejects_double_assessment():
    # An already-assessed record is terminal -> cannot be assessed again.
    repo = FakeRepo(_executed(lifecycle_state=LifecycleState.ASSESSED))
    with pytest.raises(StateTransitionError):
        _assess(repo)
    assert repo.updated is None


def test_assess_unknown_intervention_is_not_found():
    repo = FakeRepo(None)
    with pytest.raises(InterventionNotFoundError):
        _assess(repo)
