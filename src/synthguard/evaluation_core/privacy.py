"""Transparent copy and proximity evidence for synthetic candidates."""

from __future__ import annotations

import math
from decimal import Decimal
from importlib.metadata import version
from numbers import Number
from threading import Lock
from typing import Any

import numpy as np
import pandas as pd
from sdmetrics.single_table import DCRBaselineProtection
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .contracts import EvaluationCoreError, EvaluationRequest, PrivacyEvidenceResult
from .validation import ValidatedEvaluationPair

_NEAR_DUPLICATE_THRESHOLD = 0.05
_DCR_RANDOM_LOCK = Lock()


def evaluate_privacy_evidence(
    pair: ValidatedEvaluationPair,
    request: EvaluationRequest,
) -> PrivacyEvidenceResult:
    """Measure exact copies and bounded proximity without claiming anonymity."""

    try:
        exact_match_count = _count_exact_matches(pair.real, pair.synthetic)
        real_sample = _bounded_sample(pair.real, request.max_privacy_rows, request.random_seed)
        synthetic_sample = _bounded_sample(
            pair.synthetic,
            request.max_privacy_rows,
            request.random_seed + 1,
        )
        distances = _nearest_distances(pair, real_sample, synthetic_sample)
        dcr_score = _dcr_score(
            real_sample,
            synthetic_sample,
            pair.metadata,
            pair.table_name,
            request.random_seed,
        )
        return PrivacyEvidenceResult(
            exact_match_count=exact_match_count,
            exact_match_rate=exact_match_count / len(pair.synthetic),
            near_duplicate_count=int(np.count_nonzero(distances <= _NEAR_DUPLICATE_THRESHOLD)),
            nearest_distance_min=float(np.min(distances)),
            nearest_distance_fifth_percentile=float(np.percentile(distances, 5)),
            nearest_distance_median=float(np.median(distances)),
            distance_threshold=_NEAR_DUPLICATE_THRESHOLD,
            dcr_baseline_protection_score=_unit_score(dcr_score),
            sampled_real_rows=len(real_sample),
            sampled_synthetic_rows=len(synthetic_sample),
            sampling_seed=request.random_seed,
            excluded_identifier_columns=pair.identifier_columns,
            metric_provenance=(
                f"SynthGuard normalized mixed-type distance; "
                f"SDMetrics DCRBaselineProtection {version('sdmetrics')}"
            ),
        )
    except Exception as error:
        raise EvaluationCoreError(
            "PRIVACY_EVALUATION_FAILED",
            "Privacy-risk evidence could not be evaluated for this candidate.",
        ) from error


def _count_exact_matches(real: pd.DataFrame, synthetic: pd.DataFrame) -> int:
    real_rows = {_normalized_row(row) for row in real.itertuples(index=False, name=None)}
    return sum(
        _normalized_row(row) in real_rows for row in synthetic.itertuples(index=False, name=None)
    )


def _normalized_row(row: tuple[object, ...]) -> tuple[tuple[str, object], ...]:
    return tuple(_normalized_value(value) for value in row)


def _normalized_value(value: object) -> tuple[str, object]:
    if _is_null(value):
        return ("null", "")
    if isinstance(value, (bool, np.bool_)):
        return ("boolean", bool(value))
    if isinstance(value, Number):
        return ("number", Decimal(str(value)).normalize())
    if isinstance(value, pd.Timestamp):
        return ("datetime", value.isoformat())
    return ("text", str(value))


def _is_null(value: object) -> bool:
    if value is None or value is pd.NA or value is pd.NaT:
        return True
    if isinstance(value, Decimal):
        return value.is_nan()
    if isinstance(value, (float, np.floating)):
        return math.isnan(float(value))
    return False


def _bounded_sample(frame: pd.DataFrame, limit: int, seed: int) -> pd.DataFrame:
    if len(frame) <= limit:
        return frame.copy(deep=True).reset_index(drop=True)
    return frame.sample(n=limit, random_state=seed).reset_index(drop=True)


def _nearest_distances(
    pair: ValidatedEvaluationPair,
    real_sample: pd.DataFrame,
    synthetic_sample: pd.DataFrame,
) -> np.ndarray[Any, np.dtype[np.float64]]:
    usable_columns = [
        column for column in real_sample.columns if column not in pair.identifier_columns
    ]
    if not usable_columns:
        raise ValueError("distance evaluation requires a non-identifier column")

    definitions = pair.metadata["tables"][pair.table_name]["columns"]
    numeric_columns = [
        column for column in usable_columns if definitions[column].get("sdtype") == "numerical"
    ]
    datetime_columns = [
        column for column in usable_columns if definitions[column].get("sdtype") == "datetime"
    ]
    categorical_columns = [
        column
        for column in usable_columns
        if column not in numeric_columns and column not in datetime_columns
    ]

    combined = pd.concat(
        [real_sample[usable_columns], synthetic_sample[usable_columns]],
        ignore_index=True,
    )
    for column in datetime_columns:
        parsed = pd.to_datetime(combined[column], errors="coerce", utc=True)
        numeric_dates = parsed.astype("int64").astype(float)
        combined[column] = numeric_dates.mask(parsed.isna())

    transformers: list[tuple[str, Pipeline, list[str]]] = []
    scaled_columns = numeric_columns + datetime_columns
    if scaled_columns:
        transformers.append(
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                        ("scaler", StandardScaler()),
                    ]
                ),
                scaled_columns,
            )
        )
    if categorical_columns:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        (
                            "imputer",
                            SimpleImputer(strategy="most_frequent", keep_empty_features=True),
                        ),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_columns,
            )
        )

    processor = ColumnTransformer(transformers=transformers)
    matrix = processor.fit_transform(combined)
    real_matrix = matrix[: len(real_sample)]
    synthetic_matrix = matrix[len(real_sample) :]
    neighbors = NearestNeighbors(n_neighbors=1, algorithm="brute")
    neighbors.fit(real_matrix)
    distances, _ = neighbors.kneighbors(synthetic_matrix)
    return np.asarray(distances[:, 0], dtype=float)


def _dcr_score(
    real: pd.DataFrame,
    synthetic: pd.DataFrame,
    metadata: dict[str, Any],
    table_name: str,
    seed: int,
) -> float:
    seeded_metric: Any = type(
        "_SeededDCRBaselineProtection",
        (DCRBaselineProtection,),
        {"_seed": seed},
    )
    with _DCR_RANDOM_LOCK:
        random_state = np.random.get_state()
        np.random.seed(seed)
        try:
            score = seeded_metric.compute(
                real_data=real,
                synthetic_data=synthetic,
                metadata=metadata,
                table_name=table_name,
                num_rows_subsample=None,
                num_iterations=1,
            )
        finally:
            np.random.set_state(random_state)
    return float(score)


def _unit_score(value: float) -> float:
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError("privacy metric score is outside the unit interval")
    return value
