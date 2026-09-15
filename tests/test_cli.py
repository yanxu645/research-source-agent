import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from research_source_agent.cli import main


class EntryPointTests(TestCase):
    @patch("streamlit.web.cli.main")
    def test_web_resolves_packaged_app_and_forwards_options(self, run_web):
        with patch.object(sys, "argv", ["research-source-agent"]):
            main(["web", "--server.port=8510"])
            self.assertTrue(Path(sys.argv[2]).is_file())
            self.assertIn("interfaces", Path(sys.argv[2]).parts)
            self.assertEqual(sys.argv[-1], "--server.port=8510")
            run_web.assert_called_once_with()

    @patch("research_source_agent.interfaces.mcp.server.main")
    def test_mcp_dispatches_without_starting_web(self, run_mcp):
        main(["mcp"])
        run_mcp.assert_called_once_with()
