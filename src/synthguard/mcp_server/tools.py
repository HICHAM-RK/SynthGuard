"""Framework-independent adapters behind the MCP tool surface."""

from __future__ import annotations

from synthguard import run_workflow
from synthguard.data_core import (
    GenerationMethod,
    GenerationRequest,
    ProfileRequest,
    generate_candidate,
    profile_csv,
)
from synthguard.evaluation_core import EvaluationRequest, evaluate_candidate
from synthguard.quality_gate import (
    CandidateEvidence,
    GatePolicy,
    GateRequest,
    apply_quality_gate,
)

from .contracts import GateCandidateInput
from .paths import PathPolicy


class SynthGuardTools:
    """Apply path policy, then delegate every calculation to public domain APIs."""

    def __init__(self, path_policy: PathPolicy) -> None:
        self._paths = path_policy

    def profile_dataset(self, source_csv: str) -> dict[str, object]:
        source = self._paths.input_file(source_csv)
        result = profile_csv(ProfileRequest(source_path=source))
        return result.model_dump(mode="json")

    def generate_synthetic_data(
        self,
        source_csv: str,
        output_directory: str,
        method: GenerationMethod,
        row_count: int,
        random_seed: int,
    ) -> dict[str, object]:
        source = self._paths.input_file(source_csv)
        output = self._paths.output_directory(output_directory)
        result = generate_candidate(
            GenerationRequest(
                source_path=source,
                output_directory=output,
                method=method,
                row_count=row_count,
                random_seed=random_seed,
            )
        )
        return result.model_dump(mode="json")

    def evaluate_synthetic_data(
        self,
        real_csv: str,
        synthetic_csv: str,
        metadata_json: str,
        classification_target: str | None,
        random_seed: int,
        max_privacy_rows: int,
    ) -> dict[str, object]:
        result = evaluate_candidate(
            EvaluationRequest(
                real_csv=self._paths.input_file(real_csv),
                synthetic_csv=self._paths.input_file(synthetic_csv),
                metadata_json=self._paths.input_file(metadata_json),
                classification_target=classification_target,
                random_seed=random_seed,
                max_privacy_rows=max_privacy_rows,
            )
        )
        return result.model_dump(mode="json")

    def gate_candidates(
        self,
        candidates: list[GateCandidateInput],
        policy: GatePolicy,
    ) -> dict[str, object]:
        result = apply_quality_gate(
            GateRequest(
                candidates=tuple(
                    CandidateEvidence(
                        candidate_id=candidate.candidate_id,
                        evaluation=candidate.evaluation,
                    )
                    for candidate in candidates
                ),
                policy=policy,
            )
        )
        return result.model_dump(mode="json")

    def run_synthguard_workflow(
        self,
        source_csv: str,
        output_directory: str,
        methods: list[GenerationMethod],
        row_count: int,
        random_seed: int,
        classification_target: str | None,
        policy: GatePolicy,
    ) -> dict[str, object]:
        run = run_workflow(
            source_csv=self._paths.input_file(source_csv),
            output_directory=self._paths.output_directory(output_directory),
            methods=tuple(methods),
            row_count=row_count,
            random_seed=random_seed,
            classification_target=classification_target,
            policy=policy,
        )
        return {
            "generations": {
                name: result.model_dump(mode="json") for name, result in run.generations.items()
            },
            "evaluations": {
                name: result.model_dump(mode="json") for name, result in run.evaluations.items()
            },
            "gate": run.gate.model_dump(mode="json"),
            "report_markdown": run.report_markdown,
        }
