"""Memory system API routes."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..config import Configuration
from .manager import MemoryManager, create_memory_manager
from .models import (
    DeleteResponse,
    SearchResponse,
    SessionDetailResponse,
    SessionListResponse,
)

router = APIRouter()

logger = logging.getLogger(__name__)

_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """获取或创建 MemoryManager 实例"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = create_memory_manager()
    return _memory_manager


@router.get("/search", response_model=SearchResponse)
async def search_memories(
    q: str = Query(..., description="搜索查询文本"),
    session_id: Optional[str] = Query(None, description="限定在某个会话中搜索"),
    content_type: Optional[str] = Query(None, description="过滤内容类型"),
    limit: int = Query(5, ge=1, le=20, description="返回结果数量"),
) -> SearchResponse:
    """语义搜索历史记忆"""
    try:
        manager = get_memory_manager()
        results = manager.search(
            query=q,
            session_id=session_id,
            content_type=content_type,
            limit=limit,
        )
        return SearchResponse(results=results, total=len(results))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    status: Optional[str] = Query(None, description="过滤状态: active, completed, failed"),
) -> SessionListResponse:
    """列出所有研究会话"""
    try:
        manager = get_memory_manager()
        sessions, total = manager.list_sessions(status=status, limit=limit, offset=offset)
        return SessionListResponse(sessions=sessions, total=total, limit=limit, offset=offset)
    except Exception as e:
        logger.exception("Failed to list sessions")
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(session_id: str) -> SessionDetailResponse:
    """获取会话详情和所有记忆"""
    try:
        manager = get_memory_manager()
        session = manager.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")

        memories = manager.get_session_memories(session_id)

        return SessionDetailResponse(session=session, memories=memories)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话详情失败: {str(e)}")


@router.delete("/sessions/{session_id}", response_model=DeleteResponse)
async def delete_session(session_id: str) -> DeleteResponse:
    """删除会话及其所有记忆"""
    try:
        manager = get_memory_manager()
        deleted_count = manager.delete_session(session_id)

        return DeleteResponse(
            success=True,
            deleted_session_id=session_id,
            deleted_memory_count=deleted_count,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")