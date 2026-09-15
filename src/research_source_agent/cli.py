"""Installed command-line entry points."""

from __future__ import annotations

import argparse
import sys
from importlib.resources import as_file, files


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Scholarly research agent")
    parser.add_argument("interface", choices=("web", "mcp"))
    args, extra = parser.parse_known_args(argv)
    if args.interface == "mcp":
        if extra:
            parser.error("MCP does not accept additional arguments")
        from research_source_agent.interfaces.mcp.server import main as run_mcp

        run_mcp()
        return

    from streamlit.web import cli as streamlit_cli

    app = files("research_source_agent.interfaces.web").joinpath("app.py")
    with as_file(app) as app_path:
        sys.argv = [
            "streamlit", "run", str(app_path),
            "--server.address=127.0.0.1", "--server.port=8502",
            "--server.headless=true", "--browser.gatherUsageStats=false",
            *extra,
        ]
        streamlit_cli.main()
