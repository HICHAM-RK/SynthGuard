from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastmcp import Client

from synthguard.mcp_server.paths import PathPolicy
from synthguard.mcp_server.server import create_server


@pytest.mark.anyio
async def test_server_discovers_exact_documented_tool_surface(tmp_path: Path) -> None:
    server = create_server(PathPolicy((tmp_path,)))

    tools = await server.list_tools()

    assert {tool.name for tool in tools} == {
        "profile_dataset",
        "generate_synthetic_data",
        "evaluate_synthetic_data",
        "gate_candidates",
        "run_synthguard_workflow",
    }


@pytest.mark.anyio
async def test_path_failure_becomes_structured_mcp_tool_error(tmp_path: Path) -> None:
    server = create_server(PathPolicy((tmp_path,)))
    outside = tmp_path.parent / "outside.csv"
    outside.write_text("private-value\n", encoding="utf-8")

    async with Client(server) as client:
        result = await client.call_tool(
            "profile_dataset",
            {"source_csv": str(outside)},
            raise_on_error=False,
        )

    assert result.is_error
    payload = json.loads(result.content[0].text)
    assert payload["code"] == "PATH_NOT_ALLOWED"
    assert "private-value" not in result.content[0].text
    assert str(tmp_path) not in result.content[0].text
