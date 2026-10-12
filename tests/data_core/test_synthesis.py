from __future__ import annotations

from pathlib import Path

import pytest

from synthguard.data_core import DataCoreError, GenerationMethod, GenerationRequest
from synthguard.data_core.synthesis import SynthesisOptions, synthesize_candidate_data

FIXTURE = Path(__file__).parent / "fixtures" / "mixed_types.csv"


def test_gaussian_candidate_has_requested_shape_and_public_data_only(tmp_path: Path) -> None:
    request = GenerationRequest(
        source_path=FIXTURE,
        output_directory=tmp_path,
        method=GenerationMethod.GAUSSIAN_COPULA,
        row_count=50,
        random_seed=42,
    )

    candidate = synthesize_candidate_data(request)

    assert candidate.method is GenerationMethod.GAUSSIAN_COPULA
    assert candidate.random_seed == 42
    assert candidate.frame.shape == (50, 7)
    assert candidate.frame.columns.tolist() == [
        "customer_id",
        "age",
        "income",
        "is_member",
        "joined_at",
        "segment",
        "email",
    ]
    assert candidate.training_duration_seconds >= 0
    assert not hasattr(candidate, "synthesizer")


def test_gaussian_candidate_records_reproducibility_limitation(tmp_path: Path) -> None:
    request = GenerationRequest(
        source_path=FIXTURE,
        output_directory=tmp_path,
        method=GenerationMethod.GAUSSIAN_COPULA,
        row_count=5,
        random_seed=7,
    )

    candidate = synthesize_candidate_data(request)

    assert {warning.code for warning in candidate.warnings} == {"SDV_REPRODUCIBILITY_LIMITATION"}


def test_gaussian_training_failure_uses_stable_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_training(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("private-person@example.test")

    monkeypatch.setattr(
        "synthguard.data_core.synthesis.GaussianCopulaSynthesizer.fit", fail_training
    )
    request = GenerationRequest(
        source_path=FIXTURE,
        output_directory=tmp_path,
        method=GenerationMethod.GAUSSIAN_COPULA,
        row_count=5,
        random_seed=7,
    )

    with pytest.raises(DataCoreError) as caught:
        synthesize_candidate_data(request)

    assert caught.value.code == "TRAINING_FAILED"
    assert "private-person@example.test" not in str(caught.value)
    assert caught.value.details == {"method": "gaussian_copula"}


def test_ctgan_candidate_has_requested_shape_on_cpu(tmp_path: Path) -> None:
    request = GenerationRequest(
        source_path=FIXTURE,
        output_directory=tmp_path,
        method=GenerationMethod.CTGAN,
        row_count=8,
        random_seed=42,
    )
    options = SynthesisOptions(
        ctgan_epochs=1,
        ctgan_batch_size=10,
        ctgan_pac=1,
        ctgan_enable_gpu=False,
    )

    candidate = synthesize_candidate_data(request, options=options)

    assert candidate.method is GenerationMethod.CTGAN
    assert candidate.frame.shape == (8, 7)
    assert candidate.frame.columns.tolist() == [
        "customer_id",
        "age",
        "income",
        "is_member",
        "joined_at",
        "segment",
        "email",
    ]
    assert candidate.training_duration_seconds >= 0


def test_ctgan_production_options_are_not_changed_by_test_configuration() -> None:
    assert SynthesisOptions().ctgan_epochs == 300
    assert SynthesisOptions().ctgan_enable_gpu is False
