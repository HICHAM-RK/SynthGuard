"""Public demo regression test."""

from pathlib import Path

from synthguard.data_core import GenerationMethod
from synthguard.quality_gate import GatePolicy, GateStatus
from synthguard.workflow import run_workflow

PROJECT_ROOT = Path(__file__).parents[2]


def test_committed_demo_completes_fast_workflow(tmp_path: Path) -> None:
    run = run_workflow(
        source_csv=PROJECT_ROOT / "examples/demo_customers.csv",
        output_directory=tmp_path,
        methods=(GenerationMethod.GAUSSIAN_COPULA,),
        row_count=100,
        random_seed=42,
        classification_target=None,
        policy=GatePolicy(),
    )

    decision = run.gate.candidates[0]
    generation = run.generations[decision.candidate_id]

    assert decision.status is GateStatus.PASS
    assert run.gate.winner_candidate_id == GenerationMethod.GAUSSIAN_COPULA.value
    assert generation.artifacts.synthetic_csv.is_file()
    assert generation.artifacts.metadata_json.is_file()
    assert generation.artifacts.manifest_json.is_file()
    assert "not an anonymity or compliance guarantee" in run.report_markdown.lower()
