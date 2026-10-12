"""Safe loading and validation for real/synthetic evaluation pairs."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
from sdv.metadata import Metadata

from .contracts import EvaluationCoreError, EvaluationRequest

_MAX_ARTIFACT_BYTES = 25_000_000
_SUPPORTED_TARGET_SDTYPES = frozenset({"boolean", "categorical"})


@dataclass(frozen=True, slots=True)
class ValidatedEvaluationPair:
    """Validated in-memory artifacts passed to metric adapters."""

    real: pd.DataFrame
    synthetic: pd.DataFrame
    metadata: dict[str, Any]
    table_name: str
    identifier_columns: tuple[str, ...]
    classification_target: str | None
    real_fingerprint: str
    synthetic_fingerprint: str
    metadata_fingerprint: str


@dataclass(frozen=True, slots=True)
class _LoadedCsv:
    frame: pd.DataFrame
    fingerprint: str


def load_evaluation_pair(request: EvaluationRequest) -> ValidatedEvaluationPair:
    """Load and validate evaluation inputs without changing their artifacts."""

    real = _load_csv(request.real_csv, artifact_name="real CSV")
    synthetic = _load_csv(request.synthetic_csv, artifact_name="synthetic CSV")
    metadata, metadata_fingerprint = _load_metadata(request.metadata_json)
    table_name, metadata_columns, identifier_columns = _metadata_schema(metadata)

    real_columns = tuple(str(column) for column in real.frame.columns)
    synthetic_columns = tuple(str(column) for column in synthetic.frame.columns)
    if real_columns != synthetic_columns or real_columns != metadata_columns:
        raise EvaluationCoreError(
            "SCHEMA_MISMATCH",
            "The real, synthetic, and metadata schemas must match in the same order.",
            {
                "real_column_count": len(real_columns),
                "synthetic_column_count": len(synthetic_columns),
                "metadata_column_count": len(metadata_columns),
            },
        )

    _validate_target(
        request.classification_target,
        real.frame,
        synthetic.frame,
        metadata["tables"][table_name]["columns"],
    )
    return ValidatedEvaluationPair(
        real=real.frame,
        synthetic=synthetic.frame,
        metadata=metadata,
        table_name=table_name,
        identifier_columns=identifier_columns,
        classification_target=request.classification_target,
        real_fingerprint=real.fingerprint,
        synthetic_fingerprint=synthetic.fingerprint,
        metadata_fingerprint=metadata_fingerprint,
    )


def _load_csv(path: Path, *, artifact_name: str) -> _LoadedCsv:
    raw = _read_bounded(path, artifact_name=artifact_name)
    if not raw:
        raise EvaluationCoreError("EMPTY_DATASET", f"The {artifact_name} is empty.")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise EvaluationCoreError("INVALID_CSV", f"The {artifact_name} must use UTF-8.") from error

    row_count = _validate_csv_structure(text, artifact_name=artifact_name)
    if row_count == 0:
        raise EvaluationCoreError("EMPTY_DATASET", f"The {artifact_name} contains no data rows.")

    try:
        frame = pd.read_csv(StringIO(text))
    except (pd.errors.ParserError, ValueError) as error:
        raise EvaluationCoreError(
            "INVALID_CSV", f"The {artifact_name} structure is invalid."
        ) from error
    return _LoadedCsv(frame=frame, fingerprint=hashlib.sha256(raw).hexdigest())


def _read_bounded(path: Path, *, artifact_name: str) -> bytes:
    if not path.is_file():
        raise EvaluationCoreError("FILE_NOT_FOUND", f"The {artifact_name} was not found.")
    try:
        file_size = path.stat().st_size
    except OSError as error:
        raise EvaluationCoreError(
            "FILE_NOT_FOUND", f"The {artifact_name} could not be read."
        ) from error
    if file_size > _MAX_ARTIFACT_BYTES:
        raise EvaluationCoreError(
            "FILE_TOO_LARGE",
            f"The {artifact_name} exceeds the byte limit.",
            {"max_bytes": _MAX_ARTIFACT_BYTES, "actual_bytes": file_size},
        )
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise EvaluationCoreError(
            "FILE_NOT_FOUND", f"The {artifact_name} could not be read."
        ) from error
    if len(raw) > _MAX_ARTIFACT_BYTES:
        raise EvaluationCoreError(
            "FILE_TOO_LARGE",
            f"The {artifact_name} exceeds the byte limit.",
            {"max_bytes": _MAX_ARTIFACT_BYTES, "actual_bytes": len(raw)},
        )
    return raw


def _validate_csv_structure(text: str, *, artifact_name: str) -> int:
    try:
        reader = csv.reader(StringIO(text), strict=True)
        header = next(reader)
        if not header or any(not name.strip() for name in header):
            raise EvaluationCoreError("INVALID_CSV", f"The {artifact_name} header is invalid.")
        if len(set(header)) != len(header):
            raise EvaluationCoreError(
                "INVALID_CSV", f"The {artifact_name} contains duplicate columns."
            )

        row_count = 0
        for row_number, row in enumerate(reader, start=2):
            if not row:
                continue
            if len(row) != len(header):
                raise EvaluationCoreError(
                    "INVALID_CSV",
                    f"The {artifact_name} has inconsistent row widths.",
                    {"row_number": row_number},
                )
            row_count += 1
    except csv.Error as error:
        raise EvaluationCoreError(
            "INVALID_CSV", f"The {artifact_name} structure is invalid."
        ) from error
    except StopIteration:
        return 0
    return row_count


def _load_metadata(path: Path) -> tuple[dict[str, Any], str]:
    raw = _read_bounded(path, artifact_name="metadata JSON")
    try:
        parsed = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(parsed, dict):
            raise TypeError("metadata root must be an object")
        metadata: dict[str, Any] = parsed
        Metadata.load_from_dict(metadata).validate()
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise EvaluationCoreError("INVALID_METADATA", "The metadata JSON is invalid.") from error
    except Exception as error:
        raise EvaluationCoreError(
            "INVALID_METADATA", "The metadata JSON could not be validated."
        ) from error
    return metadata, hashlib.sha256(raw).hexdigest()


def _metadata_schema(metadata: dict[str, Any]) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    try:
        tables = metadata["tables"]
        if not isinstance(tables, dict) or len(tables) != 1:
            raise TypeError("one table is required")
        table_name = next(iter(tables))
        columns = tables[table_name]["columns"]
        if not isinstance(columns, dict) or not columns:
            raise TypeError("columns are required")
        metadata_columns = tuple(columns)
        identifiers = tuple(
            name for name, definition in columns.items() if definition.get("sdtype") == "id"
        )
    except (KeyError, AttributeError, TypeError) as error:
        raise EvaluationCoreError(
            "INVALID_METADATA", "The metadata JSON does not define one valid table."
        ) from error
    return table_name, metadata_columns, identifiers


def _validate_target(
    target: str | None,
    real: pd.DataFrame,
    synthetic: pd.DataFrame,
    column_definitions: dict[str, Any],
) -> None:
    if target is None:
        return
    target_is_missing = (
        target not in real.columns
        or target not in synthetic.columns
        or target not in column_definitions
    )
    if target_is_missing:
        raise EvaluationCoreError(
            "TARGET_NOT_FOUND",
            "The classification target was not found in every artifact.",
            {"target_name": target},
        )
    sdtype = column_definitions[target].get("sdtype")
    if sdtype not in _SUPPORTED_TARGET_SDTYPES:
        raise EvaluationCoreError(
            "UNSUPPORTED_TARGET",
            "The selected target is not a supported classification column.",
            {"target_name": target, "sdtype": str(sdtype)},
        )
    for dataset_name, frame in (("real", real), ("synthetic", synthetic)):
        if frame[target].nunique(dropna=True) < 2:
            raise EvaluationCoreError(
                "INSUFFICIENT_CLASSES",
                "The classification target needs at least two classes.",
                {"target_name": target, "dataset": dataset_name},
            )
