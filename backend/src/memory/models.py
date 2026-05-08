"""Memory system data models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class MemoryMetadata(BaseModel):
    """记忆记录的元数据"""

    session_id: str = Field(..., description="所属会话 ID")
    session_topic: str = Field(..., description="会话主题/研究话题")

    content_type: Literal[
        "task_summary",
        "research_finding",
        "user_query",
        "agent_response",
        "report_section",
        "report",
    ] = Field(..., description="内容类型")

    task_id: Optional[str] = Field(default=None, description="关联的任务 ID")
    task_title: Optional[str] = Field(default=None, description="关联的任务标题")

    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    source: str = Field(default="agent", description="来源标记")


class MemoryRecord(BaseModel):
    """记忆记录向量存储结构"""

    id: str = Field(default_factory=lambda: f"mem_{uuid4().hex[:8]}", description="记忆记录 ID")
    content: str = Field(..., description="文档内容")
    metadata: MemoryMetadata = Field(..., description="元数据")

    def to_chroma_format(self) -> dict:
        """转换为 Chroma 格式"""
        return {
            "id": self.id,
            "document": self.content,
            "metadata": self.metadata.model_dump(),
        }

    @classmethod
    def from_chroma_result(
        cls, chroma_id: str, document: str, metadata: dict, distance: float
    ) -> "MemoryRecord":
        """从 Chroma 结果创建"""
        return cls(
            id=chroma_id,
            content=document,
            metadata=MemoryMetadata(**metadata),
        )


class ResearchSession(BaseModel):
    """研究会话"""

    id: str = Field(default_factory=lambda: f"sess_{uuid4().hex[:8]}", description="会话 ID")
    topic: str = Field(..., description="研究主题")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    status: Literal["active", "completed", "failed"] = Field(default="active")

    task_count: int = Field(default=0, description="任务数量")
    memory_count: int = Field(default=0, description="记忆记录数量")
    summary: Optional[str] = Field(default=None, description="会话摘要")


class SearchResult(BaseModel):
    """搜索结果"""

    id: str
    content: str
    metadata: MemoryMetadata
    distance: float


class SearchResponse(BaseModel):
    """搜索响应"""

    results: list[SearchResult]
    total: int


class SessionListResponse(BaseModel):
    """会话列表响应"""

    sessions: list[ResearchSession]
    total: int
    limit: int
    offset: int


class SessionDetailResponse(BaseModel):
    """会话详情响应"""

    session: ResearchSession
    memories: list[SearchResult]


class DeleteResponse(BaseModel):
    """删除响应"""

    success: bool
    deleted_session_id: str
    deleted_memory_count: int