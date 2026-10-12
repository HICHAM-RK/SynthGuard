from __future__ import annotations

from typing import Any, ClassVar

import pandas as pd
import pytest

from synthguard.evaluation_core import EvaluationCoreError
from synthguard.evaluation_core.statistical import evaluate_statistical_quality
from synthguard.evaluation_core.validation import ValidatedEvaluationPair


def test_realistic_candidate_scores_above_collapsed_candidate() -> None:
    real = pd.DataFrame(
        {
            "age": list(range(20, 70)) * 2,
            "segment": (["basic"] * 25 + ["premium"] * 25) * 2,
        }
    )
    realistic = real.sample(frac=1, random_state=7).reset_index(drop=True)
    collapsed = pd.DataFrame({"age": [20] * len(real), "segment": ["basic"] * len(real)})

    realistic_result = evaluate_statistical_quality(_pair(real, realistic))
    collapsed_result = evaluate_statistical_quality(_pair(real, collapsed))

    assert realistic_result.overall_score > collapsed_result.overall_score
    assert realistic_result.column_shapes_score > collapsed_result.column_shapes_score
    assert len(realistic_result.column_scores) == 2
    assert realistic_result.metric_provenance.startswith("SDMetrics QualityReport ")


def test_statistical_details_are_sorted_and_weak_areas_are_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "synthguard.evaluation_core.statistical.QualityReport",
        _DeterministicReport,
    )

    result = evaluate_statistical_quality(
        _pair(pd.DataFrame({"b": [1], "a": [2]}), pd.DataFrame({"b": [1], "a": [2]}))
    )

    assert [item.column_name for item in result.column_scores] == ["a", "b"]
    assert [item.score for item in result.column_scores] == [0.8, 0.2]
    assert [(item.kind, item.name, item.score) for item in result.weakest_areas] == [
        ("column_shape", "b", 0.2),
        ("column_pair_trend", "a | b", 0.4),
        ("column_shape", "a", 0.8),
    ]
    assert _DeterministicReport.generate_arguments["verbose"] is False


def test_statistical_failure_is_mapped_without_internal_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "private-source-value"

    class FailingReport:
        def generate(self, *_args: object, **_kwargs: object) -> None:
            raise RuntimeError(secret)

    monkeypatch.setattr("synthguard.evaluation_core.statistical.QualityReport", FailingReport)

    with pytest.raises(EvaluationCoreError) as caught:
        evaluate_statistical_quality(_pair(pd.DataFrame({"a": [1]}), pd.DataFrame({"a": [1]})))

    assert caught.value.code == "STATISTICAL_EVALUATION_FAILED"
    assert secret not in str(caught.value)
    assert secret not in repr(caught.value.to_dict())


class _DeterministicReport:
    generate_arguments: ClassVar[dict[str, Any]] = {}

    def generate(
        self,
        real_data: dict[str, pd.DataFrame],
        synthetic_data: dict[str, pd.DataFrame],
        metadata: dict[str, Any],
        *,
        verbose: bool,
    ) -> None:
        self.generate_arguments = {
            "real_data": real_data,
            "synthetic_data": synthetic_data,
            "metadata": metadata,
            "verbose": verbose,
        }
        type(self).generate_arguments = self.generate_arguments

    def get_score(self) -> float:
        return 0.5

    def get_properties(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"Property": "Column Pair Trends", "Score": 0.4},
                {"Property": "Column Shapes", "Score": 0.5},
            ]
        )

    def get_details(self, property_name: str) -> pd.DataFrame:
        if property_name == "Column Shapes":
            return pd.DataFrame(
                [
                    {"Column": "b", "Score": 0.2},
                    {"Column": "a", "Score": 0.8},
                ]
            )
        return pd.DataFrame([{"Column 1": "b", "Column 2": "a", "Score": 0.4}])


def _pair(real: pd.DataFrame, synthetic: pd.DataFrame) -> ValidatedEvaluationPair:
    columns = {
        column: {"sdtype": "numerical" if column in {"age", "a", "b"} else "categorical"}
        for column in real.columns
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
        identifier_columns=(),
        classification_target=None,
        real_fingerprint="a" * 64,
        synthetic_fingerprint="b" * 64,
        metadata_fingerprint="c" * 64,
    )
