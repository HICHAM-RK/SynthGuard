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
]
