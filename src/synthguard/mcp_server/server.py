"""FastMCP stdio server exposing the safe SynthGuard workflow."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import NoReturn

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import ValidationError

from synthguard.data_core import DataCoreError, GenerationMethod
from synthguard.evaluation_core import EvaluationCoreError
from synthguard.quality_gate import GatePolicy, QualityGateError

from .contracts import GateCandidateInput
from .paths import McpServerError, PathPolicy
from .tools import SynthGuardTools

_EXPECTED_ERRORS = (
    McpServerError,
    DataCoreError,
    EvaluationCoreError,
    QualityGateError,
    ValidationError,
)


def create_server(path_policy: PathPolicy) -> FastMCP:
    """Create an independently testable server with an explicit filesystem policy."""

    tools = SynthGuardTools(path_policy)
    server = FastMCP(
        "SynthGuard",
        instructions=(
            "Local synthetic-data generation and evidence tools. A passing gate is not a "
            "privacy, anonymity, or compliance guarantee."
        ),
    )

    @server.tool
    def profile_dataset(source_csv: str) -> dict[str, object]:
        """Profile one allowed CSV without returning source rows."""

        return _safe_call(lambda: tools.profile_dataset(source_csv))

    @server.tool
    def generate_synthetic_data(
        source_csv: str,
        output_directory: str,
        method: GenerationMethod,
        row_count: int,
        random_seed: int = 42,
    ) -> dict[str, object]:
        """Generate one immutable synthetic artifact run inside an allowed directory."""

        return _safe_call(
            lambda: tools.generate_synthetic_data(
                source_csv,
                output_directory,
                method,
                row_count,
                random_seed,
            )
        )

    @server.tool
    def evaluate_synthetic_data(
        real_csv: str,
        synthetic_csv: str,
        metadata_json: str,
        classification_target: str | None = None,
        random_seed: int = 42,
        max_privacy_rows: int = 5_000,
    ) -> dict[str, object]:
        """Measure fidelity, copy risk, DCR, and optional classification utility."""

        return _safe_call(
            lambda: tools.evaluate_synthetic_data(
                real_csv,
                synthetic_csv,
                metadata_json,
                classification_target,
                random_seed,
                max_privacy_rows,
            )
        )

    @server.tool
    def gate_candidates(
        candidates: list[GateCandidateInput],
        policy: GatePolicy | None = None,
    ) -> dict[str, object]:
        """Apply explicit thresholds and deterministically rank evaluation results."""

        return _safe_call(lambda: tools.gate_candidates(candidates, policy or GatePolicy()))

    @server.tool
    def run_synthguard_workflow(
        source_csv: str,
        output_directory: str,
        methods: list[GenerationMethod],
        row_count: int,
        random_seed: int = 42,
        classification_target: str | None = None,
        policy: GatePolicy | None = None,
    ) -> dict[str, object]:
        """Generate, evaluate, gate, and report selected candidate methods."""

        return _safe_call(
            lambda: tools.run_synthguard_workflow(
                source_csv,
                output_directory,
                methods,
                row_count,
                random_seed,
                classification_target,
                policy or GatePolicy(),
            )
        )

    return server


def _safe_call[ResultT](operation: Callable[[], ResultT]) -> ResultT:
    try:
        return operation()
    except _EXPECTED_ERRORS as error:
        _raise_tool_error(error)


def _raise_tool_error(error: Exception) -> NoReturn:
    if hasattr(error, "to_dict"):
        payload = error.to_dict()
    elif isinstance(error, ValidationError):
        payload = {
            "code": "INVALID_REQUEST",
            "message": "The tool request is invalid.",
            "details": {},
        }
    else:
        payload = {"code": "TOOL_FAILED", "message": "The tool failed.", "details": {}}
    raise ToolError(json.dumps(payload, sort_keys=True)) from error


mcp = create_server(PathPolicy.from_environment())


def run_server() -> None:
    """Run the local stdio transport used by MCP desktop clients."""

    mcp.run()


if __name__ == "__main__":
    run_server()
