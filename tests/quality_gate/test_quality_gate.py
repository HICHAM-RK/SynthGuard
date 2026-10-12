from __future__ import annotations

from itertools import permutations

import pytest
from pydantic import ValidationError

import synthguard.quality_gate as quality_gate
from synthguard.evaluation_core import (
    ClassificationUtilityResult,
    EvaluationResult,
    PrivacyEvidenceResult,
    StatisticalQualityResult,
)
from synthguard.quality_gate import (
    CandidateEvidence,
    CriterionStatus,
    GatePolicy,
    GateRequest,
    GateStatus,
    QualityGateError,
    apply_quality_gate,
)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("min_statistical_score", -0.01),
        ("max_exact_match_rate", 1.01),
        ("max_near_duplicate_rate", -0.01),
        ("min_dcr_score", 1.01),
        ("min_utility_retention", -0.01),
    ],
)
def test_policy_rejects_values_outside_unit_interval(field_name: str, value: float) -> None:
    with pytest.raises(ValidationError):
        GatePolicy(**{field_name: value})


def test_request_rejects_empty_candidates_and_ids() -> None:
    with pytest.raises(ValidationError):
        GateRequest(candidates=())
    with pytest.raises(ValidationError):
        CandidateEvidence(candidate_id=" ", evaluation=_evaluation())


def test_threshold_boundaries_are_inclusive() -> None:
    policy = GatePolicy(
        min_statistical_score=0.7,
        max_exact_match_rate=0.1,
        max_near_duplicate_rate=0.05,
        min_dcr_score=0.5,
        min_utility_retention=0.8,
        require_utility=True,
    )
    evidence = CandidateEvidence(
        candidate_id="boundary",
        evaluation=_evaluation(
            statistical_score=0.7,
            exact_match_rate=0.1,
            near_duplicate_count=5,
            dcr_score=0.5,
            utility_retention=0.8,
        ),
    )

    decision = apply_quality_gate(GateRequest(candidates=(evidence,), policy=policy)).candidates[0]

    assert decision.status is GateStatus.PASS
    assert [criterion.status for criterion in decision.criteria] == [CriterionStatus.PASS] * 5
    assert [criterion.comparator for criterion in decision.criteria] == [
        ">=",
        "<=",
        "<=",
        ">=",
        ">=",
    ]


def test_missing_optional_utility_is_explicitly_skipped() -> None:
    decision = apply_quality_gate(
        GateRequest(
            candidates=(CandidateEvidence(candidate_id="candidate", evaluation=_evaluation()),)
        )
    ).candidates[0]

    assert decision.status is GateStatus.PASS
    utility = decision.criteria[-1]
    assert utility.name == "utility_retention"
    assert utility.status is CriterionStatus.SKIPPED
    assert utility.observed_value is None


def test_missing_required_utility_fails_only_that_candidate() -> None:
    decision = apply_quality_gate(
        GateRequest(
            candidates=(CandidateEvidence(candidate_id="candidate", evaluation=_evaluation()),),
            policy=GatePolicy(require_utility=True),
        )
    ).candidates[0]

    assert decision.status is GateStatus.FAIL
    assert decision.criteria[-1].status is CriterionStatus.FAIL
    assert "required" in decision.criteria[-1].explanation.lower()


def test_undefined_utility_retention_fails_the_criterion() -> None:
    evaluation = _evaluation(utility_retention=0.8)
    assert evaluation.utility is not None
    evaluation = evaluation.model_copy(
        update={
            "utility": evaluation.utility.model_copy(update={"utility_retention": None}),
        }
    )

    decision = apply_quality_gate(
        GateRequest(
            candidates=(CandidateEvidence(candidate_id="candidate", evaluation=evaluation),)
        )
    ).candidates[0]

    assert decision.status is GateStatus.FAIL
    assert decision.criteria[-1].status is CriterionStatus.FAIL
    assert "undefined" in decision.criteria[-1].explanation.lower()


