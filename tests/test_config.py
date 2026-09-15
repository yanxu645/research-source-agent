"""Configuration must work without a checkout or real credentials."""

import os
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from research_source_agent.config import load_settings


class SettingsTests(TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_environment_overrides_local_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "OPENAI_API_KEY=file-key\nOPENAI_MODEL=file-model\n"
                "OPENAI_BASE_URL=https://provider.example/v1\n",
                encoding="utf-8",
            )
            os.environ["OPENAI_API_KEY"] = "deployment-key"
            settings = load_settings(path)
        self.assertEqual(settings.openai_api_key, "deployment-key")
        self.assertEqual(settings.openai_model, "file-model")
        self.assertEqual(settings.openai_base_url, "https://provider.example/v1")

    @patch.dict(os.environ, {}, clear=True)
    def test_explicit_env_file_works_outside_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "custom.env"
            path.write_text("OPENAI_MODEL=custom-model\n", encoding="utf-8")
            os.environ["RESEARCH_ENV_FILE"] = str(path)
            settings = load_settings()
        self.assertEqual(settings.openai_model, "custom-model")

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_env_file_uses_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = load_settings(Path(directory) / "missing.env")
        self.assertEqual(settings.openai_api_key, "")
        self.assertIsNone(settings.openai_base_url)
        self.assertEqual(settings.openai_model, "gpt-4.1-mini")
