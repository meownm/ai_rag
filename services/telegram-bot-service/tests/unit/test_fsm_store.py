from telegram_ui.fsm import InMemoryConversationStore, RedisConversationStore
from telegram_ui.models import BotState


class FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex=None):
        self.data[key] = value


def test_inmemory_prevents_concurrent_processing():
    store = InMemoryConversationStore()
    store.get_or_create(1)

    assert store.try_begin_processing(1) is True
    assert store.try_begin_processing(1) is False
    store.finish_processing(1)
    assert store.try_begin_processing(1) is True


def test_redis_store_persists_state_and_processing_flag():
    redis = FakeRedis()
    store = RedisConversationStore(redis)

    context = store.get_or_create(42, debug_default=True)
    assert context.debug_enabled is True

    store.update(42, lambda c: setattr(c, "state", BotState.AWAITING_QUESTION))
    restored = store.get_or_create(42)
    assert restored.state == BotState.AWAITING_QUESTION

    assert store.try_begin_processing(42) is True
    assert store.try_begin_processing(42) is False
    store.finish_processing(42)
    assert store.try_begin_processing(42) is True
