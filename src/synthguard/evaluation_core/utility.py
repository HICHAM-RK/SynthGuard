"""Leakage-safe classification utility evidence for synthetic candidates."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .contracts import ClassificationUtilityResult, EvaluationCoreError, EvaluationRequest
from .validation import ValidatedEvaluationPair

_TEST_SIZE = 0.2
_MAX_ITERATIONS = 1_000


def evaluate_classification_utility(
    pair: ValidatedEvaluationPair,
    request: EvaluationRequest,
) -> ClassificationUtilityResult:
    """Compare two fixed classifiers on one untouched real holdout."""

    try:
        target = pair.classification_target
        if target is None or target != request.classification_target:
            raise ValueError("a validated classification target is required")

        definitions = pair.metadata["tables"][pair.table_name]["columns"]
        feature_definitions = {
            name: definition
            for name, definition in definitions.items()
            if name != target and name not in pair.identifier_columns
        }
        if not feature_definitions:
            raise ValueError("classification requires at least one non-identifier feature")

        real_features = _prepare_features(pair.real, feature_definitions)
        synthetic_features = _prepare_features(pair.synthetic, feature_definitions)
        real_target = pair.real[target]
        synthetic_target = pair.synthetic[target]
        real_train_x, real_test_x, real_train_y, real_test_y = train_test_split(
            real_features,
            real_target,
            test_size=_TEST_SIZE,
            random_state=request.random_seed,
            stratify=real_target,
        )

        real_pipeline = _build_pipeline(feature_definitions, request.random_seed)
        synthetic_pipeline = _build_pipeline(feature_definitions, request.random_seed)
        real_pipeline.fit(real_train_x, real_train_y)
        synthetic_pipeline.fit(synthetic_features, synthetic_target)
        real_score = _weighted_f1(real_test_y, real_pipeline.predict(real_test_x))
        synthetic_score = _weighted_f1(real_test_y, synthetic_pipeline.predict(real_test_x))
        retention = synthetic_score / real_score if real_score > 0.0 else None

        return ClassificationUtilityResult(
            target_name=target,
            class_count=int(real_target.nunique(dropna=True)),
            real_train_rows=len(real_train_x),
            real_test_rows=len(real_test_x),
            synthetic_train_rows=len(synthetic_features),
            metric_name="weighted_f1",
            real_train_score=real_score,
            synthetic_train_score=synthetic_score,
            utility_retention=retention,
            model_parameters={
                "class_weight": "none",
                "max_iter": _MAX_ITERATIONS,
                "random_seed": request.random_seed,
                "solver": "lbfgs",
                "test_size": _TEST_SIZE,
            },
        )
    except Exception as error:
        raise EvaluationCoreError(
            "UTILITY_EVALUATION_FAILED",
            "Classification utility could not be evaluated for this candidate.",
        ) from error


def _prepare_features(
    frame: pd.DataFrame,
    definitions: dict[str, Any],
) -> pd.DataFrame:
    prepared = frame[list(definitions)].copy(deep=True)
    for column, definition in definitions.items():
        if definition.get("sdtype") == "datetime":
            parsed = pd.to_datetime(prepared[column], errors="coerce", utc=True)
            numeric_dates = parsed.astype("int64").astype(float)
            prepared[column] = numeric_dates.mask(parsed.isna())
    return prepared


def _build_pipeline(definitions: dict[str, Any], seed: int) -> Pipeline:
    numeric_columns = [
        column
        for column, definition in definitions.items()
        if definition.get("sdtype") in {"numerical", "datetime"}
    ]
    categorical_columns = [column for column in definitions if column not in numeric_columns]
    transformers: list[tuple[str, Pipeline, list[str]]] = []
    if numeric_columns:
        transformers.append(
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_columns,
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
    classifier = LogisticRegression(
        solver="lbfgs",
        max_iter=_MAX_ITERATIONS,
        random_state=seed,
    )
    return Pipeline([("preprocessor", processor), ("classifier", classifier)])


def _weighted_f1(
    expected: pd.Series,
    predicted: np.ndarray[Any, np.dtype[Any]],
) -> float:
    return float(f1_score(expected, predicted, average="weighted", zero_division=0))
