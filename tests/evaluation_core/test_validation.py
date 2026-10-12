from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from synthguard.evaluation_core import EvaluationCoreError, EvaluationRequest
from synthguard.evaluation_core.validation import load_evaluation_pair


def test_load_evaluation_pair_returns_trusted_artifacts_without_modifying_sources(
    tmp_path: Path,
) -> None:
    request = _write_artifacts(tmp_path, classification_target="segment")
    checksums_before = _checksums(request)

    pair = load_evaluation_pair(request)

    assert tuple(pair.real.columns) == ("customer_id", "age", "segment")
    assert tuple(pair.synthetic.columns) == tuple(pair.real.columns)
    assert pair.real_fingerprint == checksums_before[request.real_csv]
    assert pair.synthetic_fingerprint == checksums_before[request.synthetic_csv]
    assert pair.metadata_fingerprint == checksums_before[request.metadata_json]
    assert pair.table_name == "table"
    assert pair.identifier_columns == ("customer_id",)
    assert pair.classification_target == "segment"
    assert _checksums(request) == checksums_before


@pytest.mark.parametrize("missing_name", ["real.csv", "synthetic.csv", "metadata.json"])
def test_missing_artifact_raises_stable_error(tmp_path: Path, missing_name: str) -> None:
    request = _write_artifacts(tmp_path)
    (tmp_path / missing_name).unlink()

    with pytest.raises(EvaluationCoreError) as caught:
        load_evaluation_pair(request)

    assert caught.value.code == "FILE_NOT_FOUND"
    assert str(tmp_path) not in str(caught.value)


def test_oversized_artifact_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request = _write_artifacts(tmp_path)
    monkeypatch.setattr("synthguard.evaluation_core.validation._MAX_ARTIFACT_BYTES", 10)

    with pytest.raises(EvaluationCoreError) as caught:
        load_evaluation_pair(request)

    assert caught.value.code == "FILE_TOO_LARGE"
    assert caught.value.details["max_bytes"] == 10


@pytest.mark.parametrize("contents", ["", "customer_id,age,segment\n"])
def test_empty_real_dataset_is_rejected(tmp_path: Path, contents: str) -> None:
    request = _write_artifacts(tmp_path)
    request.real_csv.write_text(contents, encoding="utf-8")

    with pytest.raises(EvaluationCoreError) as caught:
        load_evaluation_pair(request)

    assert caught.value.code == "EMPTY_DATASET"


def test_malformed_csv_is_rejected_without_exposing_values(tmp_path: Path) -> None:
    request = _write_artifacts(tmp_path)
    secret_value = "private-cell-value"
    request.synthetic_csv.write_text(
        f"customer_id,age,segment\nS-1,22,basic,{secret_value}\n",
        encoding="utf-8",
    )

    with pytest.raises(EvaluationCoreError) as caught:
        load_evaluation_pair(request)

    assert caught.value.code == "INVALID_CSV"
    assert secret_value not in str(caught.value)
    assert secret_value not in repr(caught.value.to_dict())


def test_invalid_metadata_is_rejected(tmp_path: Path) -> None:
    request = _write_artifacts(tmp_path)
    request.metadata_json.write_text("{not-json", encoding="utf-8")

    with pytest.raises(EvaluationCoreError) as caught:
        load_evaluation_pair(request)

    assert caught.value.code == "INVALID_METADATA"


@pytest.mark.parametrize(
    ("synthetic_header", "metadata_columns"),
    [
        ("age,customer_id,segment", ("customer_id", "age", "segment")),
        ("customer_id,age,segment", ("customer_id", "segment", "age")),
    ],
)
def test_schema_order_mismatch_is_rejected(
    tmp_path: Path,
    synthetic_header: str,
    metadata_columns: tuple[str, ...],
) -> None:
    request = _write_artifacts(tmp_path, metadata_columns=metadata_columns)
    request.synthetic_csv.write_text(
        f"{synthetic_header}\nS-1,22,basic\nS-2,48,premium\n",
        encoding="utf-8",
    )

    with pytest.raises(EvaluationCoreError) as caught:
        load_evaluation_pair(request)

    assert caught.value.code == "SCHEMA_MISMATCH"
    assert caught.value.details == {
        "real_column_count": 3,
        "synthetic_column_count": 3,
        "metadata_column_count": 3,
    }


def test_unknown_classification_target_is_rejected(tmp_path: Path) -> None:
    request = _write_artifacts(tmp_path, classification_target="unknown")

    with pytest.raises(EvaluationCoreError) as caught:
        load_evaluation_pair(request)

    assert caught.value.code == "TARGET_NOT_FOUND"
    assert caught.value.details == {"target_name": "unknown"}


def test_identifier_classification_target_is_rejected(tmp_path: Path) -> None:
    request = _write_artifacts(tmp_path, classification_target="customer_id")

    with pytest.raises(EvaluationCoreError) as caught:
        load_evaluation_pair(request)

    assert caught.value.code == "UNSUPPORTED_TARGET"
    assert caught.value.details == {"target_name": "customer_id", "sdtype": "id"}


def test_target_with_one_real_class_is_rejected(tmp_path: Path) -> None:
    request = _write_artifacts(tmp_path, classification_target="segment")
    request.real_csv.write_text(
        "customer_id,age,segment\nR-1,20,basic\nR-2,30,basic\n",
        encoding="utf-8",
    )

    with pytest.raises(EvaluationCoreError) as caught:
        load_evaluation_pair(request)

    assert caught.value.code == "INSUFFICIENT_CLASSES"
    assert caught.value.details == {"target_name": "segment", "dataset": "real"}


def _write_artifacts(
    tmp_path: Path,
    *,
    classification_target: str | None = None,
    metadata_columns: tuple[str, ...] = ("customer_id", "age", "segment"),
) -> EvaluationRequest:
    real_csv = tmp_path / "real.csv"
    synthetic_csv = tmp_path / "synthetic.csv"
    metadata_json = tmp_path / "metadata.json"
    real_csv.write_text(
        "customer_id,age,segment\nR-1,20,basic\nR-2,30,premium\nR-3,40,basic\nR-4,50,premium\n",
        encoding="utf-8",
    )
    synthetic_csv.write_text(
        "customer_id,age,segment\nS-1,22,basic\nS-2,48,premium\n",
        encoding="utf-8",
    )
    definitions = {
        "customer_id": {"sdtype": "id"},
        "age": {"sdtype": "numerical"},
        "segment": {"sdtype": "categorical"},
    }
    metadata = {
        "tables": {
            "table": {
                "columns": {name: definitions[name] for name in metadata_columns},
            }
        },
        "relationships": [],
        "METADATA_SPEC_VERSION": "V1",
    }
    metadata_json.write_text(json.dumps(metadata), encoding="utf-8")
    return EvaluationRequest(
        real_csv=real_csv,
        synthetic_csv=synthetic_csv,
        metadata_json=metadata_json,
        classification_target=classification_target,
    )


def _checksums(request: EvaluationRequest) -> dict[Path, str]:
    return {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (request.real_csv, request.synthetic_csv, request.metadata_json)
    }
