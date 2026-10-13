"""Smoke-test the installed distribution without importing the source checkout."""

from __future__ import annotations

import asyncio
from importlib.metadata import entry_points, version
from pathlib import Path
from tempfile import TemporaryDirectory

import synthguard
from synthguard.mcp_server.paths import PathPolicy
from synthguard.mcp_server.server import create_server

EXPECTED_TOOLS = {
    "evaluate_synthetic_data",
    "gate_candidates",
    "generate_synthetic_data",
    "profile_dataset",
    "run_synthguard_workflow",
}


async def _verify() -> None:
    assert version("synthguard") == "0.1.0"
    assert synthguard.__all__ == ["WorkflowRun", "build_markdown_report", "run_workflow"]
    assert any(point.name == "synthguard-mcp" for point in entry_points(group="console_scripts"))

    with TemporaryDirectory(prefix="synthguard-smoke-") as root:
        server = create_server(PathPolicy((Path(root),)))
        tools = await server.list_tools()
        assert {tool.name for tool in tools} == EXPECTED_TOOLS


if __name__ == "__main__":
    asyncio.run(_verify())
