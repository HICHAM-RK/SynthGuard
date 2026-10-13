from __future__ import annotations

import shutil
from pathlib import Path

from synthguard.data_core import GenerationMethod
from synthguard.mcp_server.contracts import GateCandidateInput
from synthguard.mcp_server.paths import PathPolicy
from synthguard.mcp_server.tools import SynthGuardTools
from synthguard.quality_gate import GatePolicy

FIXTURE = Path(__file__).parents[1] / "data_core" / "fixtures" / "mixed_types.csv"


def test_tool_adapter_profiles_generates_evaluates_and_gates(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    shutil.copyfile(FIXTURE, source)
    tools = SynthGuardTools(PathPolicy((tmp_path,)))

    profile = tools.profile_dataset(str(source))
    generated = tools.generate_synthetic_data(
        str(source),
        str(tmp_path / "runs"),
        GenerationMethod.GAUSSIAN_COPULA,
        20,
        42,
    )
    artifacts = generated["artifacts"]
    assert isinstance(artifacts, dict)
    evaluation = tools.evaluate_synthetic_data(
        str(source),
        str(artifacts["synthetic_csv"]),
        str(artifacts["metadata_json"]),
        None,
        42,
        100,
    )
    gate = tools.gate_candidates(
        [GateCandidateInput(candidate_id="gaussian", evaluation=evaluation)],
        GatePolicy(),
    )

    assert profile["row_count"] == 4
    assert generated["method"] == "gaussian_copula"
    assert evaluation["synthetic_row_count"] == 20
    assert gate["candidates"][0]["candidate_id"] == "gaussian"


def test_complete_workflow_returns_artifacts_evidence_gate_and_report(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    shutil.copyfile(FIXTURE, source)
    tools = SynthGuardTools(PathPolicy((tmp_path,)))

    result = tools.run_synthguard_workflow(
        str(source),
        str(tmp_path / "workflow-runs"),
        [GenerationMethod.GAUSSIAN_COPULA],
        20,
        7,
        None,
        GatePolicy(),
    )

    assert set(result) == {"generations", "evaluations", "gate", "report_markdown"}
    assert set(result["generations"]) == {"gaussian_copula"}
    assert "# SynthGuard evidence report" in result["report_markdown"]
    assert "not formal privacy proofs" in result["report_markdown"]
