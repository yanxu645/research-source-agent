"""公开学术数据源检索与确定性去重。"""

from __future__ import annotations
import hashlib
import html
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Iterable
from urllib.parse import quote
import requests


CROSSREF_API = "https://api.crossref.org/works"
ARXIV_API = "https://export.arxiv.org/api/query"
DEFAULT_TIMEOUT = 20


@dataclass
class Article:
    ref_id: str
    title: str
    authors: list[str]
    year: int | None
    venue: str
    doi: str
    url: str
    abstract: str
    source_database: str
    source_query: str
    relevance: float = 0.0

    def public_dict(self) -> dict:
        data = asdict(self)
        data.pop("relevance", None)
        return data


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def _normalize_doi(value: str | None) -> str:
    if not value:
        return ""
    doi = value.strip().lower()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
    return re.sub(r"^doi:\s*", "", doi).strip()


def _normalize_title(value: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", value.lower())


def _stable_ref_id(article: Article) -> str:
    identity = article.doi or article.url or _normalize_title(article.title)
    digest = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:7].upper()
    return f"S-{digest}"


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
        title = _clean_text(title_values[0] if title_values else "")
        if not title:
            continue

        authors = []
        for author in item.get("author") or []:
            name = " ".join(
                part for part in (author.get("given", ""), author.get("family", "")) if part
            ).strip()
            if name:
                authors.append(name)

        doi = _normalize_doi(item.get("DOI"))
        containers = item.get("container-title") or []
        article = Article(
            ref_id="",
            title=title,
            authors=authors[:8],
            year=_publication_year(item),
            venue=_clean_text(containers[0] if containers else item.get("publisher", "")),
            doi=doi,
            url=f"https://doi.org/{quote(doi, safe='/()')}" if doi else item.get("URL", ""),
            abstract=_clean_text(item.get("abstract"))[:2400],
            source_database="Crossref",
            source_query=query,
            relevance=float(limit - rank),
        )
        article.ref_id = _stable_ref_id(article)
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
        published = _clean_text(entry.findtext(f"{atom}published"))
        year = int(published[:4]) if re.match(r"^\d{4}", published) else None
        if year_from and year and year < year_from:
            continue

        entry_url = _clean_text(entry.findtext(f"{atom}id"))
        arxiv_id = entry_url.rstrip("/").rsplit("/", 1)[-1]
        article = Article(
            ref_id="",
            title=_clean_text(entry.findtext(f"{atom}title")),
            authors=[
                _clean_text(author.findtext(f"{atom}name"))
                for author in entry.findall(f"{atom}author")
            ][:8],
            year=year,
            venue="arXiv",
            doi="",
            url=entry_url,
            abstract=_clean_text(entry.findtext(f"{atom}summary"))[:2400],
            source_database="arXiv",
            source_query=query,
            relevance=float(limit - rank),
        )
        doi_node = entry.find("{http://arxiv.org/schemas/atom}doi")
        if doi_node is not None and doi_node.text:
            article.doi = _normalize_doi(doi_node.text)
            article.url = f"https://doi.org/{quote(article.doi, safe='/()')}"
        elif arxiv_id:
            article.url = f"https://arxiv.org/abs/{arxiv_id}"
        article.ref_id = _stable_ref_id(article)
        if article.title:
            articles.append(article)
    return articles


def _same_article(left: Article, right: Article) -> bool:
    if left.doi and right.doi:
        return _normalize_doi(left.doi) == _normalize_doi(right.doi)
    left_title = _normalize_title(left.title)
    right_title = _normalize_title(right.title)
    if not left_title or not right_title:
        return False
    if left_title == right_title:
        return True
    return SequenceMatcher(None, left_title, right_title).ratio() >= 0.94


def _merge_article(kept: Article, candidate: Article) -> Article:
    if len(candidate.abstract) > len(kept.abstract):
        kept.abstract = candidate.abstract
    if not kept.doi and candidate.doi:
        kept.doi = candidate.doi
        kept.url = candidate.url
    if len(candidate.authors) > len(kept.authors):
        kept.authors = candidate.authors
    if not kept.venue and candidate.venue:
        kept.venue = candidate.venue
    if not kept.year and candidate.year:
        kept.year = candidate.year
    databases = set(kept.source_database.split(" + "))
    databases.update(candidate.source_database.split(" + "))
    kept.source_database = " + ".join(sorted(databases))
    kept.relevance = max(kept.relevance, candidate.relevance)
    kept.ref_id = _stable_ref_id(kept)
    return kept


def deduplicate_articles(articles: Iterable[Article]) -> tuple[list[Article], int]:
    unique: list[Article] = []
    duplicate_count = 0
    for candidate in articles:
        match = next((item for item in unique if _same_article(item, candidate)), None)
        if match is None:
            unique.append(candidate)
        else:
            _merge_article(match, candidate)
            duplicate_count += 1
    return unique, duplicate_count


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
