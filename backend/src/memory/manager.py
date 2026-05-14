"""Memory manager - core class for memory system."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from ..config import Configuration
from .models import (
    MemoryMetadata,
    ResearchSession,
    SearchResult,
)
from .storage import ChromaStorage, DEFAULT_EMBEDDING_MODEL

logger = logging.getLogger(__name__)


class MemoryManager:
    """记忆管理器 - 提供记忆存储和检索功能"""

    def __init__(self, config: Optional[Configuration] = None, storage_type: str = "chroma"):
        if config is None:
            config = Configuration.from_env()

        self.config = config

        chroma_dir = getattr(config, "chroma_persist_directory", "./data/chroma")
        embedding_model = getattr(
            config, "embedding_model", DEFAULT_EMBEDDING_MODEL
        )

        # 根据 storage_type 创建不同的存储实例
        if storage_type == "qdrant":
            from .storage import QdrantStorage
            self.storage = QdrantStorage(
                embedding_model=embedding_model,
            )
            # Qdrant 使用不同的目录
            self.sessions_file = Path("./data/qdrant") / "sessions.json"
        else:
            from .storage import ChromaStorage
            self.storage = ChromaStorage(
                persist_directory=chroma_dir,
                embedding_model=embedding_model,
            )
            self.sessions_file = Path(chroma_dir) / "sessions.json"

        self._sessions = self._load_sessions()

    def _load_sessions(self) -> dict[str, ResearchSession]:
        """加载会话数据"""
        if self.sessions_file.exists():
            try:
                data = json.loads(self.sessions_file.read_text(encoding="utf-8"))
                return {k: ResearchSession(**v) for k, v in data.items()}
            except Exception as e:
                logger.warning(f"Failed to load sessions: {e}")
        return {}

    def _save_sessions(self) -> None:
        """保存会话数据"""
        try:
            self.sessions_file.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v.model_dump() for k, v in self._sessions.items()}
            self.sessions_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")

    def create_session(self, topic: str) -> ResearchSession:
        """创建新会话"""
        session = ResearchSession(topic=topic)
        self._sessions[session.id] = session
        self._save_sessions()
        logger.info(f"Created new session: {session.id} - {topic}")
        return session

    def update_session(
        self,
        session_id: str,
        status: Optional[str] = None,
        summary: Optional[str] = None,
        task_count: Optional[int] = None,
    ) -> ResearchSession:
        """更新会话"""
        if session_id not in self._sessions:
            raise ValueError(f"Session not found: {session_id}")

        session = self._sessions[session_id]
        session.updated_at = datetime.utcnow().isoformat() + "Z"

        if status:
            session.status = status
        if summary:
            session.summary = summary
        if task_count is not None:
            session.task_count = task_count

        session.memory_count = self.storage.count_memories(session_id)

        self._save_sessions()
        logger.info(f"Updated session: {session_id}")
        return session

    def delete_session(self, session_id: str) -> int:
        """删除会话及其所有记忆"""
        if session_id not in self._sessions:
            return 0

        deleted_count = self.storage.delete_memories_by_session(session_id)
        del self._sessions[session_id]
        self._save_sessions()

        logger.info(f"Deleted session: {session_id}, memories: {deleted_count}")
        return deleted_count

    def get_session(self, session_id: str) -> Optional[ResearchSession]:
        """获取会话"""
        return self._sessions.get(session_id)

    def list_sessions(
        self,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ResearchSession], int]:
        """列出会话"""
        sessions = list(self._sessions.values())

        if status:
            sessions = [s for s in sessions if s.status == status]

        sessions.sort(key=lambda x: x.created_at, reverse=True)

        total = len(sessions)
        paginated = sessions[offset : offset + limit]

        return paginated, total

    def add_memory(
        self,
        session_id: str,
        session_topic: str,
        content: str,
        content_type: str,
        task_id: Optional[str] = None,
        task_title: Optional[str] = None,
        source: str = "agent",
        metadata: Optional[dict] = None,
    ) -> str:
        """添加记忆记录"""
        memory_id = f"mem_{uuid4().hex[:8]}"
        now = datetime.utcnow().isoformat() + "Z"

        metadata = metadata or {}
        metadata.update({
            "session_id": session_id,
            "session_topic": session_topic,
            "content_type": content_type,
            "task_id": task_id or "",
            "task_title": task_title or "",
            "created_at": now,
            "updated_at": now,
            "source": source,
        })

        self.storage.add_memory(
            memory_id=memory_id,
            content=content,
            metadata=metadata,
        )

        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.memory_count = self.storage.count_memories(session_id)
            session.updated_at = now
            self._save_sessions()

        logger.debug(f"Added memory to session {session_id}: {content_type}")
        return memory_id

    def search(
        self,
        query: str,
        session_id: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 5,
    ) -> list[SearchResult]:
        """语义搜索记忆"""
        return self.storage.search(
            query=query,
            session_id=session_id,
            content_type=content_type,
            limit=limit,
        )

    def get_session_memories(
        self, session_id: str
    ) -> list[SearchResult]:
        """获取会话的所有记忆"""
        return self.storage.get_memories_by_session(session_id)

    def get_related_memories(
        self, query: str, limit: int = 3
    ) -> list[SearchResult]:
        """获取与查询相关的历史记忆（用于上下文增强）"""
        return self.search(query=query, limit=limit)


def create_memory_manager(
    config: Optional[Configuration] = None,
    storage_type: Optional[str] = None,
) -> MemoryManager:
    """工厂函数：创建 MemoryManager实例"""
    # 从环境变量读取存储类型，默认使用 chroma
    if storage_type is None:
        storage_type = os.environ.get("STORAGE_TYPE", "chroma")

    return MemoryManager(config, storage_type=storage_type)