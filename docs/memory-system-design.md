# DeepResearch 记忆系统设计文档

## 1. 概述

### 1.1 目标

为 DeepResearch 项目设计一个基于 Chroma 向量数据库的记忆系统，实现以下核心功能：

- **会话记忆存储**：保存研究过程中的对话历史和任务上下文
- **语义搜索**：通过自然语言查询历史研究内容
- **上下文复用**：让 AI Agent 能够引用历史研究结果，避免重复工作
- **会话管理**：支持查看、检索和删除历史会话

### 1.2 功能范围

| 功能 | 描述 |
|------|------|
| 自动记忆捕获 | 在 Agent 运行过程中自动保存关键信息到向量数据库 |
| 语义搜索 | 通过自然语言查询历史记忆 |
| 会话管理 | 列出、查看、删除历史研究会话 |
| 上下文增强 | 为后续研究提供相关历史背景 |

---

## 2. 数据模型

### 2.1 与现有 models.py 的关系

现有的 `models.py` 定义了以下核心数据结构：

```python
class TodoItem(BaseModel):
    id: str
    title: str
    intent: str
    query: str
    status: str
    summary: str | None
    sources_summary: str | None
    note_id: str | None
    note_path: str | None

class ResearchResult(BaseModel):
    todo_items: list[TodoItem]
    report_markdown: str | None
    running_summary: str | None
```

记忆系统在设计上与现有模型互补：
- **ResearchResult** 代表单次研究运行的结果
- **Memory** 存储跨会话的研究记忆，支持语义检索

### 2.2 新增向量存储数据结构

#### 2.2.1 MemoryRecord (记忆记录)

存储在 Chroma Collection 中的核心数据结构：

```python
class MemoryRecord(BaseModel):
    """记忆记录向量存储结构"""

    # 向量 ID（唯一标识）
    id: str

    # 文档内容（用于生成 embedding 和展示）
    content: str

    # 元数据
    metadata: MemoryMetadata


class MemoryMetadata(BaseModel):
    """记忆记录的元数据"""

    # 会话关联
    session_id: str                    # 所属会话 ID
    session_topic: str                 # 会话主题/研究话题

    # 内容类型
    content_type: Literal[
        "task_summary",       # 任务总结
        "research_finding",   # 研究发现
        "user_query",         # 用户查询
        "agent_response",     # Agent 响应
        "report_section"      # 报告章节
    ]

    # 任务关联（可选）
    task_id: str | None               # 关联的任务 ID
    task_title: str | None            # 关联的任务标题

    # 时间戳
    created_at: str                   # ISO 格式时间戳
    updated_at: str                   # 更新时间戳

    # 来源信息
    source: str                       # 来源标记，如 "agent", "user", "system"
```

#### 2.2.2 ResearchSession (研究会话)

管理会话级别的元数据（存储在 PostgreSQL/SQLite 或 JSON 文件中）：

```python
class ResearchSession(BaseModel):
    """研究会话"""

    id: str                           # 会话 ID (UUID)
    topic: str                        # 研究主题
    created_at: str                   # 创建时间
    updated_at: str                   # 最后更新时间
    status: Literal["active", "completed", "failed"]

    # 统计信息
    task_count: int                   # 任务数量
    memory_count: int                 # 记忆记录数量

    # 摘要信息
    summary: str | None               # 会话摘要
```

### 2.3 数据流转关系

```
┌─────────────────────────────────────────────────────────────┐
│                        ResearchSession                       │
│  (会话级元数据: id, topic, status, summary)                  │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      MemoryRecord                            │
│  (向量存储: content + metadata)                              │
│  ├── content_type="task_summary"  → 来自 TodoItem.summary  │
│  ├── content_type="research_finding" → 来自sources_summary │
│  ├── content_type="user_query"    → 用户输入                │
│  └── content_type="report_section" → 报告内容              │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 存储层设计

### 3.1 Chroma Collection 设计

#### 3.1.1 Collection 命名

| Collection 名称 | 用途 |
|-----------------|------|
| `research_memories` | 主要记忆存储 collection |

#### 3.1.2 字段配置

```python
# Collection 字段设计
collection_schema = {
    "id": "string (primary key)",
    "document": "string (自动生成 embedding)",
    "metadata": {
        "session_id": "string",
        "session_topic": "string",
        "content_type": "string",
        "task_id": "string",
        "task_title": "string",
        "created_at": "string",
        "updated_at": "string",
        "source": "string"
    }
}
```

#### 3.1.3 Collection 配置

```python
from chromadb.config import Settings

