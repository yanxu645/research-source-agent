"""Structured agent results passed to presentation layers."""

from dataclasses import dataclass, field


@dataclass
class ToolEvent:
    name:str #工具名
    query: str = ""  # 检索词
    unique_count: int = 0 #去重后的文献数
    duplicates_removed: int = 0 #重复文献数
    warnings: list[str] = field(default_factory=list) #警告信息
    articles: list[dict] = field(default_factory=list) #文献清单

@dataclass
class AgentResult:
    answer:str #用于在聊天区域中显示的回答
    tool_events: list[ToolEvent]
