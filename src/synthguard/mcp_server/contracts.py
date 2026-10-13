"""Typed MCP inputs that compose existing domain contracts."""

from pydantic import BaseModel, ConfigDict, Field

from synthguard.evaluation_core import EvaluationResult


class GateCandidateInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str = Field(min_length=1, max_length=200)
    evaluation: EvaluationResult
