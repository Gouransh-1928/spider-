from spider.memory.store import MemoryStore


class MemoryManager:
    def __init__(self, store: MemoryStore | None = None) -> None:
        self.store = store or MemoryStore()

    def build_context(
        self,
        conversation_id: int,
        query: str,
    ) -> str:
        recent = self.store.get_recent_messages(
            conversation_id=conversation_id,
            limit=12,
        )

        memories = self.store.search_memories(
            query=query,
            limit=5,
        )

        sections: list[str] = []

        if memories:
            memory_text = "\n".join(
                f"- {item['content']}"
                for item in memories
            )
            sections.append(
                "RELEVANT LONG-TERM MEMORY:\n"
                + memory_text
            )

        if recent:
            recent_text = "\n".join(
                f"{item['role']}: {item['content']}"
                for item in recent
            )
            sections.append(
                "RECENT CONVERSATION:\n"
                + recent_text
            )

        context = "\n\n".join(sections)

        # Hard safety bound for token-efficient context.
        return context[:6000]