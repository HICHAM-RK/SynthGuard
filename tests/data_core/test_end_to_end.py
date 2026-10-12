from __future__ import annotations

import hashlib
import json
import socket
from pathlib import Path

import pandas as pd
import pytest

from synthguard.data_core import (
    GenerationMethod,
    GenerationRequest,
    ProfileRequest,
    SemanticType,
    generate_candidate,
    profile_csv,
)
from synthguard.data_core.synthesis import SynthesisOptions

FIXTURE = Path(__file__).parent / "fixtures" / "mixed_types.csv"


def test_profile_override_generate_flow_is_local_and_preserves_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_checksum = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()

    def deny_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("data-core attempted network access")

    monkeypatch.setattr(socket, "create_connection", deny_network)
    profile = profile_csv(ProfileRequest(source_path=FIXTURE))
    result = generate_candidate(
        GenerationRequest(
            source_path=FIXTURE,
            output_directory=tmp_path,
            method=GenerationMethod.GAUSSIAN_COPULA,
            row_count=20,
            random_seed=2026,
            column_overrides={"email": SemanticType.IDENTIFIER},
        )
    )

    assert profile.dataset_fingerprint == source_checksum
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == source_checksum
    assert len(pd.read_csv(result.artifacts.synthetic_csv)) == 20
    artifact_paths = (
        result.artifacts.synthetic_csv,
        result.artifacts.metadata_json,
        result.artifacts.manifest_json,
    )
    assert all(path.is_relative_to(tmp_path.resolve()) for path in artifact_paths)

    metadata = json.loads(result.artifacts.metadata_json.read_text(encoding="utf-8"))
    assert metadata["tables"]["table"]["columns"]["email"] == {"sdtype": "id"}


def test_ctgan_public_flow_produces_complete_artifacts(tmp_path: Path) -> None:
    result = generate_candidate(
        GenerationRequest(
            source_path=FIXTURE,
            output_directory=tmp_path,
            method=GenerationMethod.CTGAN,
            row_count=6,
            random_seed=2026,
        ),
        options=SynthesisOptions(
            ctgan_epochs=1,
            ctgan_batch_size=10,
            ctgan_pac=1,
            ctgan_enable_gpu=False,
        ),
    )

    assert result.method is GenerationMethod.CTGAN
    assert len(pd.read_csv(result.artifacts.synthetic_csv)) == 6
    assert result.artifacts.metadata_json.is_file()
    assert result.artifacts.manifest_json.is_file()
