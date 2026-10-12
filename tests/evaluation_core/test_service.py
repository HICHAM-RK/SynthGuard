from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from synthguard.evaluation_core import (
    ClassificationUtilityResult,
    EvaluationRequest,
    evaluate_candidate,
)


def test_evaluate_candidate_returns_complete_serializable_evidence(tmp_path: Path) -> None:
    request = _write_artifacts(tmp_path)

    result = evaluate_candidate(request)

    assert result.real_fingerprint != result.synthetic_fingerprint
    assert result.real_row_count == 120
    assert result.synthetic_row_count == 120
    assert result.column_count == 4
    assert result.utility is None
    assert result.warnings == ()
    assert result.evaluation_duration_seconds >= 0.0
    assert '"statistical"' in result.model_dump_json()
    assert '"privacy"' in result.model_dump_json()


def test_evaluate_candidate_includes_requested_utility(tmp_path: Path) -> None:
    request = _write_artifacts(tmp_path, classification_target="churned")

    result = evaluate_candidate(request)

    assert result.utility is not None
    assert result.utility.target_name == "churned"
    assert result.utility.metric_name == "weighted_f1"


def test_zero_real_utility_baseline_adds_explicit_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _write_artifacts(tmp_path, classification_target="churned")
    utility = ClassificationUtilityResult(
        target_name="churned",
        class_count=2,
        real_train_rows=96,
        real_test_rows=24,
        synthetic_train_rows=120,
        metric_name="weighted_f1",
        real_train_score=0.0,
        synthetic_train_score=0.2,
        utility_retention=None,
        model_parameters={},
    )
    monkeypatch.setattr(
        "synthguard.evaluation_core.service.evaluate_classification_utility",
        lambda *_args: utility,
    )

    result = evaluate_candidate(request)

    assert [(warning.code, warning.message) for warning in result.warnings] == [
        (
            "ZERO_REAL_UTILITY_BASELINE",
            "Utility retention is undefined because the real-trained baseline scored zero.",
        )
    ]


def _write_artifacts(
    tmp_path: Path,
    *,
    classification_target: str | None = None,
) -> EvaluationRequest:
    row_count = 120
    ages = [18 + index % 60 for index in range(row_count)]
    plans = ["premium" if index % 3 == 0 else "basic" for index in range(row_count)]
    churned = [
        "yes" if age > 50 or plan == "basic" else "no"
        for age, plan in zip(ages, plans, strict=True)
    ]
    real = pd.DataFrame(
        {
            "customer_id": [f"R-{index}" for index in range(row_count)],
            "age": ages,
            "plan": plans,
            "churned": churned,
        }
    )
    synthetic = real.sample(frac=1, random_state=13).reset_index(drop=True).copy()
    synthetic["customer_id"] = [f"S-{index}" for index in range(row_count)]

    real_csv = tmp_path / "real.csv"
    synthetic_csv = tmp_path / "synthetic.csv"
    metadata_json = tmp_path / "metadata.json"
    real.to_csv(real_csv, index=False)
    synthetic.to_csv(synthetic_csv, index=False)
    metadata = {
        "tables": {
            "table": {
                "columns": {
                    "customer_id": {"sdtype": "id"},
                    "age": {"sdtype": "numerical"},
                    "plan": {"sdtype": "categorical"},
                    "churned": {"sdtype": "categorical"},
                }
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
        random_seed=31,
        max_privacy_rows=100,
    )
