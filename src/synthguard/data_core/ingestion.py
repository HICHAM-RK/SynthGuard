"""Bounded, local-only CSV ingestion for data-core."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from io import StringIO

import pandas as pd

from .contracts import DataCoreError, ProfileRequest


@dataclass(frozen=True, slots=True)
class LoadedDataset:
    """Validated frame plus a content-derived identity."""

    frame: pd.DataFrame
    dataset_fingerprint: str


def read_validated_csv(request: ProfileRequest) -> LoadedDataset:
    """Read a bounded UTF-8 CSV without exposing source values in failures."""

    source = request.source_path
    if not source.is_file():
        raise DataCoreError("FILE_NOT_FOUND", "The source CSV file was not found.")

    try:
        file_size = source.stat().st_size
    except OSError as error:
        raise DataCoreError("FILE_NOT_FOUND", "The source CSV file could not be read.") from error

    if file_size == 0:
        raise DataCoreError("EMPTY_DATASET", "The source CSV is empty.")
    if file_size > request.max_bytes:
        raise DataCoreError(
            "FILE_TOO_LARGE",
            "The source CSV exceeds the configured byte limit.",
            {"max_bytes": request.max_bytes, "actual_bytes": file_size},
        )

    try:
        raw = source.read_bytes()
    except OSError as error:
        raise DataCoreError("FILE_NOT_FOUND", "The source CSV file could not be read.") from error

    if len(raw) > request.max_bytes:
        raise DataCoreError(
            "FILE_TOO_LARGE",
            "The source CSV exceeds the configured byte limit.",
            {"max_bytes": request.max_bytes, "actual_bytes": len(raw)},
        )

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise DataCoreError(
            "UNSUPPORTED_ENCODING", "The source CSV must use UTF-8 encoding."
        ) from error

    row_count = _validate_csv_structure(text, max_rows=request.max_rows)
    if row_count == 0:
        raise DataCoreError("EMPTY_DATASET", "The source CSV contains no data rows.")

    try:
        frame = pd.read_csv(StringIO(text))
    except (pd.errors.ParserError, ValueError) as error:
        raise DataCoreError("INVALID_CSV", "The source CSV structure is invalid.") from error

    return LoadedDataset(
        frame=frame,
        dataset_fingerprint=hashlib.sha256(raw).hexdigest(),
    )


def _validate_csv_structure(text: str, max_rows: int) -> int:
    try:
        reader = csv.reader(StringIO(text), strict=True)
        header = next(reader)
        if not header or any(not name.strip() for name in header):
            raise DataCoreError("INVALID_CSV", "The source CSV header is invalid.")
        if len(set(header)) != len(header):
            raise DataCoreError("INVALID_CSV", "The source CSV contains duplicate columns.")

        row_count = 0
        for row_number, row in enumerate(reader, start=2):
            if not row:
                continue
            if len(row) != len(header):
                raise DataCoreError(
                    "INVALID_CSV",
                    "The source CSV has inconsistent row widths.",
                    {"row_number": row_number},
                )
            row_count += 1
            if row_count > max_rows:
                raise DataCoreError(
                    "ROW_LIMIT_EXCEEDED",
                    "The source CSV exceeds the configured row limit.",
                    {"max_rows": max_rows},
                )
    except csv.Error as error:
        raise DataCoreError("INVALID_CSV", "The source CSV structure is invalid.") from error
    except StopIteration:
        return 0

    return row_count
