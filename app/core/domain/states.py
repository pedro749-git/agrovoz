"""Intervention lifecycle state machine (spec §2).

Legal records never move backwards: corrections are a new intervention plus
a soft-delete of the old one.
"""

from enum import StrEnum

from app.core.domain.errors import StateTransitionError


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
