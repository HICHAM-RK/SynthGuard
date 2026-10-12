"""Typed contracts shared by every SynthGuard data-core consumer."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContractModel(BaseModel):
    """Immutable base model that rejects accidental contract expansion."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class GenerationMethod(StrEnum):
    GAUSSIAN_COPULA = "gaussian_copula"
    CTGAN = "ctgan"


class PhysicalType(StrEnum):
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    STRING = "string"
    DATETIME = "datetime"
    UNKNOWN = "unknown"


class SemanticType(StrEnum):
    NUMERICAL = "numerical"
    CATEGORICAL = "categorical"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    IDENTIFIER = "identifier"
    UNKNOWN = "unknown"


def _validate_non_empty_path(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        raise ValueError("path must not be empty")
    if isinstance(value, Path) and str(value).strip() in {"", "."}:
        raise ValueError("path must not be empty")
    return value


class ProfileRequest(ContractModel):
    source_path: Path
    max_bytes: int = Field(default=25_000_000, ge=1)
    max_rows: int = Field(default=100_000, ge=1)

    _source_path_not_empty = field_validator("source_path", mode="before")(_validate_non_empty_path)


class GenerationRequest(ContractModel):
    source_path: Path
    output_directory: Path
    method: GenerationMethod
    row_count: int = Field(ge=1, le=100_000)
    random_seed: int
    column_overrides: dict[str, SemanticType] = Field(default_factory=dict)

    _source_path_not_empty = field_validator("source_path", mode="before")(_validate_non_empty_path)
    _output_path_not_empty = field_validator("output_directory", mode="before")(
        _validate_non_empty_path
    )


class DatasetWarning(ContractModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    column_name: str | None = None


class ColumnProfile(ContractModel):
    name: str = Field(min_length=1)
    physical_type: PhysicalType
    semantic_type: SemanticType
    is_sensitive_candidate: bool = False
    sensitivity_reason: str | None = None
    null_rate: float = Field(ge=0.0, le=1.0)
    unique_rate: float = Field(ge=0.0, le=1.0)
    cardinality: int = Field(ge=0)
    safe_summary: dict[str, Any] = Field(default_factory=dict)


class DatasetProfile(ContractModel):
    dataset_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    columns: tuple[ColumnProfile, ...]
    warnings: tuple[DatasetWarning, ...] = ()
    inferred_metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactPaths(ContractModel):
    synthetic_csv: Path
    metadata_json: Path
    manifest_json: Path


class GenerationResult(ContractModel):
    run_id: UUID
    method: GenerationMethod
    row_count: int = Field(ge=1, le=100_000)
    random_seed: int
    dataset_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    artifacts: ArtifactPaths
    training_duration_seconds: float = Field(ge=0.0)
    warnings: tuple[DatasetWarning, ...] = ()


class DataCoreError(Exception):
    """Expected data-core failure with a stable machine-readable code."""

    def __init__(self, code: str, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})

    def to_dict(self) -> dict[str, object]:
        return {"code": self.code, "message": self.message, "details": self.details}
