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
    "profile_csv",
]