def test_ranking_is_stable_across_input_permutations() -> None:
    candidates = (
        CandidateEvidence(
            candidate_id="accepted-low", evaluation=_evaluation(statistical_score=0.71)
        ),
        CandidateEvidence(
            candidate_id="accepted-high", evaluation=_evaluation(statistical_score=0.95)
        ),
        CandidateEvidence(
            candidate_id="failed-high",
            evaluation=_evaluation(statistical_score=1.0, exact_match_rate=0.2),
        ),
    )

    orders = {
        tuple(
            decision.candidate_id
            for decision in apply_quality_gate(GateRequest(candidates=ordering)).candidates
        )
        for ordering in permutations(candidates)
    }

    assert orders == {("accepted-high", "accepted-low", "failed-high")}
    result = apply_quality_gate(GateRequest(candidates=candidates))
    assert result.winner_candidate_id == "accepted-high"
    assert [decision.rank for decision in result.candidates] == [1, 2, 3]


def test_ties_use_candidate_id_and_utility_above_one_is_capped() -> None:
    candidates = (
        CandidateEvidence(candidate_id="zeta", evaluation=_evaluation(utility_retention=1.2)),
        CandidateEvidence(candidate_id="alpha", evaluation=_evaluation(utility_retention=1.2)),
    )

    result = apply_quality_gate(GateRequest(candidates=candidates))

    assert [decision.candidate_id for decision in result.candidates] == ["alpha", "zeta"]
    assert all(0.0 <= decision.composite_score <= 1.0 for decision in result.candidates)


def test_all_failed_candidates_produce_no_winner_and_serialize() -> None:
    result = apply_quality_gate(
        GateRequest(
            candidates=(
                CandidateEvidence(
                    candidate_id="failed",
                    evaluation=_evaluation(statistical_score=0.2),
                ),
            )
        )
    )

    assert result.winner_candidate_id is None
    assert '"status":"fail"' in result.model_dump_json()


def test_duplicate_candidate_ids_raise_stable_error() -> None:
    candidate = CandidateEvidence(candidate_id="same", evaluation=_evaluation())

    with pytest.raises(QualityGateError) as caught:
        apply_quality_gate(GateRequest(candidates=(candidate, candidate)))

    assert caught.value.code == "DUPLICATE_CANDIDATE_ID"
    assert caught.value.to_dict() == {
        "code": "DUPLICATE_CANDIDATE_ID",
        "message": "Candidate identifiers must be unique.",
        "details": {"candidate_id": "same"},
    }


def test_package_exports_only_public_gate_surface() -> None:
    assert set(quality_gate.__all__) == {
        "CandidateDecision",
        "CandidateEvidence",
        "CriterionResult",
        "CriterionStatus",
        "GatePolicy",
        "GateRequest",
        "GateResult",
        "GateStatus",
        "QualityGateError",
        "apply_quality_gate",
    }


def _evaluation(
    *,
    statistical_score: float = 0.8,
    exact_match_rate: float = 0.0,
    near_duplicate_count: int = 0,
    dcr_score: float = 0.8,
    utility_retention: float | None = None,
) -> EvaluationResult:
    utility = None
    if utility_retention is not None:
        utility = ClassificationUtilityResult(
            target_name="label",
            class_count=2,
            real_train_rows=80,
            real_test_rows=20,
            synthetic_train_rows=100,
            metric_name="weighted_f1",
            real_train_score=0.5,
            synthetic_train_score=min(utility_retention * 0.5, 1.0),
            utility_retention=utility_retention,
            model_parameters={},
        )
    return EvaluationResult(
        real_fingerprint="a" * 64,
        synthetic_fingerprint="b" * 64,
        real_row_count=100,
        synthetic_row_count=100,
        column_count=2,
        statistical=StatisticalQualityResult(
            overall_score=statistical_score,
            column_shapes_score=statistical_score,
            column_pair_trends_score=statistical_score,
            column_scores=(),
            weakest_areas=(),
            metric_provenance="test",
        ),
        privacy=PrivacyEvidenceResult(
            exact_match_count=int(exact_match_rate * 100),
            exact_match_rate=exact_match_rate,
            near_duplicate_count=near_duplicate_count,
            nearest_distance_min=0.1,
            nearest_distance_fifth_percentile=0.2,
            nearest_distance_median=0.5,
            distance_threshold=0.05,
            dcr_baseline_protection_score=dcr_score,
            sampled_real_rows=100,
            sampled_synthetic_rows=100,
            sampling_seed=42,
            metric_provenance="test",
        ),
        utility=utility,
        evaluation_duration_seconds=0.1,
    )
