"""Public orchestration for one complete candidate evaluation."""

from __future__ import annotations

from time import perf_counter

from .contracts import EvaluationRequest, EvaluationResult, EvaluationWarning
from .privacy import evaluate_privacy_evidence
from .statistical import evaluate_statistical_quality
from .utility import evaluate_classification_utility
from .validation import load_evaluation_pair


def evaluate_candidate(request: EvaluationRequest) -> EvaluationResult:
    """Evaluate one synthetic artifact against its real source and metadata."""

    started_at = perf_counter()
    pair = load_evaluation_pair(request)
    statistical = evaluate_statistical_quality(pair)
    privacy = evaluate_privacy_evidence(pair, request)
    utility = (
        evaluate_classification_utility(pair, request)
        if request.classification_target is not None
        else None
    )
    warnings: tuple[EvaluationWarning, ...] = ()
    if utility is not None and utility.utility_retention is None:
        warnings = (
            EvaluationWarning(
                code="ZERO_REAL_UTILITY_BASELINE",
                message=(
                    "Utility retention is undefined because the real-trained baseline scored zero."
                ),
            ),
        )

    return EvaluationResult(
        real_fingerprint=pair.real_fingerprint,
        synthetic_fingerprint=pair.synthetic_fingerprint,
        real_row_count=len(pair.real),
        synthetic_row_count=len(pair.synthetic),
        column_count=len(pair.real.columns),
        statistical=statistical,
        privacy=privacy,
        utility=utility,
        warnings=warnings,
        evaluation_duration_seconds=perf_counter() - started_at,
    )
