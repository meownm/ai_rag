import pytest

from telegram_ui.fsm import ALLOWED_TRANSITIONS, InvalidTransitionError, transition
from telegram_ui.models import BotState, ConversationContext


def test_required_state_paths_supported():
    context = ConversationContext(user_id=1)
    transition(context, BotState.AWAITING_QUESTION)
    transition(context, BotState.PROCESSING)
    transition(context, BotState.CLARIFICATION)
    transition(context, BotState.PROCESSING)
    transition(context, BotState.ANSWER)
    assert context.state == BotState.ANSWER


def test_error_transition_supported():
    context = ConversationContext(user_id=2)
    transition(context, BotState.AWAITING_QUESTION)
    transition(context, BotState.PROCESSING)
    transition(context, BotState.ERROR)
    transition(context, BotState.AWAITING_QUESTION)
    assert context.state == BotState.AWAITING_QUESTION


def test_invalid_transitions_rejected_for_all_states():
    for state in BotState:
        context = ConversationContext(user_id=3, state=state)
        allowed = ALLOWED_TRANSITIONS.get(state, set())
        for target in BotState:
            if target in allowed:
                continue
            with pytest.raises(InvalidTransitionError):
                transition(context, target)
