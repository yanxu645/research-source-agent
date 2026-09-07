from unittest import TestCase
from unittest.mock import patch
from datetime import datetime, timezone
from types import SimpleNamespace
import re
import xml.etree.ElementTree as ET
import requests
from research_source_agent.article_search import (
    Article,
    _normalize_title,
    _normalize_doi,
    deduplicate_articles,
    search_articles,
    search_arxiv,
)


def make_article(title: str, doi: str = "", abstract: str = "") -> Article:
    return Article(
        ref_id="S-TEST",
        title=title,
        authors=[],
        year=2025,
        venue="Test Journal",
        doi=doi,
        url="https://example.com/paper",
        abstract=abstract,
        source_database="Crossref",
        source_query="test",
    )


class ArticleDeduplicationTests(TestCase):
    def test_normalizes_doi_urls(self):
        self.assertEqual(_normalize_doi("https://doi.org/10.1000/ABC"), "10.1000/abc")

    def test_normalizes_title_punctuation_and_case(self):
        self.assertEqual(
            _normalize_title("Generative-AI: Writing!"),
            _normalize_title("generative ai writing"),
        )

    def test_deduplicates_matching_doi(self):
        first = make_article("First metadata title", "10.1000/test")
        second = make_article("Updated metadata title", "https://doi.org/10.1000/TEST")
        second.doi = _normalize_doi(second.doi)
        unique, removed = deduplicate_articles([first, second])
        self.assertEqual(len(unique), 1)
        self.assertEqual(removed, 1)

    def test_deduplicates_small_title_variation_and_keeps_richer_abstract(self):
        first = make_article("Generative AI in Higher Education", abstract="Short")
        second = make_article("Generative AI in higher-education", abstract="A much richer abstract")
        unique, removed = deduplicate_articles([first, second])
        self.assertEqual(removed, 1)
        self.assertEqual(unique[0].abstract, "A much richer abstract")

    def test_keeps_distinct_titles(self):
        first = make_article("AI literacy in universities")
        second = make_article("Academic integrity policy design")
        unique, removed = deduplicate_articles([first, second])
        self.assertEqual(len(unique), 2)
        self.assertEqual(removed, 0)

    def test_keeps_conflicting_dois_without_mixing_metadata(self):
        for title in (
            "Research on language learning: Part I",
            "Research on language learning: Part II",
        ):
            with self.subTest(title=title):
                first = make_article(
                    "Research on language learning: Part I", "10.1000/part1", "First"
                )
                second = make_article(title, "10.1000/part2", "Longer second abstract")
                unique, removed = deduplicate_articles([first, second])
                self.assertEqual(len(unique), 2)
                self.assertEqual(removed, 0)
                self.assertEqual(unique[0].abstract, "First")
                self.assertEqual(unique[1].doi, "10.1000/part2")

    def test_matches_doi_url_without_caller_normalization(self):
        first = make_article("First title", "10.1000/test")
        second = make_article("Different title", "https://doi.org/10.1000/TEST")
        unique, removed = deduplicate_articles([first, second])
        self.assertEqual(len(unique), 1)
        self.assertEqual(removed, 1)

    def test_title_fallback_enriches_missing_doi(self):
        first = make_article("Shared paper")
        second = make_article("Shared paper", "10.1000/shared")
        unique, removed = deduplicate_articles([first, second])
        self.assertEqual(removed, 1)
        self.assertEqual(unique[0].doi, "10.1000/shared")

    @patch("research_source_agent.article_search.search_arxiv")
    @patch("research_source_agent.article_search.search_crossref")
    def test_aggregates_providers_and_reports_duplicates(self, crossref, arxiv):
        crossref.return_value = [make_article("Shared research paper", "10.1000/shared")]
        duplicate = make_article("Shared research paper", "10.1000/shared", "Rich abstract")
        duplicate.source_database = "arXiv"
        arxiv.return_value = [duplicate]

        result = search_articles("research topic", year_from=2022, limit=8)

        self.assertEqual(result["unique_count"], 1)
        self.assertEqual(result["duplicates_removed"], 1)
        self.assertEqual(result["articles"][0]["source_database"], "Crossref + arXiv")

    @patch("research_source_agent.article_search.search_arxiv")
    @patch("research_source_agent.article_search.search_crossref")
    def test_keeps_partial_results_when_one_provider_times_out(self, crossref, arxiv):
        crossref.side_effect = requests.Timeout("timeout")
        arxiv.return_value = [make_article("Available arXiv paper")]

        result = search_articles("research topic", year_from=2022, limit=8)

        self.assertEqual(result["unique_count"], 1)
        self.assertEqual(len(result["warnings"]), 1)
        self.assertIn("crossref", result["warnings"][0])


class ArxivYearFilterTests(TestCase):
    def setUp(self):
        clock_patch = patch("research_source_agent.article_search.datetime")
        clock = clock_patch.start()
        self.addCleanup(clock_patch.stop)
        clock.now.return_value = datetime(2026, 9, 7, 9, 0, tzinfo=timezone.utc)

    @staticmethod
    def response_for(records):
        root = ET.Element("feed", xmlns="http://www.w3.org/2005/Atom")
        for title, published in records:
            entry = ET.SubElement(root, "entry")
            ET.SubElement(entry, "id").text = "https://arxiv.org/abs/2501.00001v1"
            ET.SubElement(entry, "title").text = title
            ET.SubElement(entry, "published").text = published
        return SimpleNamespace(
            text=ET.tostring(root, encoding="unicode"), raise_for_status=lambda: None
        )

    @patch("research_source_agent.article_search.requests.get")
    def test_filters_before_provider_truncates_results(self, get):
        records = [
            ("Older relevant paper", "2024-12-31T23:59:00Z"),
            ("New eligible paper", "2025-01-01T00:00:00Z"),
        ]

        def provider(url, *, params, **kwargs):
            selected = records
            dates = re.search(
                r"submittedDate:\[(\d{12}) TO (\d{12})\]", params["search_query"]
            )
            if dates:
                selected = [
                    record for record in records
                    if dates[1] <= re.sub(r"\D", "", record[1])[:12] <= dates[2]
                ]
            return self.response_for(selected[:params["max_results"]])

        get.side_effect = provider
        articles = search_arxiv("language learning", 2025, 1)
        self.assertEqual([article.title for article in articles], ["New eligible paper"])
        self.assertEqual(articles[0].year, 2025)

    @patch("research_source_agent.article_search.requests.get")
    def test_unrestricted_search_keeps_older_papers(self, get):
        get.return_value = self.response_for([("Older paper", "2020-01-01T00:00:00Z")])
        articles = search_arxiv("topic", None, 1)
        self.assertEqual(articles[0].year, 2020)
        self.assertNotIn("submittedDate", get.call_args.kwargs["params"]["search_query"])

    @patch("research_source_agent.article_search.requests.get")
    def test_retains_local_year_guard(self, get):
        get.return_value = self.response_for([
            ("Old paper", "2024-12-31T23:59:00Z"),
            ("Boundary paper", "2025-01-01T00:00:00Z"),
        ])
        articles = search_arxiv("topic", 2025, 2)
        self.assertEqual([article.title for article in articles], ["Boundary paper"])

    @patch("research_source_agent.article_search.requests.get")
    def test_future_year_returns_empty_without_invalid_range(self, get):
        self.assertEqual(search_arxiv("topic", 2027, 1), [])
        get.assert_not_called()
