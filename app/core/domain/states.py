"""Intervention lifecycle state machine (spec §2).

Legal records never move backwards: corrections are a new intervention plus
a soft-delete of the old one.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from app.core.domain.errors import StateTransitionError

if TYPE_CHECKING:
    # Type-only import: models.py imports this module, so importing it back at
    # runtime would be a circular import. `from __future__ import annotations`
    # keeps the hint as a string, evaluated only by the type checker.
    from app.core.domain.models import Intervention


class LifecycleState(StrEnum):
    OBSERVATION = "OBSERVATION"  # terminal: GIP surveillance, no product/dose
    PRESCRIBED = "PRESCRIBED"
    EXECUTED = "EXECUTED"
    ASSESSED = "ASSESSED"  # terminal


# None = a new intervention being created from an audio. EXECUTED appears as
# an initial state because the advisor may arrive with the treatment already
# done (direct execution creates PRESCRIBED+EXECUTED in one step).
VALID_TRANSITIONS: dict[LifecycleState | None, set[LifecycleState]] = {
    None: {LifecycleState.OBSERVATION, LifecycleState.PRESCRIBED, LifecycleState.EXECUTED},
    LifecycleState.PRESCRIBED: {LifecycleState.EXECUTED},
    LifecycleState.EXECUTED: {LifecycleState.ASSESSED},
    LifecycleState.OBSERVATION: set(),
    LifecycleState.ASSESSED: set(),
}


def validate_transition(current: LifecycleState | None, new: LifecycleState) -> None:
    if new not in VALID_TRANSITIONS.get(current, set()):
        raise StateTransitionError(f"{current} → {new} not allowed")


def transition(intervention: Intervention, new: LifecycleState) -> None:
    """The single gate for changing state: check first, then mutate."""
    validate_transition(intervention.lifecycle_state, new)
    intervention.lifecycle_state = new