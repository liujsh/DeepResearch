"""Vector storage layer for memory system (Chroma/Qdrant)."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from .models import MemoryMetadata, SearchResult

logger = logging.getLogger(__name__)

# 设置 HuggingFace 镜像（如果配置了）
_HF_ENDPOINT = os.environ.get("HF_ENDPOINT", "")
if _HF_ENDPOINT:
    os.environ["HF_ENDPOINT"] = _HF_ENDPOINT
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
    logger.info(f"Using HuggingFace mirror: {_HF_ENDPOINT}")

COLLECTION_NAME = "research_memories"

# 默认使用 bge-large-zh-v1.5 (中文效果更好)
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-large-zh-v1.5"

# 分块配置
CHUNK_SIZE = 1024  # 每个块的最大字符数
CHUNK_OVERLAP = 128  # 块之间的重叠字符数
MAX_CHUNK_LENGTH = 2000  # 超过此长度自动分块

# Qdrant 配置
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
QDRANT_GRPC_PORT = int(os.environ.get("QDRANT_GRPC_PORT", "6334"))


def text_chunker(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """
    将长文本分块，返回块列表。
    每个块包含: id, content, metadata
    """
    if len(text) <= chunk_size:
        return [{"id": "full", "content": text, "chunk_index": 0}]

    chunks = []
    # 按段落分割，保留段落完整性
    paragraphs = re.split(r'\n\n+', text)

    current_chunk = ""
    chunk_index = 0

    for para in paragraphs:
        # 如果单个段落超过 chunk_size，进一步按句子分割
        if len(para) > chunk_size:
            if current_chunk:
                chunks.append({
                    "id": f"chunk_{chunk_index}",
                    "content": current_chunk.strip(),
                    "chunk_index": chunk_index
                })
                chunk_index += 1
                current_chunk = ""

            # 按句子分割大段落
            sentences = re.split(r'(?<=[。！？]) +', para)
            for sent in sentences:
                if len(current_chunk) + len(sent) > chunk_size:
                    if current_chunk:
                        chunks.append({
                            "id": f"chunk_{chunk_index}",
                            "content": current_chunk.strip(),
                            "chunk_index": chunk_index
                        })
                        chunk_index += 1
                    # 从上一块末尾保留 overlap 长度的内容
                    current_chunk = current_chunk[-overlap:] + sent if len(current_chunk) > overlap else sent
                else:
                    current_chunk += sent + "\n\n"
        else:
            if len(current_chunk) + len(para) > chunk_size:
                chunks.append({
                    "id": f"chunk_{chunk_index}",
                    "content": current_chunk.strip(),
                    "chunk_index": chunk_index
                })
                chunk_index += 1
                # 从上一块末尾保留 overlap 长度的内容
                current_chunk = current_chunk[-overlap:] + para if len(current_chunk) > overlap else para
            else:
                current_chunk += para + "\n\n"

    # 添加最后一个块
    if current_chunk.strip():
        chunks.append({
            "id": f"chunk_{chunk_index}",
            "content": current_chunk.strip(),
            "chunk_index": chunk_index
        })

    logger.debug(f"Chunked text into {len(chunks)} pieces")
    return chunks


class ChromaStorage:
    """Chroma 向量存储抽象"""

    def __init__(
        self,
        persist_directory: str = "./data/chroma",
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
        max_chunk_length: int = MAX_CHUNK_LENGTH,
    ):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_chunk_length = max_chunk_length

        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        self.embedding_function = self._create_embedding_function()
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        """获取或创建 collection，自动处理 embedding 模型变化"""
        ef = self.embedding_function
        try:
            collection = self.client.get_collection(
                COLLECTION_NAME,
                embedding_function=ef
            )

            # 检查 embedding 模型是否变化
            existing_model = collection.metadata.get("embedding_model") if collection.metadata else None
            if existing_model and existing_model != self.embedding_model:
                logger.warning(
                    f"Embedding model changed from {existing_model} to {self.embedding_model}. "
                    "Recreating collection..."
                )
                self.client.delete_collection(COLLECTION_NAME)
                collection = self.client.create_collection(
                    name=COLLECTION_NAME,
                    embedding_function=ef,
                    metadata={"description": "DeepResearch memory storage", "embedding_model": self.embedding_model},
                )
                logger.info(f"Created new collection with model: {self.embedding_model}")
            else:
                logger.info(f"Loaded existing collection: {COLLECTION_NAME}")

        except Exception:
            logger.info(f"Creating new collection: {COLLECTION_NAME} with {self.embedding_model}")
            collection = self.client.create_collection(
                name=COLLECTION_NAME,
                embedding_function=ef,
                metadata={"description": "DeepResearch memory storage", "embedding_model": self.embedding_model},
            )

        return collection

    def _create_embedding_function(self):
        """创建 embedding 函数"""
        # 支持 sentence-transformers 格式的模型
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

        # 支持 HuggingFace 格式的模型 (如 bge-large-zh-v1.5)
        try:
            from chromadb.utils.embedding_functions import (
                HuggingFaceEmbeddingFunction,
            )

            return HuggingFaceEmbeddingFunction(
                model_name=self.embedding_model
            )
        except ImportError:
            logger.warning(
                f"HuggingFaceEmbeddingFunction not available for {self.embedding_model}"
            )

        return None

    def add_memory(
        self,
        memory_id: str,
        content: str,
        metadata: dict,
        disable_chunk: bool = False,
    ) -> None:
        """
        添加记忆记录，支持自动分块。

        如果内容超过 max_chunk_length 且未禁用分块，会自动将内容分成多个块存储。
        每个块都有独立的向量，用于语义检索。
        """
        # 检查是否需要分块
        needs_chunking = not disable_chunk and len(content) > self.max_chunk_length

        if needs_chunking:
            # 分块存储
            chunks = text_chunker(content, self.chunk_size, self.chunk_overlap)

            ids = []
            documents = []
            metadatas = []

            # 保存原始内容的完整记录 (标记为 full_report)
            full_metadata = dict(metadata)
            full_metadata["is_full_report"] = True
            full_metadata["total_chunks"] = len(chunks)

            ids.append(f"{memory_id}_full")
            documents.append(content)  # 存储完整内容
            metadatas.append(full_metadata)

            # 存储每个分块
            for chunk in chunks:
                chunk_metadata = dict(metadata)
                chunk_metadata["is_chunk"] = True
                chunk_metadata["chunk_id"] = chunk["id"]
                chunk_metadata["chunk_index"] = chunk["chunk_index"]
                chunk_metadata["total_chunks"] = len(chunks)
                chunk_metadata["is_full_report"] = True  # 标记为报告内容

                # 只存储 chunk，不存储完整内容在 document 字段以节省空间
                chunk_full_id = f"{memory_id}_{chunk['id']}"
                ids.append(chunk_full_id)
                documents.append(chunk["content"])
                metadatas.append(chunk_metadata)

            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            logger.debug(f"Added memory {memory_id} as {len(chunks) + 1} chunks")
        else:
            # 不分块，直接存储
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


"""Qdrant 向量存储抽象 - 支持混合检索"""

import hashlib
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, Filter, FieldCondition, MatchValue, PointStruct

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-large-zh-v1.5"
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))


def _str_to_uuid(s: str, prefix: str = "") -> str:
    """将字符串转换为有效的 UUID"""
    if prefix:
        s = f"{prefix}_{s}"
    # 使用 MD5 哈希生成固定的 UUID
    h = hashlib.md5(s.encode()).hexdigest()
    return f"{h[:8]}-{h[8:12]}-4{h[12:15]}-{h[16:20]}-{h[20:]}"


class QdrantStorage:
    """Qdrant 向量存储抽象 - 支持混合检索"""

    def __init__(
        self,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        chunk_size: int = 1024,
        chunk_overlap: int = 128,
        max_chunk_length: int = 2000,
        host: str = QDRANT_HOST,
        port: int = QDRANT_PORT,
    ):
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_chunk_length = max_chunk_length
        self.host = host
        self.port = port

        # 初始化 Qdrant 客户端
        try:
            self._client = QdrantClient(host=self.host, port=self.port)
            self._vector_size = self._get_embedding_size()
            self._ensure_collection()
            logger.info(f"Connected to Qdrant at {self.host}:{self.port}")
        except ImportError:
            logger.error("qdrant-client not installed. Install with: pip install qdrant-client")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise

    def _get_embedding_size(self) -> int:
        """获取 embedding 向量维度"""
        if "bge-large" in self.embedding_model.lower():
            return 1024
        elif "bge" in self.embedding_model.lower():
            return 768
        elif "e5" in self.embedding_model.lower():
            return 1024
        return 768

    def _ensure_collection(self) -> None:
        """确保 collection 存在"""
        collections = self._client.get_collections().collections
        collection_names = [c.name for c in collections]

        if COLLECTION_NAME not in collection_names:
            self._client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=self._vector_size,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created Qdrant collection: {COLLECTION_NAME}")
        else:
            logger.info(f"Using existing Qdrant collection: {COLLECTION_NAME}")

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        """使用 sentence-transformers 生成 embedding"""
        try:
            from sentence_transformers import SentenceTransformer

            cache_folder = os.environ.get("SENTENCE_TRANSFORMERS_HOME")
            model = SentenceTransformer(self.embedding_model, cache_folder=cache_folder)
            embeddings = model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        except ImportError:
            logger.error("sentence-transformers not installed")
            raise
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise

    def add_memory(
        self,
        memory_id: str,
        content: str,
        metadata: dict,
        disable_chunk: bool = False,
    ) -> None:
        """添加记忆记录，支持自动分块"""
        needs_chunking = not disable_chunk and len(content) > self.max_chunk_length

        if needs_chunking:
            chunks = text_chunker(content, self.chunk_size, self.chunk_overlap)

            # 准备批量插入
            points = []

            # 完整报告
            full_metadata = dict(metadata)
            full_metadata["is_full_report"] = True
            full_metadata["total_chunks"] = len(chunks)
            full_metadata["original_id"] = memory_id  # 保存原始 ID

            full_embedding = self._embed_texts([content])[0]
            point_id = _str_to_uuid(f"{memory_id}_full", "full")

            points.append(PointStruct(
                id=point_id,
                vector=full_embedding,
                payload={**full_metadata, "content": content}
            ))

            # 分块
            for chunk in chunks:
                chunk_metadata = dict(metadata)
                chunk_metadata["is_chunk"] = True
                chunk_metadata["chunk_id"] = chunk["id"]
                chunk_metadata["chunk_index"] = chunk["chunk_index"]
                chunk_metadata["total_chunks"] = len(chunks)
                chunk_metadata["is_full_report"] = True
                chunk_metadata["original_id"] = memory_id

                chunk_embedding = self._embed_texts([chunk["content"]])[0]
                chunk_point_id = _str_to_uuid(f"{memory_id}_{chunk['id']}", "chunk")

                points.append(PointStruct(
                    id=chunk_point_id,
                    vector=chunk_embedding,
                    payload={**chunk_metadata, "content": chunk["content"]}
                ))

            self._client.upsert(
                collection_name=COLLECTION_NAME,
                points=points
            )
            logger.debug(f"Added memory {memory_id} as {len(chunks) + 1} chunks to Qdrant")
        else:
            # 不分块，直接存储
            embedding = self._embed_texts([content])[0]
            point_id = _str_to_uuid(memory_id, "mem")

            self._client.upsert(
                collection_name=COLLECTION_NAME,
                points=[PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={**metadata, "content": content, "original_id": memory_id}
                )]
            )
            logger.debug(f"Added memory to Qdrant: {memory_id} -> {point_id}")

    def search(
        self,
        query: str,
        session_id: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 5,
    ) -> list[SearchResult]:
        """语义搜索"""
        # 生成查询向量
        query_embedding = self._embed_texts([query])[0]

        # 构建过滤条件
        must_filters = []
        if session_id:
            must_filters.append({"key": "session_id", "match": {"value": session_id}})
        if content_type:
            must_filters.append({"key": "content_type", "match": {"value": content_type}})

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        search_params = {"limit": limit}
        if must_filters:
            filter_cond = Filter(must=[
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in [("session_id", session_id), ("content_type", content_type)]
                if v is not None
            ])
            search_params["query_filter"] = filter_cond

        results = self._client.query(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            **search_params
        )

        search_results = []
        for result in results:
            payload = result.payload
            content = payload.pop("content", "")
            search_results.append(
                SearchResult(
                    id=str(result.id),
                    content=content,
                    metadata=MemoryMetadata(**payload),
                    distance=result.score,
                )
            )

        return search_results

    def get_memories_by_session(self, session_id: str) -> list[SearchResult]:
        """获取会话的所有记忆"""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        results = self._client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(must=[
                FieldCondition(key="session_id", match=MatchValue(value=session_id))
            ]),
            with_payload=True,
            with_vectors=False,
        )[0]

        search_results = []
        for result in results:
            payload = result.payload
            content = payload.pop("content", "")
            search_results.append(
                SearchResult(
                    id=str(result.id),
                    content=content,
                    metadata=MemoryMetadata(**payload),
                    distance=0.0,
                )
            )

        return search_results

    def delete_memories_by_session(self, session_id: str) -> int:
        """删除会话的所有记忆"""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        results = self._client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(must=[
                FieldCondition(key="session_id", match=MatchValue(value=session_id))
            ]),
            with_payload=False,
        )[0]

        if results:
            ids = [r.id for r in results]
            self._client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=ids
            )
            deleted_count = len(ids)
            logger.info(f"Deleted {deleted_count} memories for session: {session_id}")
            return deleted_count

        return 0

    def count_memories(self, session_id: Optional[str] = None) -> int:
        """统计记忆数量"""
        if session_id:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            results = self._client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=Filter(must=[
                    FieldCondition(key="session_id", match=MatchValue(value=session_id))
                ]),
                with_payload=False,
                limit=100,  # 使用较大值获取所有记录
            )[0]
            return len(results)
        return self._client.get_collection(COLLECTION_NAME).points_count

    def clear_all(self) -> None:
        """清空所有记忆（危险操作）"""
        self._client.delete_collection(COLLECTION_NAME)
        self._ensure_collection()
        logger.warning("Cleared all memories from Qdrant collection")


def create_storage(storage_type: str = "chroma", **kwargs):
    """工厂函数：创建存储实例"""
    if storage_type == "qdrant":
        return QdrantStorage(**kwargs)
    else:
        return ChromaStorage(**kwargs)