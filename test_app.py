from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest

from research_source_agent.agent import AgentResult, ToolEvent


class SearchWarningTests(TestCase):
    def setUp(self):
        st.cache_resource.clear()
        self.addCleanup(st.cache_resource.clear)

    @patch("research_source_agent.agent.ResearchSourceAgent")
    def test_warnings_survive_reruns_and_followups_until_new_research(self, agent_class):
        warning = "crossref temporarily unavailable"
        agent_class.return_value.run.side_effect = [
            AgentResult(
                answer="Partial results",
                tool_events=[ToolEvent(name="search", warnings=[warning])],
            ),
            AgentResult(answer="Follow-up answer", tool_events=[]),
        ]
        app = AppTest.from_file(
            str(Path(__file__).with_name("app.py")), default_timeout=20
        ).run()
        self.assertFalse(app.exception)
        app.chat_input[0].set_value("Find papers").run()
        self.assertFalse(app.exception)
        self.assertEqual([item.value for item in app.warning], [warning])
        self.assertEqual(app.session_state.messages[-1]["warnings"], [warning])

        app.run()
        self.assertEqual([item.value for item in app.warning], [warning])
        app.chat_input[0].set_value("Summarize the results").run()
        self.assertFalse(app.exception)
        # AppTest can retain stale element deltas after the app's st.rerun().
        app.run()
        self.assertEqual([item.value for item in app.warning], [warning])
        self.assertEqual(app.session_state.messages[-1]["warnings"], [])

        previous_thread = app.session_state.thread_id
        app.sidebar.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(list(app.warning), [])
        self.assertEqual(app.session_state.messages, [])
        self.assertNotEqual(app.session_state.thread_id, previous_thread)
