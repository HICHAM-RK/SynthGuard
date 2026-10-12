"""Statistical-fidelity evidence through the current SDMetrics report API."""

from __future__ import annotations

import math
from importlib.metadata import version
from typing import Any

import pandas as pd
from sdmetrics.reports import QualityReport

from .contracts import (
    ColumnQualityScore,
    EvaluationCoreError,
    StatisticalQualityResult,
    WeakArea,
)
from .validation import ValidatedEvaluationPair

_COLUMN_SHAPES = "Column Shapes"
_COLUMN_PAIR_TRENDS = "Column Pair Trends"


def evaluate_statistical_quality(pair: ValidatedEvaluationPair) -> StatisticalQualityResult:
    """Measure distributions and column relationships without making a gate decision."""

    try:
        report = QualityReport()
        report.generate(
            {pair.table_name: pair.real},
            {pair.table_name: pair.synthetic},
            pair.metadata,
            verbose=False,
        )
        properties = report.get_properties()
        shape_details = report.get_details(_COLUMN_SHAPES)
        pair_details = report.get_details(_COLUMN_PAIR_TRENDS)

        column_scores = _column_scores(shape_details)
        weak_areas = _weak_areas(shape_details, pair_details)
        return StatisticalQualityResult(
            overall_score=_unit_score(report.get_score()),
            column_shapes_score=_property_score(properties, _COLUMN_SHAPES),
            column_pair_trends_score=_property_score(properties, _COLUMN_PAIR_TRENDS),
            column_scores=column_scores,
            weakest_areas=weak_areas,
            metric_provenance=f"SDMetrics QualityReport {version('sdmetrics')}",
        )
    except Exception as error:
        raise EvaluationCoreError(
            "STATISTICAL_EVALUATION_FAILED",
            "Statistical quality could not be evaluated for this candidate.",
        ) from error


def _property_score(properties: pd.DataFrame, property_name: str) -> float:
    matches = properties.loc[properties["Property"] == property_name, "Score"]
    if len(matches) != 1:
        raise ValueError("required SDMetrics property is unavailable")
    return _unit_score(matches.iloc[0])


def _column_scores(details: pd.DataFrame) -> tuple[ColumnQualityScore, ...]:
    scores = [
        ColumnQualityScore(column_name=str(row["Column"]), score=_unit_score(row["Score"]))
        for row in _records(details)
    ]
    return tuple(sorted(scores, key=lambda item: item.column_name))


def _weak_areas(
    shape_details: pd.DataFrame,
    pair_details: pd.DataFrame,
) -> tuple[WeakArea, ...]:
    areas = [
        WeakArea(kind="column_shape", name=str(row["Column"]), score=_unit_score(row["Score"]))
        for row in _records(shape_details)
    ]
    for row in _records(pair_details):
        first, second = sorted((str(row["Column 1"]), str(row["Column 2"])))
        areas.append(
            WeakArea(
                kind="column_pair_trend",
                name=f"{first} | {second}",
                score=_unit_score(row["Score"]),
            )
        )
    areas.sort(key=lambda item: (item.score, item.kind, item.name))
    return tuple(areas[:10])


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {str(key): value for key, value in record.items()}
        for record in frame.to_dict(orient="records")
    ]


def _unit_score(value: object) -> float:
    score = float(value)  # type: ignore[arg-type]
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        raise ValueError("metric score is outside the unit interval")
    return score
