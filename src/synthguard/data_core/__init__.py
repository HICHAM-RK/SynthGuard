"""Stable public contract for SynthGuard's data-core module."""

from .contracts import (
    ArtifactPaths,
    ColumnProfile,
    DataCoreError,
    DatasetProfile,
    DatasetWarning,
    GenerationMethod,
    GenerationRequest,
    GenerationResult,
    PhysicalType,
    ProfileRequest,
    SemanticType,
)
from .profiling import profile_csv
from .synthesis import generate_candidate

__all__ = [
    "ArtifactPaths",
    "ColumnProfile",
    "DataCoreError",
    "DatasetProfile",
    "DatasetWarning",
    "GenerationMethod",
    "GenerationRequest",
    "GenerationResult",
    "PhysicalType",
    "ProfileRequest",
    "SemanticType",
    "generate_candidate",
    "profile_csv",
]
