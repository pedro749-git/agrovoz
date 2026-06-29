"""ExecutionService tests (M5) — one per FLUJO B edge case.

In-memory fake repository, so it never touches Supabase. Async bodies run via
asyncio.run (no pytest-asyncio, matching the pipeline tests). Run:
    uv run pytest tests/test_execution_service.py
"""

import asyncio
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.core.domain.errors import (
    AreaError,
    DoseError,
    InterventionNotFoundError,
    StateTransitionError,
)
from app.core.domain.models import Holding, Intervention, Plot, Product
from app.core.domain.states import LifecycleState
from app.core.services.execution_service import ExecutionService

ADV = UUID("11111111-1111-1111-1111-111111111111")
HOLD, PLOT, IVID = uuid4(), uuid4(), uuid4()
PRESCRIBED_AT = datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc)
TREATED_AT = datetime(2026, 6, 15, 7, 30, tzinfo=timezone.utc)


def _prescribed(**overrides) -> Intervention:
    base = dict(
        transaction_id=uuid4(),
        lifecycle_state=LifecycleState.PRESCRIBED,
        advisor_id=ADV,
        holding_id=HOLD,
        plot_id=PLOT,
        product_registration_number="ES-1",
        prescription_date=PRESCRIBED_AT,
        prescribed_dose=1.0,
        target_pest="araña roja",
        id=IVID,
    )
    base.update(overrides)
    return Intervention(**base)


class FakeRepo:
    """Only the methods ExecutionService.confirm touches."""

    def __init__(self, intervention: Intervention | None):
        self._intervention = intervention
        self.updated: Intervention | None = None

    async def get_intervention(self, intervention_id, advisor_id):
        return self._intervention

    async def get_holding(self, holding_id):
        return Holding(
            advisor_id=ADV, owner_name="Pepe", owner_nif="1", rea_regepa_number="R",
            default_operator_name="Pepe Titular", default_operator_ropo="OP-1",
            id=HOLD,
        )

    async def get_plot(self, plot_id):
        return Plot(
            holding_id=HOLD, voice_alias="Finca de Pepe", crop="Limonero",
            enclosure_area_ha=5.0, sigpac_province="30", sigpac_municipality="001",
            sigpac_polygon="1", sigpac_parcel="1", sigpac_enclosure="1", id=PLOT,
        )

    async def get_product_by_registration_number(self, registration_number):
        return Product(
            registration_number=registration_number, trade_name="Abamectina",
            active_substance="abamectina", authorized=True, max_allowed_dose=1.5,
            dose_unit="L/ha", pre_harvest_interval_days=14,
        )

    async def update_intervention(self, intervention):
        self.updated = intervention
        return intervention


def _confirm(repo, **kwargs):
    service = ExecutionService(repo)
    return asyncio.run(
        service.confirm(
            intervention_id=IVID, advisor_id=ADV, treatment_date=TREATED_AT, **kwargs
        )
    )


def test_confirm_promotes_to_executed_with_defaults():
    # No real figures given -> dose falls back to prescribed, operator to the
    # holding default, harvest date = treatment_date + product PHI.
    repo = FakeRepo(_prescribed())
    result = _confirm(repo)

    assert result.lifecycle_state is LifecycleState.EXECUTED
    assert result.treatment_date == TREATED_AT
    assert result.applied_dose == 1.0  # prescribed_dose
    assert result.dose_unit == "L/ha"  # from the product
    assert result.operator_name == "Pepe Titular"  # holding default
    assert result.operator_ropo == "OP-1"
    assert result.earliest_harvest_date == date(2026, 6, 29)  # 2026-06-15 + 14d
    assert repo.updated is result  # persisted via update_intervention


def test_confirm_uses_explicit_real_values():
    repo = FakeRepo(_prescribed())
    result = _confirm(
        repo, applied_dose=1.2, treated_area_ha=3.0,
        operator_name="Juan", operator_ropo="OP-9", spray_volume_l_ha=200.0,
        delivery_note_number="ALB-2026-7",
    )

    assert result.applied_dose == 1.2
    assert result.treated_area_ha == 3.0
    assert result.operator_name == "Juan"
    assert result.operator_ropo == "OP-9"
    assert result.spray_volume_l_ha == 200.0
    assert result.delivery_note_number == "ALB-2026-7"


def test_confirm_rejects_non_prescribed_state():
    # An already-executed record cannot be confirmed again (no backward/again).
    repo = FakeRepo(_prescribed(lifecycle_state=LifecycleState.EXECUTED))
    with pytest.raises(StateTransitionError):
        _confirm(repo)
    assert repo.updated is None  # nothing persisted


def test_confirm_unknown_intervention_is_not_found():
    repo = FakeRepo(None)
    with pytest.raises(InterventionNotFoundError):
        _confirm(repo)


def test_confirm_revalidates_real_dose_over_max():
    # Real applied dose above the product's legal maximum -> DoseError, no write.
    repo = FakeRepo(_prescribed())
    with pytest.raises(DoseError):
        _confirm(repo, applied_dose=2.0)  # max_allowed_dose = 1.5
    assert repo.updated is None


def test_confirm_revalidates_real_area_over_enclosure():
    # Real treated area above the SIGPAC enclosure -> AreaError, no write.
    repo = FakeRepo(_prescribed())
    with pytest.raises(AreaError):
        _confirm(repo, treated_area_ha=10.0)  # enclosure_area_ha = 5.0
    assert repo.updated is None
