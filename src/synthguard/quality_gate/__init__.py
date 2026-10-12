"""Stable public contract for SynthGuard's quality-gate module."""

from .contracts import (
    CandidateDecision,
    CandidateEvidence,
    CriterionResult,
    CriterionStatus,
    GatePolicy,
    GateRequest,
    GateResult,
    GateStatus,
    QualityGateError,
)
from .service import apply_quality_gate

__all__ = [
    "CandidateDecision",
    "CandidateEvidence",
    "CriterionResult",
    "CriterionStatus",
    "GatePolicy",
    "GateRequest",
    "GateResult",
    "GateStatus",
    "QualityGateError",
    "apply_quality_gate",
]
