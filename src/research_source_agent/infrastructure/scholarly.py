"""HTTP adapters for Crossref JSON and arXiv Atom metadata."""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import quote

import requests

from research_source_agent.domain.articles import (
    Article, clean_text, normalize_doi, stable_ref_id,
)


CROSSREF_API = "https://api.crossref.org/works"
ARXIV_API = "https://export.arxiv.org/api/query"
DEFAULT_TIMEOUT = 20


def _publication_year(item: dict) -> int | None:
    for key in ("published-print", "published-online", "issued", "created"):
        parts = item.get(key, {}).get("date-parts", [])
        if parts and parts[0] and isinstance(parts[0][0], int):
            return parts[0][0]
    return None


def _crossref_headers() -> dict[str, str]:
    email = os.getenv("CROSSREF_MAILTO", "").strip()
    agent = "ResearchSourceAgent/1.0"
    if email:
        agent += f" (mailto:{email})"
    return {"User-Agent": agent, "Accept": "application/json"}


def search_crossref(query: str, year_from: int | None, limit: int) -> list[Article]:
    params: dict[str, str | int] = {
        "query.bibliographic": query,
        "rows": limit,
        "sort": "relevance",
        "order": "desc",
    }
    if year_from:
        params["filter"] = f"from-pub-date:{year_from}-01-01"

    response = requests.get(
        CROSSREF_API,
        params=params,
        headers=_crossref_headers(),
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    response.encoding = "utf-8"

    articles: list[Article] = []
    for rank, item in enumerate(response.json().get("message", {}).get("items", [])):
        title_values = item.get("title") or []
        title = clean_text(title_values[0] if title_values else "")
        if not title:
            continue

        authors = []
        for author in item.get("author") or []:
            name = " ".join(
                part for part in (author.get("given", ""), author.get("family", "")) if part
            ).strip()
            if name:
                authors.append(name)

        doi = normalize_doi(item.get("DOI"))
        containers = item.get("container-title") or []
        article = Article(
            ref_id="",
            title=title,
            authors=authors[:8],
            year=_publication_year(item),
            venue=clean_text(containers[0] if containers else item.get("publisher", "")),
            doi=doi,
            url=f"https://doi.org/{quote(doi, safe='/()')}" if doi else item.get("URL", ""),
            abstract=clean_text(item.get("abstract"))[:2400],
            source_database="Crossref",
            source_query=query,
            relevance=float(limit - rank),
        )
        article.ref_id = stable_ref_id(article)
        articles.append(article)
    return articles


def search_arxiv(query: str, year_from: int | None, limit: int) -> list[Article]:
    search_terms = re.findall(r"[0-9A-Za-z][0-9A-Za-z.+-]*|[\u4e00-\u9fff]{2,}", query)
    arxiv_query = " AND ".join(f"all:{term}" for term in search_terms[:8])
    arxiv_query = arxiv_query or f"all:{query}"
    if year_from:
        now = datetime.now(timezone.utc)
        if year_from > now.year:
            return []
        arxiv_query = (
            f"({arxiv_query}) AND "
            f"submittedDate:[{year_from}01010000 TO {now:%Y%m%d%H%M}]"
        )
    response = requests.get(
        ARXIV_API,
        params={
            "search_query": arxiv_query,
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
            "sortOrder": "descending",
        },
        headers={"User-Agent": "ResearchSourceAgent/1.0"},
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()

    root = ET.fromstring(response.text)
    atom = "{http://www.w3.org/2005/Atom}"
    articles: list[Article] = []
    for rank, entry in enumerate(root.findall(f"{atom}entry")):
        published = clean_text(entry.findtext(f"{atom}published"))
        year = int(published[:4]) if re.match(r"^\d{4}", published) else None
        if year_from and year and year < year_from:
            continue

        entry_url = clean_text(entry.findtext(f"{atom}id"))
        arxiv_id = entry_url.rstrip("/").rsplit("/", 1)[-1]
        article = Article(
            ref_id="",
            title=clean_text(entry.findtext(f"{atom}title")),
            authors=[
                clean_text(author.findtext(f"{atom}name"))
                for author in entry.findall(f"{atom}author")
            ][:8],
            year=year,
            venue="arXiv",
            doi="",
            url=entry_url,
            abstract=clean_text(entry.findtext(f"{atom}summary"))[:2400],
            source_database="arXiv",
            source_query=query,
            relevance=float(limit - rank),
        )
        doi_node = entry.find("{http://arxiv.org/schemas/atom}doi")
        if doi_node is not None and doi_node.text:
            article.doi = normalize_doi(doi_node.text)
            article.url = f"https://doi.org/{quote(article.doi, safe='/()')}"
        elif arxiv_id:
            article.url = f"https://arxiv.org/abs/{arxiv_id}"
        article.ref_id = stable_ref_id(article)
        if article.title:
            articles.append(article)
    return articles
