from __future__ import annotations

import hashlib
import socket
import urllib.request
from pathlib import Path

import pytest

from synthguard.data_core import GenerationMethod, GenerationRequest, generate_candidate
from synthguard.data_core.artifacts import persist_candidate
from synthguard.data_core.synthesis import SynthesisOptions, synthesize_candidate_data
from synthguard.evaluation_core import EvaluationRequest, evaluate_candidate

SOURCE = Path(__file__).parents[1] / "data_core" / "fixtures" / "mixed_types.csv"


@pytest.mark.parametrize("method", [GenerationMethod.GAUSSIAN_COPULA, GenerationMethod.CTGAN])
def test_generated_artifacts_are_evaluated_offline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    method: GenerationMethod,
) -> None:
    source_checksum = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    _deny_network(monkeypatch)
    generation_request = GenerationRequest(
        source_path=SOURCE,
        output_directory=tmp_path,
        method=method,
        row_count=20,
        random_seed=42,
    )
    if method is GenerationMethod.CTGAN:
        candidate = synthesize_candidate_data(
            generation_request,
            options=SynthesisOptions(
                ctgan_epochs=1,
                ctgan_batch_size=10,
                ctgan_pac=1,
                ctgan_enable_gpu=False,
            ),
        )
        generated = persist_candidate(candidate, tmp_path)
    else:
        generated = generate_candidate(generation_request)

    result = evaluate_candidate(
        EvaluationRequest(
            real_csv=SOURCE,
            synthetic_csv=generated.artifacts.synthetic_csv,
            metadata_json=generated.artifacts.metadata_json,
            random_seed=42,
            max_privacy_rows=100,
        )
    )

    assert result.real_row_count == 4
    assert result.synthetic_row_count == 20
    assert result.column_count == 7
    assert 0.0 <= result.statistical.overall_score <= 1.0
    assert 0.0 <= result.privacy.dcr_baseline_protection_score <= 1.0
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_checksum


def _deny_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Network access is forbidden during evaluation tests.")

    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(urllib.request, "urlopen", fail)
