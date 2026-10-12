from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pytest

from synthguard.evaluation_core import EvaluationCoreError, EvaluationRequest
from synthguard.evaluation_core.utility import evaluate_classification_utility
from synthguard.evaluation_core.validation import ValidatedEvaluationPair


def test_classification_utility_is_deterministic_and_uses_same_real_holdout() -> None:
    real = _classification_frame("R")
    synthetic = real.sample(frac=1, random_state=9).reset_index(drop=True).copy()
    synthetic["customer_id"] = [f"S-{index}" for index in range(len(synthetic))]
    pair = _pair(real, synthetic)
    request = _request(random_seed=23)

    first = evaluate_classification_utility(pair, request)
    second = evaluate_classification_utility(pair, request)

    assert first == second
    assert first.target_name == "churned"
    assert first.class_count == 2
    assert first.real_train_rows == 160
    assert first.real_test_rows == 40
    assert first.synthetic_train_rows == 200
    assert first.real_train_score >= 0.9
    assert first.synthetic_train_score >= 0.9
    assert first.utility_retention == pytest.approx(
        first.synthetic_train_score / first.real_train_score
    )
    assert first.model_parameters == {
        "class_weight": "none",
        "max_iter": 1000,
        "random_seed": 23,
        "solver": "lbfgs",
        "test_size": 0.2,
    }


def test_real_and_synthetic_models_receive_one_identical_holdout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pipelines: list[_RecordingPipeline] = []

    def build_pipeline(_definitions: dict[str, Any], _seed: int) -> _RecordingPipeline:
        pipeline = _RecordingPipeline()
        pipelines.append(pipeline)
        return pipeline

    monkeypatch.setattr("synthguard.evaluation_core.utility._build_pipeline", build_pipeline)
    real = _classification_frame("R", row_count=100)
    synthetic = _classification_frame("S", row_count=120)

    result = evaluate_classification_utility(_pair(real, synthetic), _request())

    assert result.real_train_rows == 80
    assert result.real_test_rows == 20
    assert result.synthetic_train_rows == 120
    assert len(pipelines) == 2
    assert set(pipelines[0].fit_indices).isdisjoint(pipelines[0].predict_indices)
    assert pipelines[0].predict_indices == pipelines[1].predict_indices
    assert "customer_id" not in pipelines[0].fit_columns
    assert "churned" not in pipelines[0].fit_columns


def test_zero_real_baseline_has_undefined_retention(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scores = iter([0.0, 0.4])
    monkeypatch.setattr(
        "synthguard.evaluation_core.utility._weighted_f1",
        lambda *_args: next(scores),
    )
    real = _classification_frame("R", row_count=100)

    result = evaluate_classification_utility(_pair(real, real.copy()), _request())

    assert result.real_train_score == 0.0
    assert result.synthetic_train_score == 0.4
    assert result.utility_retention is None


def test_utility_failure_is_mapped_without_source_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "private-target-value"

    def fail(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError(secret)

    monkeypatch.setattr("synthguard.evaluation_core.utility._build_pipeline", fail)
    real = _classification_frame("R", row_count=100)

    with pytest.raises(EvaluationCoreError) as caught:
        evaluate_classification_utility(_pair(real, real.copy()), _request())

    assert caught.value.code == "UTILITY_EVALUATION_FAILED"
    assert secret not in str(caught.value)
    assert secret not in repr(caught.value.to_dict())


class _RecordingPipeline:
    def __init__(self) -> None:
        self.fit_indices: list[int] = []
        self.predict_indices: list[int] = []
        self.fit_columns: list[str] = []
        self._prediction: object = "no"

    def fit(self, features: pd.DataFrame, target: pd.Series) -> _RecordingPipeline:
        self.fit_indices = list(features.index)
        self.fit_columns = list(features.columns)
        self._prediction = target.iloc[0]
        return self

    def predict(self, features: pd.DataFrame) -> np.ndarray[Any, np.dtype[Any]]:
        self.predict_indices = list(features.index)
        return np.repeat(self._prediction, len(features))


def _classification_frame(prefix: str, row_count: int = 200) -> pd.DataFrame:
    age = np.arange(row_count) % 80 + 18
    plan = np.where(np.arange(row_count) % 3 == 0, "premium", "basic")
    churned = np.where((age > 55) | (plan == "basic"), "yes", "no")
    return pd.DataFrame(
        {
            "customer_id": [f"{prefix}-{index}" for index in range(row_count)],
            "age": age,
            "plan": plan,
            "churned": churned,
        }
    )


def _request(**overrides: int) -> EvaluationRequest:
    values: dict[str, object] = {
        "real_csv": "real.csv",
        "synthetic_csv": "synthetic.csv",
        "metadata_json": "metadata.json",
        "classification_target": "churned",
    }
    values.update(overrides)
    return EvaluationRequest(**values)  # type: ignore[arg-type]


def _pair(real: pd.DataFrame, synthetic: pd.DataFrame) -> ValidatedEvaluationPair:
    columns = {
        "customer_id": {"sdtype": "id"},
        "age": {"sdtype": "numerical"},
        "plan": {"sdtype": "categorical"},
        "churned": {"sdtype": "categorical"},
    }
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
        identifier_columns=("customer_id",),
        classification_target="churned",
        real_fingerprint="a" * 64,
        synthetic_fingerprint="b" * 64,
        metadata_fingerprint="c" * 64,
    )
