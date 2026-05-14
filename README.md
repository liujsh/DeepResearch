# DeepResearch

基于 **HelloAgents** 框架构建的深度研究 Agent 系统。能够根据用户提供的主题，自主进行多轮智能搜索、任务拆解规划、信息提炼总结，并使用流式输出（SSE）实时反馈研究进度，最终生成结构化的 Markdown 深度研究报告。

## 🌟 核心特性

- **多 Agent 协同**：内置研究规划专家、任务总结专家和报告撰写专家，分工明确、逻辑清晰。
- **流式响应 (SSE)**：前端实时展示任务拆解、搜索进度、摘要生成及最终报告，拒绝在长耗时任务中焦急等待。
- **智能化记忆系统**：集成 Chroma 向量语义存储，自动保存和检索过往研究记录，避免无效重复，保留完整的上下文知识库。
- **多渠道搜索**：支持 DuckDuckGo、Tavily、SearXNG 等多种搜索引擎后端。
- **灵活的 LLM 驱动**：
  - 支持本地模型 (Ollama, LMStudio)
  - 支持云端兼容 OpenAI 格式的 API (如 Kimi, Qwen, Claude, GPT-4 等)
- **前后端分离架构**：
  - **后端**：Python + FastAPI + HelloAgents
  - **前端**：Vue 3 + TypeScript + Vite，极简且现代的 UI。

---

## 🛠️ 技术栈

- **后端**: FastAPI, HelloAgents, Pydantic, Loguru
- **前端**: Vue 3, TypeScript, Vite, CSS
- **存储**: Chroma 向量数据库 (已内置，用于研究记忆持久化与语义检索)

---

## 🚀 快速开始

### 1. 后端服务部署

后端基于 Python 和 FastAPI 构建，使用 `uv` 进行包管理。

```bash
cd backend

# 安装依赖项
uv sync 
# 或者 pip install -r requirements.txt (如果使用常规虚拟环境)

# 配置环境变量
cp .env.example .env
```

**编辑 `.env` 文件**：
在 `.env` 中配置你想使用的 LLM 模型和搜索 API。例如：
```env
SEARCH_API=tavily  # 推荐使用 tavily 获取更稳定的搜索效果
TAVILY_API_KEY=tvly-xxx

LLM_PROVIDER=custom
LLM_MODEL_ID=Pro/moonshotai/Kimi-K2.5
LLM_API_KEY=sk-xxxx
LLM_BASE_URL=https://api.siliconflow.cn/v1
```

**启动后端服务**：
```bash
python src/main.py
# 服务将默认运行在 http://localhost:8000
```

### 2. 前端服务部署

前端基于 Vue 3 + Vite 构建。

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将运行在 `http://localhost:5173`。在浏览器中打开该地址，输入你需要深入研究的课题，即可开始体验！

---

## 🛣️ 发展路线图 (Roadmap)

近期完成和正在进行的主要改进计划包括：

- [x] **记忆系统 (向量语义存储)**：引入 Chroma 向量数据库，存储研究历史，支持语义检索过往研究，保存完整研究上下文。
- [x] **前端多研究会话管理**：支持侧边栏历史记录列表，可查看、管理和重新激活历史研究报告和相关引用、任务信息。
- [ ] **前端体验增强**：增加研究统计图表、改进前端可视化展示效果、添加暗色模式支持。
- [ ] **前沿 Agent 技术集成**：
  - 引入 MCP (Model Context Protocol) 协议
  - 增加 Prompt Caching 优化长文本/多轮对话的成本和速率
  - 升级高级 Tool Calling 优化

---

## 🤝 贡献与反馈

欢迎提交 Issue 和 Pull Request，共同帮助系统完善！

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。