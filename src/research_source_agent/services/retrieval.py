"""Aggregate providers, deduplicate results and report source failures."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Iterable

import requests

from research_source_agent.domain.articles import Article, deduplicate_articles
from research_source_agent.infrastructure.scholarly import search_arxiv, search_crossref


def search_articles(
    query: str,
    year_from: int | None = None,
    limit: int = 8,
    sources: Iterable[str] = ("crossref", "arxiv"),
) -> dict:
    """检索多个公开数据源并返回可追溯、已去重的结构化结果。"""
    query = query.strip()
    if not query:
        raise ValueError("检索主题不能为空")
    limit = max(1, min(int(limit), 12))
    requested_sources = {source.strip().lower() for source in sources}
    articles: list[Article] = []
    warnings: list[str] = []

    providers = (
        ("crossref", search_crossref),
        ("arxiv", search_arxiv),
    )
    for provider_name, provider in providers:
        if provider_name not in requested_sources:
            continue
        try:
            articles.extend(provider(query, year_from, limit))
        except (requests.RequestException, ValueError, ET.ParseError) as error:
            warnings.append(f"{provider_name} 暂时不可用：{type(error).__name__}")

    unique, duplicate_count = deduplicate_articles(articles)
    unique.sort(key=lambda item: (item.relevance, item.year or 0), reverse=True)
    selected = unique[:limit]
    return {
        "query": query,
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "requested_sources": sorted(requested_sources),
        "original_count": len(articles),
        "unique_count": len(selected),
        "duplicates_removed": duplicate_count,
        "warnings": warnings,
        "articles": [article.public_dict() for article in selected],
    }
