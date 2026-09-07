"""将同一检索能力作为 MCP 工具提供给其他 Agent。"""

from __future__ import annotations
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from research_source_agent.article_search import search_articles

mcp = FastMCP('ResearchArticleAgent')

ArticleSource = Literal["crossref", "arxiv"]

@mcp.tool()
def search_research_sources(
    query: Annotated[
        str,
        Field(
            description="具体检索词，优先使用论文常见的中英文关键词组合",
        ),
    ],
    year_from: Annotated[
        int | None,
        Field(
            ge=1900,
            le=2100,
            description="最早发表年份，不传表示不限制",
        ),
    ] = None,
    limit: Annotated[
        int,
        Field(
            ge=1,
            le=12,
            description="去重后最多返回的文章数量",
        ),
    ] = 8,
    source: Annotated[
        list[ArticleSource] | None,
        Field(
            min_length=1,
            description="要检索的数据源，可选 crossref、arxiv",
        ),
    ] = None,
) -> dict:
    """
    检索公开学术文章并返回去重后的元数据。
    返回内容包括作者、年份、来源、DOI、摘要和去重统计。
    结果中的ref_id是后续回答唯一允许使用的引用编号。
    """

    selected_sources = (
        source
        if source is not None
        else ["crossref", "arxiv"]
    )

    return search_articles(
        query=query,
        year_from=year_from,
        limit=limit,
        sources=selected_sources,
    )

if __name__ == '__main__':
    mcp.run()
