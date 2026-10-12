"""SDV synthesizer adapters for local candidate generation."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

import pandas as pd
from sdv.metadata import Metadata
from sdv.single_table import GaussianCopulaSynthesizer

from .contracts import (
    DataCoreError,
    DatasetWarning,
    GenerationMethod,
    GenerationRequest,
    ProfileRequest,
)
from .ingestion import read_validated_csv
from .metadata import build_sdv_metadata
from .profiling import build_profile


@dataclass(frozen=True, slots=True)
class GeneratedCandidate:
    """In-memory candidate passed to the artifact boundary."""

    frame: pd.DataFrame
    method: GenerationMethod
    random_seed: int
    dataset_fingerprint: str
    reviewed_metadata: dict[str, Any]
    training_duration_seconds: float
    warnings: tuple[DatasetWarning, ...]


def synthesize_candidate_data(request: GenerationRequest) -> GeneratedCandidate:
    """Train the requested adapter and return generated rows in memory."""

    loaded = read_validated_csv(ProfileRequest(source_path=request.source_path))
    profile = build_profile(loaded)
    metadata_dict = build_sdv_metadata(profile, request.column_overrides)

    if request.method is not GenerationMethod.GAUSSIAN_COPULA:
        raise DataCoreError(
            "UNSUPPORTED_METHOD",
            "The requested synthesis method is not available.",
            {"method": request.method.value},
        )

    metadata = Metadata.load_from_dict(metadata_dict)
    synthesizer = GaussianCopulaSynthesizer(metadata)
    started_at = perf_counter()
    try:
        synthesizer.fit(loaded.frame)
        generated = synthesizer.sample(num_rows=request.row_count)
    except Exception as error:
        raise DataCoreError(
            "TRAINING_FAILED",
            "Synthetic candidate generation failed.",
            {"method": request.method.value},
        ) from error
    duration = perf_counter() - started_at

    if len(generated) != request.row_count:
        raise DataCoreError(
            "TRAINING_FAILED",
            "The synthesizer returned an unexpected row count.",
            {"method": request.method.value},
        )

    generated = generated.loc[:, loaded.frame.columns]
    return GeneratedCandidate(
        frame=generated,
        method=request.method,
        random_seed=request.random_seed,
        dataset_fingerprint=loaded.dataset_fingerprint,
        reviewed_metadata=metadata_dict,
        training_duration_seconds=duration,
        warnings=(
            DatasetWarning(
                code="SDV_REPRODUCIBILITY_LIMITATION",
                message=(
                    "The locked SDV API controls internal sampling state; exact results may "
                    "differ across dependency versions."
                ),
            ),
        ),
    )
