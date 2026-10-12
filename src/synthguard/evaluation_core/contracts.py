"""Typed contracts shared by every SynthGuard evaluation consumer."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContractModel(BaseModel):
    """Immutable base model that rejects accidental contract expansion."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


def _validate_non_empty_path(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        raise ValueError("path must not be empty")
    if isinstance(value, Path) and str(value).strip() in {"", "."}:
        raise ValueError("path must not be empty")
    return value


class EvaluationRequest(ContractModel):
    real_csv: Path
    synthetic_csv: Path
    metadata_json: Path
    classification_target: str | None = None
    random_seed: int = 42
    max_privacy_rows: int = Field(default=5_000, ge=100, le=50_000)

    _real_csv_not_empty = field_validator("real_csv", mode="before")(_validate_non_empty_path)
    _synthetic_csv_not_empty = field_validator("synthetic_csv", mode="before")(
        _validate_non_empty_path
    )
    _metadata_json_not_empty = field_validator("metadata_json", mode="before")(
        _validate_non_empty_path
    )


class EvaluationWarning(ContractModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ColumnQualityScore(ContractModel):
    column_name: str = Field(min_length=1)
    score: float = Field(ge=0.0, le=1.0)


class WeakArea(ContractModel):
    kind: str = Field(min_length=1)
    name: str = Field(min_length=1)
    score: float = Field(ge=0.0, le=1.0)


class StatisticalQualityResult(ContractModel):
    overall_score: float = Field(ge=0.0, le=1.0)
    column_shapes_score: float = Field(ge=0.0, le=1.0)
    column_pair_trends_score: float = Field(ge=0.0, le=1.0)
    column_scores: tuple[ColumnQualityScore, ...]
    weakest_areas: tuple[WeakArea, ...]
    metric_provenance: str = Field(min_length=1)


class PrivacyEvidenceResult(ContractModel):
    exact_match_count: int = Field(ge=0)
    exact_match_rate: float = Field(ge=0.0, le=1.0)
    near_duplicate_count: int = Field(ge=0)
    nearest_distance_min: float = Field(ge=0.0)
    nearest_distance_fifth_percentile: float = Field(ge=0.0)
    nearest_distance_median: float = Field(ge=0.0)
    distance_threshold: float = Field(ge=0.0)
    dcr_baseline_protection_score: float = Field(ge=0.0, le=1.0)
    sampled_real_rows: int = Field(ge=0)
    sampled_synthetic_rows: int = Field(ge=0)
    sampling_seed: int
    excluded_identifier_columns: tuple[str, ...] = ()
    metric_provenance: str = Field(min_length=1)


class ClassificationUtilityResult(ContractModel):
    target_name: str = Field(min_length=1)
    class_count: int = Field(ge=2)
    real_train_rows: int = Field(ge=1)
    real_test_rows: int = Field(ge=1)
    synthetic_train_rows: int = Field(ge=1)
    metric_name: Literal["weighted_f1"]
    real_train_score: float = Field(ge=0.0, le=1.0)
    synthetic_train_score: float = Field(ge=0.0, le=1.0)
    utility_retention: float = Field(ge=0.0)
    model_parameters: dict[str, str | int | float | bool] = Field(default_factory=dict)


class EvaluationResult(ContractModel):
    real_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    synthetic_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    real_row_count: int = Field(ge=1)
    synthetic_row_count: int = Field(ge=1)
    column_count: int = Field(ge=1)
    statistical: StatisticalQualityResult
    privacy: PrivacyEvidenceResult
    utility: ClassificationUtilityResult | None = None
    warnings: tuple[EvaluationWarning, ...] = ()
    evaluation_duration_seconds: float = Field(ge=0.0)


class EvaluationCoreError(Exception):
    """Expected evaluation failure with a stable machine-readable code."""

    def __init__(self, code: str, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})

    def to_dict(self) -> dict[str, object]:
        return {"code": self.code, "message": self.message, "details": self.details}
