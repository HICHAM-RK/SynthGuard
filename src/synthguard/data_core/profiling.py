"""Deterministic, value-safe profiling for validated tabular data."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from .contracts import (
    ColumnProfile,
    DatasetProfile,
    DatasetWarning,
    PhysicalType,
    ProfileRequest,
    SemanticType,
)
from .ingestion import LoadedDataset, read_validated_csv

_SENSITIVE_NAME_PARTS = {
    "address",
    "birth",
    "dob",
    "email",
    "name",
    "passport",
    "phone",
    "ssn",
}


def profile_csv(request: ProfileRequest) -> DatasetProfile:
    """Validate and profile one CSV without returning raw source values."""

    loaded = read_validated_csv(request)
    return build_profile(loaded)


def build_profile(loaded: LoadedDataset) -> DatasetProfile:
    """Build a deterministic profile from an already validated dataset."""

    columns = tuple(_profile_column(name, loaded.frame[name]) for name in loaded.frame.columns)
    warnings = tuple(warning for column in columns for warning in _warnings_for(column))
    metadata = {
        "columns": {
            column.name: {"sdtype": _to_sdv_type(column.semantic_type)} for column in columns
        }
    }
    return DatasetProfile(
        dataset_fingerprint=loaded.dataset_fingerprint,
        row_count=len(loaded.frame),
        column_count=len(loaded.frame.columns),
        columns=columns,
        warnings=warnings,
        inferred_metadata=metadata,
    )


def _profile_column(name: str, series: pd.Series[Any]) -> ColumnProfile:
    non_null = series.dropna()
    physical_type = _physical_type(series)
    unique_rate = float(non_null.nunique(dropna=True) / len(non_null)) if len(non_null) else 0.0
    semantic_type = _semantic_type(name, series, physical_type, unique_rate)
    sensitive = _is_sensitive_name(name)

    return ColumnProfile(
        name=name,
        physical_type=physical_type,
        semantic_type=semantic_type,
        is_sensitive_candidate=sensitive,
        sensitivity_reason="column name suggests personal data" if sensitive else None,
        null_rate=float(series.isna().mean()),
        unique_rate=unique_rate,
        cardinality=int(non_null.nunique(dropna=True)),
        safe_summary=_safe_summary(series, semantic_type),
    )


def _physical_type(series: pd.Series[Any]) -> PhysicalType:
    if pd.api.types.is_bool_dtype(series.dtype):
        return PhysicalType.BOOLEAN
    if pd.api.types.is_integer_dtype(series.dtype):
        return PhysicalType.INTEGER
    if pd.api.types.is_float_dtype(series.dtype):
        return PhysicalType.FLOAT
    if pd.api.types.is_datetime64_any_dtype(series.dtype):
        return PhysicalType.DATETIME
    if pd.api.types.is_object_dtype(series.dtype) or pd.api.types.is_string_dtype(series.dtype):
        return PhysicalType.STRING
    return PhysicalType.UNKNOWN


def _semantic_type(
    name: str,
    series: pd.Series[Any],
    physical_type: PhysicalType,
    unique_rate: float,
) -> SemanticType:
    normalized_name = name.casefold()
    if (normalized_name == "id" or normalized_name.endswith("_id")) and unique_rate >= 0.9:
        return SemanticType.IDENTIFIER
    if physical_type is PhysicalType.DATETIME or _looks_like_datetime(series, physical_type):
        return SemanticType.DATETIME
    if physical_type is PhysicalType.BOOLEAN:
        return SemanticType.BOOLEAN
    if physical_type in {PhysicalType.INTEGER, PhysicalType.FLOAT}:
        return SemanticType.NUMERICAL
    if physical_type is PhysicalType.STRING:
        return SemanticType.CATEGORICAL
    return SemanticType.UNKNOWN


def _looks_like_datetime(series: pd.Series[Any], physical_type: PhysicalType) -> bool:
    if physical_type is not PhysicalType.STRING:
        return False
    non_null = series.dropna()
    if len(non_null) == 0:
        return False
    parsed = pd.to_datetime(non_null, errors="coerce", format="mixed")
    return bool(parsed.notna().mean() >= 0.9)


def _is_sensitive_name(name: str) -> bool:
    parts = {part for part in re.split(r"[^a-z0-9]+", name.casefold()) if part}
    return bool(parts & _SENSITIVE_NAME_PARTS)


def _safe_summary(series: pd.Series[Any], semantic_type: SemanticType) -> dict[str, Any]:
    non_null = series.dropna()
    if semantic_type is SemanticType.NUMERICAL and len(non_null):
        numeric = pd.to_numeric(non_null)
        return {
            "minimum": float(numeric.min()),
            "maximum": float(numeric.max()),
            "mean": float(numeric.mean()),
        }
    if semantic_type is SemanticType.BOOLEAN:
        return {
            "true_count": int(non_null.eq(True).sum()),
            "false_count": int(non_null.eq(False).sum()),
        }
    if semantic_type is SemanticType.CATEGORICAL:
        counts = non_null.value_counts(dropna=True)
        return {
            "category_count": len(counts),
            "most_frequent_count": int(counts.max()) if len(counts) else 0,
        }
    if semantic_type is SemanticType.DATETIME:
        parsed = pd.to_datetime(non_null, errors="coerce", format="mixed")
        summary: dict[str, Any] = {"valid_datetime_count": int(parsed.notna().sum())}
        if len(non_null) and non_null.astype(str).str.fullmatch(r"\d{4}-\d{2}-\d{2}").all():
            summary["datetime_format"] = "%Y-%m-%d"
        return summary
    lengths = non_null.astype(str).str.len()
    return {
        "non_null_count": len(non_null),
        "average_length": float(lengths.mean()) if len(lengths) else 0.0,
    }


def _warnings_for(column: ColumnProfile) -> tuple[DatasetWarning, ...]:
    warnings: list[DatasetWarning] = []
    if column.semantic_type is SemanticType.IDENTIFIER:
        warnings.append(
            DatasetWarning(
                code="IDENTIFIER_CANDIDATE",
                message="Review the inferred identifier type before generation.",
                column_name=column.name,
            )
        )
    if column.is_sensitive_candidate:
        warnings.append(
            DatasetWarning(
                code="SENSITIVE_COLUMN_CANDIDATE",
                message="Review this possible personal-data column before generation.",
                column_name=column.name,
            )
        )
    return tuple(warnings)


def _to_sdv_type(semantic_type: SemanticType) -> str:
    return {
        SemanticType.NUMERICAL: "numerical",
        SemanticType.CATEGORICAL: "categorical",
        SemanticType.DATETIME: "datetime",
        SemanticType.BOOLEAN: "boolean",
        SemanticType.IDENTIFIER: "id",
        SemanticType.UNKNOWN: "categorical",
    }[semantic_type]
