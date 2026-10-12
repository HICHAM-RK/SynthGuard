"""Typed contracts for deterministic SynthGuard gate decisions."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from synthguard.evaluation_core import EvaluationResult


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class GateStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"


class CriterionStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"


class GatePolicy(ContractModel):
    min_statistical_score: float = Field(default=0.70, ge=0.0, le=1.0)
    max_exact_match_rate: float = Field(default=0.00, ge=0.0, le=1.0)
    max_near_duplicate_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    min_dcr_score: float = Field(default=0.50, ge=0.0, le=1.0)
    min_utility_retention: float = Field(default=0.80, ge=0.0, le=1.0)
    require_utility: bool = False


class CandidateEvidence(ContractModel):
    candidate_id: str = Field(min_length=1, max_length=200)
    evaluation: EvaluationResult

    @field_validator("candidate_id")
    @classmethod
    def candidate_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("candidate id must not be blank")
        return value


class GateRequest(ContractModel):
    candidates: tuple[CandidateEvidence, ...] = Field(min_length=1)
    policy: GatePolicy = Field(default_factory=GatePolicy)


class CriterionResult(ContractModel):
    name: str = Field(min_length=1)
    status: CriterionStatus
    observed_value: float | None
    threshold: float
    comparator: Literal[">=", "<="]
    explanation: str = Field(min_length=1)


class CandidateDecision(ContractModel):
    candidate_id: str = Field(min_length=1)
    rank: int = Field(ge=1)
    status: GateStatus
    composite_score: float = Field(ge=0.0, le=1.0)
    criteria: tuple[CriterionResult, ...]
    failed_criteria: tuple[str, ...] = ()


class GateResult(ContractModel):
    policy: GatePolicy
    candidates: tuple[CandidateDecision, ...]
    winner_candidate_id: str | None = None


class QualityGateError(Exception):
    """Expected gate failure with a stable machine-readable code."""

    def __init__(self, code: str, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})

    def to_dict(self) -> dict[str, object]:
        return {"code": self.code, "message": self.message, "details": self.details}
