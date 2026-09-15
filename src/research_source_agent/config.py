"""Runtime configuration loaded from environment variables."""

from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_base_url: str | None
    openai_model: str


def load_settings(env_file: str | Path | None = None) -> Settings:
    """Load local defaults at startup; deployment variables take precedence."""
    path = env_file or os.getenv("RESEARCH_ENV_FILE") or Path.cwd() / ".env"
    load_dotenv(dotenv_path=path, override=False)
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_base_url=os.getenv("OPENAI_BASE_URL") or None,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
    )


def configure_langsmith(project_name: str) -> None:
    """Attach traces to this project when LangSmith is configured."""
    if os.getenv("LANGSMITH_API_KEY"):
        os.environ.setdefault("LANGSMITH_TRACING", "true")
        os.environ.setdefault("LANGSMITH_PROJECT", project_name)
