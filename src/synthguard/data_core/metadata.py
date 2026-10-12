"""Reviewable SDV metadata construction and override validation."""

from __future__ import annotations

from typing import Any

from sdv.metadata import Metadata

from .contracts import ColumnProfile, DataCoreError, DatasetProfile, PhysicalType, SemanticType

_ALLOWED_OVERRIDES: dict[PhysicalType, frozenset[SemanticType]] = {
    PhysicalType.INTEGER: frozenset(
        {SemanticType.NUMERICAL, SemanticType.CATEGORICAL, SemanticType.IDENTIFIER}
    ),
    PhysicalType.FLOAT: frozenset({SemanticType.NUMERICAL, SemanticType.CATEGORICAL}),
    PhysicalType.BOOLEAN: frozenset({SemanticType.BOOLEAN, SemanticType.CATEGORICAL}),
    PhysicalType.STRING: frozenset(
        {SemanticType.CATEGORICAL, SemanticType.DATETIME, SemanticType.IDENTIFIER}
    ),
    PhysicalType.DATETIME: frozenset({SemanticType.DATETIME, SemanticType.CATEGORICAL}),
    PhysicalType.UNKNOWN: frozenset({SemanticType.CATEGORICAL}),
}


def build_sdv_metadata(
    profile: DatasetProfile,
    overrides: dict[str, SemanticType] | None = None,
) -> dict[str, Any]:
    """Return validated SDV metadata without mutating the source profile."""

    requested = dict(overrides or {})
    columns_by_name = {column.name: column for column in profile.columns}
    for column_name, semantic_type in requested.items():
        column = columns_by_name.get(column_name)
        if column is None:
            raise DataCoreError(
                "INVALID_OVERRIDE",
                "An override references an unknown column.",
                {"column_name": column_name},
            )
        if semantic_type not in _ALLOWED_OVERRIDES[column.physical_type]:
            raise _incompatible_override(column_name, semantic_type)
        if semantic_type is SemanticType.IDENTIFIER and column.unique_rate < 0.9:
            raise _incompatible_override(column_name, semantic_type)

    columns = {
        column.name: _column_metadata(column, requested.get(column.name, column.semantic_type))
        for column in profile.columns
    }
    metadata: dict[str, Any] = {
        "tables": {
            "table": {
                "columns": columns,
            }
        },
        "relationships": [],
        "METADATA_SPEC_VERSION": "V1",
    }
    Metadata.load_from_dict(metadata).validate()
    return metadata


def _incompatible_override(column_name: str, semantic_type: SemanticType) -> DataCoreError:
    return DataCoreError(
        "INVALID_OVERRIDE",
        "The requested semantic type is incompatible with the column.",
        {"column_name": column_name, "semantic_type": semantic_type.value},
    )


def _to_sdv_type(semantic_type: SemanticType) -> str:
    return {
        SemanticType.NUMERICAL: "numerical",
        SemanticType.CATEGORICAL: "categorical",
        SemanticType.DATETIME: "datetime",
        SemanticType.BOOLEAN: "boolean",
        SemanticType.IDENTIFIER: "id",
        SemanticType.UNKNOWN: "categorical",
    }[semantic_type]


def _column_metadata(column: ColumnProfile, semantic_type: SemanticType) -> dict[str, str]:
    metadata = {"sdtype": _to_sdv_type(semantic_type)}
    datetime_format = column.safe_summary.get("datetime_format")
    if semantic_type is SemanticType.DATETIME and isinstance(datetime_format, str):
        metadata["datetime_format"] = datetime_format
    return metadata
