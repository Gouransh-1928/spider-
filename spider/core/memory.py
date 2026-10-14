"""
SPIDER — Persistent Memory
Uses ChromaDB for long-term vector memory across sessions.
"""
import datetime
import uuid
from typing import List, Optional, Dict, Any

import chromadb
from chromadb.config import Settings
from loguru import logger
from sentence_transformers import SentenceTransformer

from config.loader import CONFIG


class SpiderMemory:
    """
    Long-term persistent memory for SPIDER using ChromaDB.
    Stores conversations, user preferences, tasks, and facts.
    """

    def __init__(self):
        db_path = CONFIG["memory"]["db_path"]
        collection_name = CONFIG["memory"]["collection_name"]
        embedding_model = CONFIG["memory"]["embedding_model"]

        logger.info(f"Initializing memory at: {db_path}")
        
        # Init ChromaDB (persistent local storage)
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Load sentence transformer for embeddings
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedder = SentenceTransformer(embedding_model)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        
        logger.info(f"Memory ready. Documents stored: {self.collection.count()}")

    def remember(
        self,
        text: str,
        category: str = "conversation",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a new memory.
        Categories: 'conversation', 'preference', 'task', 'fact', 'file'
        Returns the memory ID.
        """
        mem_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()

        doc_metadata = {
            "category": category,
            "timestamp": timestamp,
            **(metadata or {}),
        }

        # Embed and store
        embedding = self.embedder.encode(text).tolist()
        self.collection.add(
            ids=[mem_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[doc_metadata],
        )

        logger.debug(f"Memory stored [{category}]: {text[:80]}...")
        return mem_id

    def recall(
        self,
        query: str,
        n_results: int = 5,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Recall memories relevant to a query.
        Returns list of {text, score, category, timestamp} dicts.
        """
        if self.collection.count() == 0:
            return []

        query_embedding = self.embedder.encode(query).tolist()
        
        where_filter = {"category": category} if category else None
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, self.collection.count()),
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        memories = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            memories.append({
                "text": doc,
                "score": 1 - dist,  # Convert distance to similarity
                "category": meta.get("category", "unknown"),
                "timestamp": meta.get("timestamp", ""),
                "metadata": meta,
            })

        return memories

    def format_context_for_llm(self, query: str, n: int = 5) -> str:
        """
        Retrieve relevant memories and format them as context for the LLM.
        """
        memories = self.recall(query, n_results=n)
        if not memories:
            return ""

        lines = ["Relevant memories from past conversations:"]
        for mem in memories:
            ts = mem["timestamp"][:10] if mem["timestamp"] else "unknown date"
            lines.append(f"- [{ts}] {mem['text']}")

        return "\n".join(lines)

    def remember_conversation(self, user_msg: str, spider_reply: str) -> None:
        """Store a conversation turn in memory."""
        combined = f"User said: {user_msg}\nSPIDER replied: {spider_reply}"
        self.remember(combined, category="conversation")

    def get_stats(self) -> Dict[str, Any]:
        """Return memory statistics."""
        return {
            "total_memories": self.collection.count(),
        }
