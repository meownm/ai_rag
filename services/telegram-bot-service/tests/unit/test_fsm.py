from telegram_ui.fsm import InvalidTransitionError, transition
from telegram_ui.models import BotState, ConversationContext


def test_valid_transition_path():
    context = ConversationContext(user_id=1)
    transition(context, BotState.AWAITING_QUESTION)
    transition(context, BotState.PROCESSING)
    transition(context, BotState.ANSWER)
    assert context.state == BotState.ANSWER


def test_invalid_transition_rejected():
    context = ConversationContext(user_id=1)
    try:
        transition(context, BotState.ANSWER)
    except InvalidTransitionError as error:
        assert "Invalid transition" in str(error)
    else:
        raise AssertionError("expected InvalidTransitionError")
