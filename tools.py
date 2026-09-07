"""供 LangGraph Agent 调用的文献检索工具。"""

from __future__ import annotations
import json
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field
from research_source_agent.article_search import search_articles

ArticleSource = Literal["crossref", "arxiv"]

class ArticleSearchInput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    query: str = Field(description='具体检索词，优先使用论文常见的中英文关键词组合',)
    year_from: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
        description='最早发表年份，比如2000，不传表示不限制起始年份',
    )
    limit: int = Field(
        default=8,
        ge=1,
        le=12,
        description='去重后最多返回文章数',
    )
    source: list[ArticleSource] = Field(
        default_factory=lambda: ["crossref", "arxiv"],
        min_length=1,
        description='要检索的公开学术数据源，仅限crossref、arxiv',
    )


@tool(args_schema=ArticleSearchInput)
def search_scholarly_articles(
        query: str,
        year_from: int | None = None,
        limit: int = 8,
        source: list[ArticleSource] | None = None,
)->str:
    """
    检索公开学术文章，返回作者、年份、来源、DOI、摘要和去重统计。
    当用户需要相关文章、引用文献、研究现状或大纲整理时，调用此工具。
    工具结束中的ref_id是后续回答唯一允许使用的引用编号，不得自行编造ref_id，也不得引用工具结果中不存在的文章
    """

    selected_sources: list[ArticleSource] = source or ["crossref", "arxiv"]

    result = search_articles(
        query=query,
        year_from=year_from,
        limit=limit,
        sources=selected_sources,
    )

    return json.dumps(result, ensure_ascii=False)

TOOLS = [search_scholarly_articles]
