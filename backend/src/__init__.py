"""HelloAgents Deep Research - A deep research assistant powered by HelloAgents."""

import os

# 确保在导入其他模块前加载 .env 配置
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(override=True)

# 预先设置 HuggingFace 镜像（如果配置了）
HF_ENDPOINT = os.environ.get("HF_ENDPOINT", "")
if HF_ENDPOINT:
    os.environ["HF_ENDPOINT"] = HF_ENDPOINT
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

__version__ = "0.0.1"

from .agent import DeepResearchAgent
from .config import Configuration, SearchAPI
from .models import SummaryState, SummaryStateInput, SummaryStateOutput, TodoItem

__all__ = [
    "DeepResearchAgent",
    "Configuration",
    "SearchAPI",
    "SummaryState",
    "SummaryStateInput",
    "SummaryStateOutput",
    "TodoItem",
]

