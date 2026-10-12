"""Stable public contract for SynthGuard's evaluation-core module."""

from .contracts import (
    ClassificationUtilityResult,
    ColumnQualityScore,
    EvaluationCoreError,
    EvaluationRequest,
    EvaluationResult,
    EvaluationWarning,
    PrivacyEvidenceResult,
    StatisticalQualityResult,
    WeakArea,
)
from .service import evaluate_candidate

__all__ = [
    "ClassificationUtilityResult",
    "ColumnQualityScore",
    "EvaluationCoreError",
    "EvaluationRequest",
    "EvaluationResult",
    "EvaluationWarning",
    "PrivacyEvidenceResult",
    "StatisticalQualityResult",
    "WeakArea",
    "evaluate_candidate",
]
