from pathlib import Path
from tempfile import TemporaryDirectory

from spider.memory.store import MemoryStore
from spider.memory.manager import MemoryManager


def test_memory_can_be_saved_and_found():
    with TemporaryDirectory() as temp:
        db = MemoryStore(Path(temp) / "test.db")

        db.add_memory(
            "User prefers Python for SPIDER",
            memory_type="preference",
            importance=3,
        )

        results = db.search_memories("Python SPIDER")

        assert results
        assert "Python" in results[0]["content"]


def test_recent_messages_are_retrieved():
    with TemporaryDirectory() as temp:
        db = MemoryStore(Path(temp) / "test.db")

        conversation_id = db.create_conversation()

        db.add_message(
            conversation_id,
            "user",
            "Hello SPIDER",
        )

        db.add_message(
            conversation_id,
            "assistant",
            "Hello. I am online.",
        )

        messages = db.get_recent_messages(
            conversation_id,
            limit=12,
        )

        assert len(messages) == 2
        assert messages[0]["role"] == "user"


def test_context_is_bounded():
    with TemporaryDirectory() as temp:
        db = MemoryStore(Path(temp) / "test.db")

        conversation_id = db.create_conversation()

        db.add_message(
            conversation_id,
            "user",
            "A" * 10000,
        )

        manager = MemoryManager(db)

        context = manager.build_context(
            conversation_id,
            "A",
        )

        assert len(context) <= 6000