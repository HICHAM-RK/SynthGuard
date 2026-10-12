from __future__ import annotations

import hashlib
import json
from pathlib import Path
from uuid import UUID

import pandas as pd
import pytest

import synthguard.data_core as data_core
from synthguard.data_core import (
    DataCoreError,
    GenerationMethod,
    GenerationRequest,
    generate_candidate,
)
from synthguard.data_core.artifacts import _assert_contained, persist_candidate
from synthguard.data_core.synthesis import synthesize_candidate_data

FIXTURE = Path(__file__).parent / "fixtures" / "mixed_types.csv"
RUN_ID = UUID("12345678-1234-5678-1234-567812345678")


def _request(output_directory: Path, row_count: int = 12) -> GenerationRequest:
    return GenerationRequest(
        source_path=FIXTURE,
        output_directory=output_directory,
        method=GenerationMethod.GAUSSIAN_COPULA,
        row_count=row_count,
        random_seed=42,
    )


def test_persisted_run_contains_required_artifacts_and_checksums(tmp_path: Path) -> None:
    request = _request(tmp_path)
    candidate = synthesize_candidate_data(request)

    result = persist_candidate(candidate, tmp_path, run_id=RUN_ID)

    assert result.run_id == RUN_ID
    assert result.artifacts.synthetic_csv.is_file()
    assert result.artifacts.metadata_json.is_file()
    assert result.artifacts.manifest_json.is_file()
    assert result.artifacts.synthetic_csv.parent == tmp_path / str(RUN_ID)
    assert len(pd.read_csv(result.artifacts.synthetic_csv)) == request.row_count

    manifest = json.loads(result.artifacts.manifest_json.read_text(encoding="utf-8"))
    assert manifest["run_id"] == str(RUN_ID)
    assert manifest["method"] == "gaussian_copula"
    assert manifest["row_count"] == request.row_count
    assert manifest["random_seed"] == 42
    assert manifest["dependencies"]["sdv"]
    for artifact_name in ("synthetic.csv", "metadata.json"):
        artifact = result.artifacts.manifest_json.parent / artifact_name
        assert (
            manifest["checksums"][artifact_name]
            == hashlib.sha256(artifact.read_bytes()).hexdigest()
        )


def test_existing_completed_run_is_never_overwritten(tmp_path: Path) -> None:
    candidate = synthesize_candidate_data(_request(tmp_path))
    first = persist_candidate(candidate, tmp_path, run_id=RUN_ID)
    original_manifest = first.artifacts.manifest_json.read_bytes()

    with pytest.raises(DataCoreError) as caught:
        persist_candidate(candidate, tmp_path, run_id=RUN_ID)

    assert caught.value.code == "ARTIFACT_WRITE_FAILED"
    assert first.artifacts.manifest_json.read_bytes() == original_manifest
    assert not (tmp_path / f".tmp-{RUN_ID}").exists()


def test_write_failure_leaves_no_partial_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = synthesize_candidate_data(_request(tmp_path))

    def fail_write(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk failure")

    monkeypatch.setattr(pd.DataFrame, "to_csv", fail_write)

    with pytest.raises(DataCoreError) as caught:
        persist_candidate(candidate, tmp_path, run_id=RUN_ID)

    assert caught.value.code == "ARTIFACT_WRITE_FAILED"
    assert not (tmp_path / str(RUN_ID)).exists()
    assert not (tmp_path / f".tmp-{RUN_ID}").exists()


def test_public_generate_candidate_returns_complete_result(tmp_path: Path) -> None:
    result = generate_candidate(_request(tmp_path, row_count=10))

    assert result.row_count == 10
    assert result.method is GenerationMethod.GAUSSIAN_COPULA
    assert result.artifacts.synthetic_csv.is_file()
    assert result.artifacts.metadata_json.is_file()
    assert result.artifacts.manifest_json.is_file()
    assert not hasattr(result, "synthesizer")


def test_package_exports_public_generation_function() -> None:
    assert "generate_candidate" in data_core.__all__


def test_artifact_containment_guard_rejects_outside_path(tmp_path: Path) -> None:
    root = tmp_path / "allowed"
    outside = tmp_path / "outside" / "run"

    with pytest.raises(DataCoreError) as caught:
        _assert_contained(root.resolve(), outside.resolve())

    assert caught.value.code == "ARTIFACT_WRITE_FAILED"
