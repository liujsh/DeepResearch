"""Chroma storage layer for memory system."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from memory.models import MemoryMetadata, SearchResult

logger = logging.getLogger(__name__)

COLLECTION_NAME = "research_memories"

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class ChromaStorage:
    """Chroma 向量存储抽象"""

    def __init__(
        self,
        persist_directory: str = "./data/chroma",
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    ):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        self.embedding_model = embedding_model

        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        """获取或创建 collection"""
        try:
            collection = self.client.get_collection(COLLECTION_NAME)
            logger.info(f"Loaded existing collection: {COLLECTION_NAME}")
        except Exception:
            logger.info(f"Creating new collection: {COLLECTION_NAME}")
            collection = self.client.create_collection(
                name=COLLECTION_NAME,
                metadata={"description": "DeepResearch memory storage"},
            )

        return collection

    def _create_embedding_function(self):
        """创建 embedding 函数"""
        if self.embedding_model.startswith("sentence-transformers"):
            try:
                from chromadb.utils.embedding_functions import (
                    SentenceTransformerEmbeddingFunction,
                )

                return SentenceTransformerEmbeddingFunction(
                    model_name=self.embedding_model
                )
            except ImportError:
                logger.warning(
                    "sentence-transformers not installed, using default embedding"
                )
        return None

    def add_memory(
        self,
        memory_id: str,
        content: str,
        metadata: dict,
    ) -> None:
        """添加记忆记录"""
        self.collection.upsert(
            ids=[memory_id],
            documents=[content],
            metadatas=[metadata],
        )
        logger.debug(f"Added memory: {memory_id}")

    def search(
        self,
        query: str,
        session_id: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 5,
    ) -> list[SearchResult]:
        """语义搜索"""
        where_clause = {}
        if session_id:
            where_clause["session_id"] = session_id
        if content_type:
            where_clause["content_type"] = content_type

        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where=where_clause if where_clause else None,
            include=["documents", "metadatas", "distances"],
        )

        search_results = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                search_results.append(
                    SearchResult(
                        id=results["ids"][0][i],
                        content=results["documents"][0][i],
                        metadata=MemoryMetadata(**results["metadatas"][0][i]),
                        distance=results["distances"][0][i],
                    )
                )

        return search_results

    def get_memories_by_session(self, session_id: str) -> list[SearchResult]:
        """获取会话的所有记忆"""
        results = self.collection.get(
            where={"session_id": session_id},
            include=["documents", "metadatas"],
        )

        search_results = []
        if results["ids"]:
            for i in range(len(results["ids"])):
                search_results.append(
                    SearchResult(
                        id=results["ids"][i],
                        content=results["documents"][i],
                        metadata=MemoryMetadata(**results["metadatas"][i]),
                        distance=0.0,
                    )
                )

        return search_results

    def delete_memories_by_session(self, session_id: str) -> int:
        """删除会话的所有记忆"""
        results = self.collection.get(
            where={"session_id": session_id},
            include=["metadatas"],
        )

        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            deleted_count = len(results["ids"])
            logger.info(f"Deleted {deleted_count} memories for session: {session_id}")
            return deleted_count

        return 0

    def count_memories(self, session_id: Optional[str] = None) -> int:
        """统计记忆数量"""
        if session_id:
            results = self.collection.get(where={"session_id": session_id})
            return len(results["ids"]) if results["ids"] else 0
        return self.collection.count()

    def clear_all(self) -> None:
        """清空所有记忆（危险操作）"""
        self.client.delete_collection(COLLECTION_NAME)
        self.collection = self._get_or_create_collection()
        logger.warning("Cleared all memories from collection")