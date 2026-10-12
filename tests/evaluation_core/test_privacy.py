from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pytest

from synthguard.evaluation_core import EvaluationCoreError, EvaluationRequest
from synthguard.evaluation_core.privacy import evaluate_privacy_evidence
from synthguard.evaluation_core.validation import ValidatedEvaluationPair


def test_exact_matches_include_null_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("synthguard.evaluation_core.privacy._dcr_score", _fixed_dcr)
    real = pd.DataFrame(
        {
            "customer_id": ["R-1", "R-2", "R-3"],
            "age": [20.0, np.nan, 40.0],
            "segment": ["basic", "premium", "basic"],
        }
    )
    synthetic = pd.DataFrame(
        {
            "customer_id": ["R-2", "S-2", "R-1"],
            "age": [np.nan, 35.0, 20.0],
            "segment": ["premium", "premium", "basic"],
        }
    )

    result = evaluate_privacy_evidence(_pair(real, synthetic), _request())

    assert result.exact_match_count == 2
    assert result.exact_match_rate == pytest.approx(2 / 3)
    assert result.excluded_identifier_columns == ("customer_id",)


def test_distance_ignores_identifiers_and_detects_near_duplicates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("synthguard.evaluation_core.privacy._dcr_score", _fixed_dcr)
    real = pd.DataFrame(
        {
            "customer_id": ["R-1", "R-2", "R-3"],
            "age": [20, 30, 40],
            "segment": ["basic", "premium", "basic"],
        }
    )
    synthetic = pd.DataFrame(
        {
            "customer_id": ["S-1", "S-2", "S-3"],
            "age": [20, 30, 40],
            "segment": ["basic", "premium", "basic"],
        }
    )

    result = evaluate_privacy_evidence(_pair(real, synthetic), _request())

    assert result.exact_match_count == 0
    assert result.near_duplicate_count == 3
    assert result.nearest_distance_min == pytest.approx(0.0)
    assert result.nearest_distance_median == pytest.approx(0.0)
    assert result.distance_threshold == 0.05
    assert result.dcr_baseline_protection_score == 0.75


def test_privacy_sampling_is_bounded_and_reproducible(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("synthguard.evaluation_core.privacy._dcr_score", _fixed_dcr)
    real = pd.DataFrame(
        {
            "customer_id": [f"R-{index}" for index in range(160)],
            "age": list(range(160)),
            "segment": ["basic", "premium"] * 80,
        }
    )
    synthetic = pd.DataFrame(
        {
            "customer_id": [f"S-{index}" for index in range(160)],
            "age": list(reversed(range(160))),
            "segment": ["premium", "basic"] * 80,
        }
    )
    request = _request(max_privacy_rows=100, random_seed=17)

    first = evaluate_privacy_evidence(_pair(real, synthetic), request)
    second = evaluate_privacy_evidence(_pair(real, synthetic), request)

    assert first == second
    assert first.sampled_real_rows == 100
    assert first.sampled_synthetic_rows == 100
    assert first.sampling_seed == 17


def test_sdmetrics_dcr_is_bounded_and_seeded() -> None:
    real = pd.DataFrame(
        {
            "customer_id": [f"R-{index}" for index in range(120)],
            "age": list(range(120)),
            "segment": ["basic", "premium"] * 60,
        }
    )
    synthetic = pd.DataFrame(
        {
            "customer_id": [f"S-{index}" for index in range(120)],
            "age": [index + 0.25 for index in range(120)],
            "segment": ["basic", "premium"] * 60,
        }
    )
    request = _request(max_privacy_rows=100, random_seed=29)

    first = evaluate_privacy_evidence(_pair(real, synthetic), request)
    second = evaluate_privacy_evidence(_pair(real, synthetic), request)

    assert first == second
    assert 0.0 <= first.dcr_baseline_protection_score <= 1.0
    assert first.metric_provenance.startswith("SynthGuard normalized mixed-type distance")


def test_privacy_failure_is_mapped_without_source_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "private-source-value"

    def fail(*_args: object, **_kwargs: object) -> float:
        raise RuntimeError(secret)

    monkeypatch.setattr("synthguard.evaluation_core.privacy._dcr_score", fail)
    real = pd.DataFrame({"age": [20, 30], "segment": ["a", "b"]})

    with pytest.raises(EvaluationCoreError) as caught:
        evaluate_privacy_evidence(_pair(real, real.copy()), _request())

    assert caught.value.code == "PRIVACY_EVALUATION_FAILED"
    assert secret not in str(caught.value)
    assert secret not in repr(caught.value.to_dict())


def _fixed_dcr(
    _real: pd.DataFrame,
    _synthetic: pd.DataFrame,
    _metadata: dict[str, Any],
    _table_name: str,
    _seed: int,
) -> float:
    return 0.75


def _request(**overrides: int) -> EvaluationRequest:
    values: dict[str, object] = {
        "real_csv": "real.csv",
        "synthetic_csv": "synthetic.csv",
        "metadata_json": "metadata.json",
    }
    values.update(overrides)
    return EvaluationRequest(**values)  # type: ignore[arg-type]


def _pair(real: pd.DataFrame, synthetic: pd.DataFrame) -> ValidatedEvaluationPair:
    definitions = {
        "customer_id": {"sdtype": "id"},
        "age": {"sdtype": "numerical"},
        "segment": {"sdtype": "categorical"},
    }
    columns = {column: definitions[column] for column in real.columns}
    metadata: dict[str, Any] = {
        "tables": {"table": {"columns": columns}},
        "relationships": [],
        "METADATA_SPEC_VERSION": "V1",
    }
    return ValidatedEvaluationPair(
        real=real,
        synthetic=synthetic,
        metadata=metadata,
        table_name="table",
        identifier_columns=tuple(
            column for column in real.columns if definitions[column]["sdtype"] == "id"
        ),
        classification_target=None,
        real_fingerprint="a" * 64,
        synthetic_fingerprint="b" * 64,
        metadata_fingerprint="c" * 64,
    )