# Chroma 客户端配置
chroma_settings = Settings(
    persist_directory="./data/chroma",  # 持久化存储目录
    anonymized_telemetry=False          # 关闭匿名遥测
)
```

### 3.2 Embedding 模型选择

| 方案 | 模型 | 维度 | 特点 | 推荐 |
|------|------|------|------|------|
| 默认 | `sentence-transformers/all-MiniLM-L6-v2` | 384 | 开源、轻量、快速 | 初期使用 |
| 高质量 | `sentence-transformers/all-mpnet-base-v2` | 768 | 精度更高 | 需要高精度时 |
| OpenAI | `text-embedding-ada-002` | 1536 | 商业级质量 | 有 API 预算时 |

**推荐配置**（config.py 中添加）：

```python
class Configuration(BaseModel):
    # ... 现有配置 ...

    # 记忆系统配置
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chroma_persist_directory: str = "./data/chroma"
```

### 3.3 存储策略

1. **持久化存储**：使用本地文件系统持久化 Chroma 数据
2. **分 Collection 存储**：不同类型的记忆可考虑分 Collection（如 `research_tasks`, `research_findings`）
3. **定期清理**：可配置自动删除过期的会话记忆（如超过 90 天）

---

## 4. API 设计

记忆系统将作为 FastAPI 的子路由挂载。以下是设计的 API 端点：

### 4.1 端点总览

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/memory/search` | 语义搜索记忆 |
| GET | `/memory/sessions` | 列出所有会话 |
| GET | `/memory/sessions/{session_id}` | 获取会话详情 |
| DELETE | `/memory/sessions/{session_id}` | 删除会话及其记忆 |
| GET | `/healthz` | 健康检查（已存在） |

### 4.2 详细 API 说明

#### 4.2.1 GET /memory/search

语义搜索历史记忆。

**请求参数**：

```
Query Parameters:
  - query: string (required)       # 搜索查询文本
  - session_id: string (optional)  # 限定在某个会话中搜索
  - content_type: string (optional) # 过滤内容类型
  - limit: int (default: 5)        # 返回结果数量
```

**响应示例**：

```json
{
  "results": [
    {
      "id": "mem_abc123",
      "content": "Python 异步编程研究总结：...",
      "metadata": {
        "session_id": "sess_xyz789",
        "session_topic": "Python 异步编程最佳实践",
        "content_type": "task_summary",
        "task_id": "task_001",
        "task_title": "异步编程基础",
        "created_at": "2024-01-15T10:30:00Z",
        "source": "agent"
      },
      "distance": 0.234
    }
  ],
  "total": 1
}
```

#### 4.2.2 GET /memory/sessions

列出所有研究会话。

**请求参数**：

```
Query Parameters:
  - limit: int (default: 20)       # 每页数量
  - offset: int (default: 0)       # 偏移量
  - status: string (optional)      # 过滤状态: active, completed, failed
```

**响应示例**：

