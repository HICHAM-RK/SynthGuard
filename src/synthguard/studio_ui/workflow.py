"""Framework-independent orchestration used by the Streamlit studio."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from synthguard.data_core import (
    GenerationMethod,
    GenerationRequest,
    GenerationResult,
    generate_candidate,
)
from synthguard.evaluation_core import EvaluationRequest, EvaluationResult, evaluate_candidate
from synthguard.quality_gate import (
    CandidateEvidence,
    GatePolicy,
    GateRequest,
    GateResult,
    apply_quality_gate,
)

from .reporting import build_markdown_report


@dataclass(frozen=True, slots=True)
class StudioRun:
    generations: dict[str, GenerationResult]
    evaluations: dict[str, EvaluationResult]
    gate: GateResult
    report_markdown: str


def run_studio_workflow(
    *,
    source_csv: Path,
    output_directory: Path,
    methods: tuple[GenerationMethod, ...],
    row_count: int,
    random_seed: int,
    classification_target: str | None,
    policy: GatePolicy,
) -> StudioRun:
    """Generate, evaluate, and rank selected methods through public APIs."""

    generations: dict[str, GenerationResult] = {}
    evaluations: dict[str, EvaluationResult] = {}
    for method in methods:
        candidate_id = method.value
        generated = generate_candidate(
            GenerationRequest(
                source_path=source_csv,
                output_directory=output_directory,
                method=method,
                row_count=row_count,
                random_seed=random_seed,
            )
        )
        evaluation = evaluate_candidate(
            EvaluationRequest(
                real_csv=source_csv,
                synthetic_csv=generated.artifacts.synthetic_csv,
                metadata_json=generated.artifacts.metadata_json,
                classification_target=classification_target,
                random_seed=random_seed,
            )
        )
        generations[candidate_id] = generated
        evaluations[candidate_id] = evaluation

    gate = apply_quality_gate(
        GateRequest(
            candidates=tuple(
                CandidateEvidence(candidate_id=candidate_id, evaluation=evaluation)
                for candidate_id, evaluation in evaluations.items()
            ),
            policy=policy,
        )
    )
    return StudioRun(
        generations=generations,
        evaluations=evaluations,
        gate=gate,
        report_markdown=build_markdown_report(gate, evaluations),
    )
