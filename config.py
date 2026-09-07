"""Runtime configuration loaded from environment variables."""

from __future__ import annotations
import os
from dotenv import load_dotenv


# Keep local development settings editable in .env even when the shell has
# variables with the same names. Values omitted from .env remain untouched.
load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or None
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def configure_langsmith(project_name: str) -> None:
    """Attach traces to this project when LangSmith is configured."""
    if os.getenv("LANGSMITH_API_KEY"):
        os.environ.setdefault("LANGSMITH_TRACING", "true")
        os.environ.setdefault("LANGSMITH_PROJECT", project_name)
