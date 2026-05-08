# DeepResearch 项目指南

## 项目概述
基于HelloAgents框架的深度研究Agent系统，支持多轮智能检索、任务规划、流式输出和报告生成。前端使用Vue 3 + TypeScript，后端使用FastAPI + Python。

## 技术栈
- **后端**: FastAPI, HelloAgents, Pydantic, Loguru
- **前端**: Vue 3, TypeScript, Vite
- **LLM**: 支持Ollama/LMStudio/第三方API
- **搜索**: DuckDuckGo, SearXNG, Tavily等
- **存储**: 向量数据库 (Chroma等)

## 关键模块

### 后端核心 (backend/src/)
- `agent.py`: DeepResearchAgent协调器，管理多Agent工作流
- `main.py`: FastAPI应用入口，提供/research和/research/stream接口
- `config.py`: Configuration类管理环境变量和配置
- `models.py`: SummaryState, TodoItem等数据结构

### 服务层 (backend/src/services/)
- `planner.py`: 任务规划服务，将主题分解为子任务
- `search.py`: 搜索分发，调用HelloAgents SearchTool
- `summarizer.py`: 任务摘要生成
- `reporter.py`: 最终报告整合生成

### 前端 (frontend/src/)
- `App.vue`: 主组件，包含表单、任务列表、研究进度展示
- `services/api.ts`: SSE流式API调用封装

## 开发约定

### 代码风格
- Python: 遵循项目现有风格，使用类型提示
- Vue/TypeScript: 使用Composition API (<script setup>)
- 变量命名: 英文语义化命名

### API设计
- RESTful: GET /healthz, POST /research, POST /research/stream
- 流式响应: 使用Server-Sent Events (SSE)

### 配置管理
- 使用config.py的Configuration类
- 环境变量: LLM相关、搜索API、笔记工作区等

### 日志
- 使用Loguru进行结构化日志
- 区分INFO/ERROR级别

## 当前改进计划

### 1. 记忆系统 - 向量语义存储 (Chroma) ✅ 已完成
- 使用Chroma向量数据库存储研究历史
- 支持语义检索过往研究
- 保存完整研究上下文

### 2. 前端渐进增强
- 增加研究统计图表
- 改进任务状态可视化
- 添加暗色模式支持

### 3. 前沿Agent技术
- MCP协议集成
- Prompt Caching
- 高级Tool Calling优化