"""Article metadata, normalization and deterministic deduplication."""

from __future__ import annotations

import hashlib
import html
import re
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from typing import Iterable


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


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def normalize_doi(value: str | None) -> str:
    if not value:
        return ""
    doi = value.strip().lower()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
    return re.sub(r"^doi:\s*", "", doi).strip()


def normalize_title(value: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", value.lower())


def stable_ref_id(article: Article) -> str:
    identity = article.doi or article.url or normalize_title(article.title)
    digest = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:7].upper()
    return f"S-{digest}"


def _same_article(left: Article, right: Article) -> bool:
    if left.doi and right.doi:
        return normalize_doi(left.doi) == normalize_doi(right.doi)
    left_title = normalize_title(left.title)
    right_title = normalize_title(right.title)
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
    kept.ref_id = stable_ref_id(kept)
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