```json
{
  "sessions": [
    {
      "id": "sess_xyz789",
      "topic": "Python 异步编程最佳实践",
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T11:30:00Z",
      "status": "completed",
      "task_count": 5,
      "memory_count": 12,
      "summary": "研究了异步编程的核心概念..."
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

#### 4.2.3 GET /memory/sessions/{session_id}

获取指定会话的详细信息和记忆记录。

**响应示例**：

```json
{
  "session": {
    "id": "sess_xyz789",
    "topic": "Python 异步编程最佳实践",
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T11:30:00Z",
    "status": "completed",
    "task_count": 5,
    "memory_count": 12,
    "summary": "研究了异步编程的核心概念..."
  },
  "memories": [
    {
      "id": "mem_abc123",
      "content": "任务总结：...",
      "content_type": "task_summary",
      "task_id": "task_001",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### 4.2.4 DELETE /memory/sessions/{session_id}

删除指定会话及其所有关联记忆。

**响应**：

```json
{
  "success": true,
  "deleted_session_id": "sess_xyz789",
  "deleted_memory_count": 12
}
```

---

## 5. 集成方案

### 5.1 在 agent.py 中接入记忆系统

#### 5.1.1 设计 MemoryManager 类

```python
# backend/src/memory/manager.py

class MemoryManager:
    """记忆管理器"""

    def __init__(self, config: Configuration):
        self.config = config
        self.client = ChromaClient(
            persist_directory=config.chroma_persist_directory
        )
        self.collection = self.client.get_or_create_collection(
            "research_memories",
            embedding_function=self._get_embedding_function()
        )

    def _get_embedding_function(self):
        """获取 embedding 函数"""
        # 根据配置选择 embedding 模型
        if self.config.embedding_model.startswith("sentence-transformers"):
            return SentenceTransformerEmbeddingFunction(
                model_name=self.config.embedding_model
            )
        # 可扩展其他 embedding 方案

    async def add_memory(self, session_id: str, session_topic: str,
                         content: str, content_type: str,
                         task_id: str = None, task_title: str = None,
                         source: str = "agent") -> str:
        """添加记忆记录"""
        memory_id = f"mem_{uuid4().hex[:8]}"
        now = datetime.utcnow().isoformat() + "Z"

        self.collection.upsert(
            ids=[memory_id],
            documents=[content],
            metadatas=[{
                "session_id": session_id,
                "session_topic": session_topic,
                "content_type": content_type,
                "task_id": task_id,
                "task_title": task_title,
                "created_at": now,
                "updated_at": now,
                "source": source
            }]
        )
        return memory_id

    async def search(self, query: str, session_id: str = None,
                     content_type: str = None, limit: int = 5) -> list[dict]:
        """语义搜索"""
        where = {}
        if session_id:
            where["session_id"] = session_id
        if content_type:
            where["content_type"] = content_type

        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where=where if where else None,
            include=["documents", "metadatas", "distances"]
        )

        return self._format_search_results(results)

    def _format_search_results(self, results: dict) -> list[dict]:
        """格式化搜索结果"""
        formatted = []
        for i in range(len(results["ids"][0])):
            formatted.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]
            })
        return formatted
```

#### 5.1.2 在 DeepResearchAgent 中集成

修改 `agent.py` 中的 `DeepResearchAgent` 类：

```python
# backend/src/agent.py

from memory.manager import MemoryManager

class DeepResearchAgent:
    def __init__(self, config: Configuration):
        self.config = config
        # ... 现有初始化 ...

        # 初始化记忆系统
        self.memory_manager = MemoryManager(config)
        self.current_session_id = str(uuid4())

    def run(self, topic: str) -> ResearchResult:
        # 创建新会话记录
        session = self._create_session(topic)

        try:
            # ... 现有研究逻辑 ...

            # 保存用户查询
            self.memory_manager.add_memory(
                session_id=self.current_session_id,
                session_topic=topic,
                content=f"用户研究主题: {topic}",
                content_type="user_query",
                source="user"
            )

            # 在任务处理过程中保存记忆
            for task in result.todo_items:
                if task.summary:
                    self.memory_manager.add_memory(
                        session_id=self.current_session_id,
                        session_topic=topic,
                        content=task.summary,
                        content_type="task_summary",
                        task_id=task.id,
                        task_title=task.title,
                        source="agent"
                    )

                if task.sources_summary:
                    self.memory_manager.add_memory(
                        session_id=self.current_session_id,
                        session_topic=topic,
                        content=task.sources_summary,
                        content_type="research_finding",
                        task_id=task.id,
                        task_title=task.title,
                        source="agent"
                    )

            # 更新会话状态
            self._update_session_status("completed")

        except Exception as e:
            self._update_session_status("failed")
            raise

        return result

    async def get_related_memories(self, query: str,
                                   limit: int = 3) -> list[dict]:
        """获取与查询相关的历史记忆（用于上下文增强）"""
        return await self.memory_manager.search(
            query=query,
            limit=limit
        )
```

#### 5.1.3 在 main.py 中挂载记忆路由

```python
# backend/src/main.py

from fastapi import FastAPI
from memory.routes import router as memory_router

def create_app() -> FastAPI:
    app = FastAPI(title="HelloAgents Deep Researcher")

    # ... 现有中间件配置 ...

    # 挂载记忆系统路由
    app.include_router(memory_router, prefix="/memory", tags=["memory"])

    return app
```

---

## 6. 目录结构建议

建议新增以下模块结构：

```
backend/src/
├── agent.py              # 现有 - Agent 主逻辑
├── config.py             # 现有 - 配置管理
├── models.py             # 现有 - 数据模型
├── main.py               # 现有 - FastAPI 入口
├── services/             # 现有 - 服务模块
│   ├── notes.py
│   ├── planner.py
│   └── ...
│
└── memory/               # 新增 - 记忆系统模块
    ├── __init__.py
    ├── manager.py        # MemoryManager 类
    ├── storage.py        # Chroma 存储抽象
    ├── models.py         # 记忆系统数据模型
    ├── routes.py         # API 路由
    └── config.py         # 记忆系统配置
```

### 6.1 各模块职责

| 文件 | 职责 |
|------|------|
| `memory/__init__.py` | 模块导出 |
| `memory/manager.py` | 记忆管理器核心类，提供添加、搜索等方法 |
| `memory/storage.py` | Chroma 底层存储抽象 |
| `memory/models.py` | Pydantic 数据模型（MemoryRecord, ResearchSession） |
| `memory/routes.py` | FastAPI 路由定义 |
| `memory/config.py` | 记忆系统配置（可扩展） |

---

## 7. 后续扩展建议

1. **语义缓存**：将常见查询的结果缓存到向量数据库，提升响应速度
2. **会话比较**：比较两个会话的相似度和关联关系
3. **自动摘要**：定期对长期记忆进行摘要压缩，节省存储空间
4. **多模态支持**：扩展支持图像、PDF 等非文本内容的记忆存储
5. **会话导出**：支持将会话数据导出为 Markdown 或 JSON 格式

---

## 8. 依赖清单

```txt
# 核心依赖
chromadb>=0.4.0

# Embedding 模型（根据选择）
sentence-transformers>=2.2.0  # 默认 embedding 模型

# 可选：高级功能
# openai>=1.0.0                # 如使用 OpenAI embedding
# httpx>=0.24.0                # 异步 HTTP 客户端
```

---

*文档版本: 1.0*
*创建日期: 2024*