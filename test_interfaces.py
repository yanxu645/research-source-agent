import json
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from research_source_agent.agent import ResearchSourceAgent, content_to_str
from research_source_agent.mcp_server import mcp, search_research_sources
from research_source_agent.tools import search_scholarly_articles


class FakeGraph:
    def __init__(self, previous_messages, result_messages):
        self.previous_messages = previous_messages
        self.result_messages = result_messages

    def get_state(self, config):
        return SimpleNamespace(values={"messages": self.previous_messages})

    def invoke(self, inputs, config):
        return {"messages": self.result_messages}


class AgentInterfaceTests(TestCase):
    def test_returns_string_answer_for_follow_up(self):
        previous = [HumanMessage(content="earlier question")]
        agent = object.__new__(ResearchSourceAgent)
        agent.graph = FakeGraph(previous, [*previous, AIMessage(content="answer")])

        result = agent.run("new question", "thread-1")

        self.assertEqual(result.answer, "answer")
        self.assertEqual(result.tool_events, [])

    def test_extracts_tool_event(self):
        payload = {
            "query": "research topic",
            "unique_count": 1,
            "duplicates_removed": 2,
            "warnings": [],
            "articles": [{"ref_id": "S-1234567"}],
        }
        messages = [
            ToolMessage(
                content=json.dumps(payload),
                name="search_scholarly_articles",
                tool_call_id="call-1",
            ),
            AIMessage(content="answer"),
        ]
        agent = object.__new__(ResearchSourceAgent)
        agent.graph = FakeGraph([], messages)

        result = agent.run("question", "thread-1")

        self.assertEqual(result.tool_events[0].query, "research topic")
        self.assertEqual(result.tool_events[0].articles, payload["articles"])

    def test_keeps_malformed_tool_event_without_crashing(self):
        messages = [
            ToolMessage(content="not json", name="search", tool_call_id="call-1"),
            AIMessage(content="answer"),
        ]
        agent = object.__new__(ResearchSourceAgent)
        agent.graph = FakeGraph([], messages)

        result = agent.run("question", "thread-1")

        self.assertEqual(result.tool_events[0].name, "search")
        self.assertEqual(result.tool_events[0].query, "")

    def test_converts_mixed_content_blocks(self):
        self.assertEqual(content_to_str([{"text": "A"}, 7]), "A7")


class ToolInterfaceTests(TestCase):
    def test_mcp_tool_is_registered(self):
        self.assertIsNotNone(mcp._tool_manager.get_tool("search_research_sources"))

    @patch("research_source_agent.tools.search_articles")
    def test_langchain_tool_passes_selected_sources(self, search_articles):
        search_articles.return_value = {"articles": []}

        output = search_scholarly_articles.invoke(
            {"query": "topic", "source": ["arxiv"]}
        )

        search_articles.assert_called_once_with(
            query="topic",
            year_from=None,
            limit=8,
            sources=["arxiv"],
        )
        self.assertEqual(json.loads(output), {"articles": []})

    @patch("research_source_agent.mcp_server.search_articles")
    def test_mcp_tool_passes_selected_sources(self, search_articles):
        search_articles.return_value = {"articles": []}

        output = search_research_sources("topic", source=["crossref"])

        self.assertEqual(output, {"articles": []})
        search_articles.assert_called_once_with(
            query="topic",
            year_from=None,
            limit=8,
            sources=["crossref"],
        )
