"""Atomic persistence for immutable synthetic-data runs."""

from __future__ import annotations

import hashlib
import json
import shutil
from importlib.metadata import version
from pathlib import Path
from uuid import UUID, uuid4

from .contracts import ArtifactPaths, DataCoreError, GenerationResult
from .synthesis import GeneratedCandidate


def persist_candidate(
    candidate: GeneratedCandidate,
    output_root: Path,
    *,
    run_id: UUID | None = None,
) -> GenerationResult:
    """Persist one candidate as an all-or-nothing immutable run."""

    resolved_root = output_root.expanduser().resolve()
    selected_run_id = run_id or uuid4()
    final_directory = (resolved_root / str(selected_run_id)).resolve()
    temporary_directory = (resolved_root / f".tmp-{selected_run_id}").resolve()
    _assert_contained(resolved_root, final_directory)
    _assert_contained(resolved_root, temporary_directory)

    try:
        resolved_root.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise _artifact_error("The output directory could not be prepared.") from error

    if final_directory.exists() or temporary_directory.exists():
        raise _artifact_error("The generated run identifier already exists.")

    created_temporary = False
    try:
        temporary_directory.mkdir()
        created_temporary = True
        synthetic_path = temporary_directory / "synthetic.csv"
        metadata_path = temporary_directory / "metadata.json"
        manifest_path = temporary_directory / "manifest.json"

        candidate.frame.to_csv(synthetic_path, index=False)
        metadata_path.write_text(
            json.dumps(candidate.reviewed_metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        manifest = _build_manifest(candidate, selected_run_id, synthetic_path, metadata_path)
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary_directory.rename(final_directory)
    except Exception as error:
        if created_temporary:
            shutil.rmtree(temporary_directory, ignore_errors=True)
        raise _artifact_error("The generated run could not be persisted.") from error

    return GenerationResult(
        run_id=selected_run_id,
        method=candidate.method,
        row_count=len(candidate.frame),
        random_seed=candidate.random_seed,
        dataset_fingerprint=candidate.dataset_fingerprint,
        artifacts=ArtifactPaths(
            synthetic_csv=final_directory / "synthetic.csv",
            metadata_json=final_directory / "metadata.json",
            manifest_json=final_directory / "manifest.json",
        ),
        training_duration_seconds=candidate.training_duration_seconds,
        warnings=candidate.warnings,
    )


def _build_manifest(
    candidate: GeneratedCandidate,
    run_id: UUID,
    synthetic_path: Path,
    metadata_path: Path,
) -> dict[str, object]:
    return {
        "run_id": str(run_id),
        "method": candidate.method.value,
        "row_count": len(candidate.frame),
        "random_seed": candidate.random_seed,
        "dataset_fingerprint": candidate.dataset_fingerprint,
        "training_duration_seconds": candidate.training_duration_seconds,
        "warnings": [warning.model_dump(mode="json") for warning in candidate.warnings],
        "dependencies": {
            "pandas": version("pandas"),
            "pydantic": version("pydantic"),
            "sdv": version("sdv"),
        },
        "checksums": {
            "synthetic.csv": _sha256(synthetic_path),
            "metadata.json": _sha256(metadata_path),
        },
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_contained(root: Path, candidate: Path) -> None:
    if not candidate.is_relative_to(root):
        raise _artifact_error("The artifact path is outside the configured output directory.")


def _artifact_error(message: str) -> DataCoreError:
    return DataCoreError("ARTIFACT_WRITE_FAILED", message)
