"""State machine tests (spec §2) — legal transitions + illegal ones.

Legal records never move backwards; a correction is a new intervention plus a
soft-delete of the old one. Run: uv run pytest tests/test_states.py
"""

import pytest

from app.core.domain.errors import StateTransitionError
from app.core.domain.states import LifecycleState as S
from app.core.domain.states import validate_transition


@pytest.mark.parametrize("new", [S.OBSERVATION, S.PRESCRIBED, S.EXECUTED])
def test_legal_initial_states(new):
    # A new audio may land directly as any of these (direct EXECUTION allowed).
    validate_transition(None, new)


@pytest.mark.parametrize("current,new", [
    (S.PRESCRIBED, S.EXECUTED),
    (S.EXECUTED, S.ASSESSED),
])
def test_legal_forward_transitions(current, new):
    validate_transition(current, new)


@pytest.mark.parametrize("current,new", [
    (S.OBSERVATION, S.PRESCRIBED),   # OBSERVATION is terminal
    (S.ASSESSED, S.EXECUTED),        # ASSESSED is terminal
    (S.EXECUTED, S.PRESCRIBED),      # backward
    (S.PRESCRIBED, S.ASSESSED),      # skips EXECUTED
    (None, S.ASSESSED),              # cannot be born ASSESSED
])
def test_illegal_transitions_raise(current, new):
    with pytest.raises(StateTransitionError):
        validate_transition(current, new)
