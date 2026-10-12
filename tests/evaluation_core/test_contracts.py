from pathlib import Path

import pytest
from pydantic import ValidationError

import synthguard.evaluation_core as evaluation_core
from synthguard.evaluation_core import (
    ClassificationUtilityResult,
    ColumnQualityScore,
    EvaluationCoreError,
    EvaluationRequest,
    EvaluationResult,
    EvaluationWarning,
    PrivacyEvidenceResult,
    StatisticalQualityResult,
    WeakArea,
)


@pytest.mark.parametrize("field_name", ["real_csv", "synthetic_csv", "metadata_json"])
@pytest.mark.parametrize("empty_path", ["", Path(".")])
def test_evaluation_request_rejects_empty_paths(field_name: str, empty_path: object) -> None:
    values: dict[str, object] = {
        "real_csv": Path("real.csv"),
        "synthetic_csv": Path("synthetic.csv"),
        "metadata_json": Path("metadata.json"),
    }
    values[field_name] = empty_path

    with pytest.raises(ValidationError):
        EvaluationRequest(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("max_privacy_rows", [99, 50_001])
def test_evaluation_request_rejects_out_of_range_privacy_limit(
    max_privacy_rows: int,
) -> None:
    with pytest.raises(ValidationError):
        EvaluationRequest(
            real_csv=Path("real.csv"),
            synthetic_csv=Path("synthetic.csv"),
            metadata_json=Path("metadata.json"),
            max_privacy_rows=max_privacy_rows,
        )


@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_quality_score_rejects_values_outside_unit_interval(score: float) -> None:
    with pytest.raises(ValidationError):
        ColumnQualityScore(column_name="age", score=score)


@pytest.mark.parametrize("distance", [-0.01, -1.0])
def test_privacy_evidence_rejects_negative_distances(distance: float) -> None:
    with pytest.raises(ValidationError):
        _privacy_evidence(nearest_distance_min=distance)


def test_evaluation_result_is_immutable_and_json_serializable() -> None:
    result = EvaluationResult(
        real_fingerprint="a" * 64,
        synthetic_fingerprint="b" * 64,
        real_row_count=100,
        synthetic_row_count=100,
        column_count=3,
        statistical=StatisticalQualityResult(
            overall_score=0.91,
            column_shapes_score=0.94,
            column_pair_trends_score=0.88,
            column_scores=(ColumnQualityScore(column_name="age", score=0.95),),
            weakest_areas=(WeakArea(kind="column_shape", name="income", score=0.71),),
            metric_provenance="SDMetrics QualityReport",
        ),
        privacy=_privacy_evidence(),
        utility=ClassificationUtilityResult(
            target_name="churned",
            class_count=2,
            real_train_rows=80,
            real_test_rows=20,
            synthetic_train_rows=100,
            metric_name="weighted_f1",
            real_train_score=0.8,
            synthetic_train_score=0.72,
            utility_retention=0.9,
            model_parameters={"solver": "lbfgs", "max_iter": 1_000},
        ),
        warnings=(EvaluationWarning(code="EXAMPLE", message="A safe warning."),),
        evaluation_duration_seconds=0.4,
    )

    assert '"overall_score":0.91' in result.model_dump_json()
    with pytest.raises(ValidationError):
        result.real_row_count = 101  # type: ignore[misc]


def test_utility_retention_may_exceed_one() -> None:
    utility = ClassificationUtilityResult(
        target_name="label",
        class_count=2,
        real_train_rows=80,
        real_test_rows=20,
        synthetic_train_rows=100,
        metric_name="weighted_f1",
        real_train_score=0.7,
        synthetic_train_score=0.8,
        utility_retention=0.8 / 0.7,
        model_parameters={},
    )

    assert utility.utility_retention > 1.0


def test_evaluation_core_error_exposes_machine_readable_payload() -> None:
    error = EvaluationCoreError(
        code="SCHEMA_MISMATCH",
        message="The evaluated schemas do not match.",
        details={"expected_column_count": 3},
    )

    assert str(error) == "The evaluated schemas do not match."
    assert error.to_dict() == {
        "code": "SCHEMA_MISMATCH",
        "message": "The evaluated schemas do not match.",
        "details": {"expected_column_count": 3},
    }


def test_package_exports_only_the_contract_surface() -> None:
    assert set(evaluation_core.__all__) == {
        "ClassificationUtilityResult",
        "ColumnQualityScore",
        "EvaluationCoreError",
        "EvaluationRequest",
        "EvaluationResult",
        "EvaluationWarning",
        "PrivacyEvidenceResult",
        "StatisticalQualityResult",
        "WeakArea",
    }


def _privacy_evidence(**overrides: float) -> PrivacyEvidenceResult:
    values: dict[str, object] = {
        "exact_match_count": 0,
        "exact_match_rate": 0.0,
        "near_duplicate_count": 1,
        "nearest_distance_min": 0.1,
        "nearest_distance_fifth_percentile": 0.2,
        "nearest_distance_median": 0.6,
        "distance_threshold": 0.05,
        "dcr_baseline_protection_score": 0.85,
        "sampled_real_rows": 100,
        "sampled_synthetic_rows": 100,
        "sampling_seed": 42,
        "excluded_identifier_columns": ("customer_id",),
        "metric_provenance": "normalized mixed-type distance and SDMetrics DCR",
    }
    values.update(overrides)
    return PrivacyEvidenceResult(**values)  # type: ignore[arg-type]
