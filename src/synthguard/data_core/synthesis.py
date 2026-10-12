"""SDV synthesizer adapters for local candidate generation."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Protocol, cast

import pandas as pd
from sdv.metadata import Metadata
from sdv.single_table import CTGANSynthesizer, GaussianCopulaSynthesizer

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


@dataclass(frozen=True, slots=True)
class SynthesisOptions:
    """Internal tuning options; safe CPU defaults remain independent from tests."""

    ctgan_epochs: int = 300
    ctgan_batch_size: int = 500
    ctgan_pac: int = 10
    ctgan_enable_gpu: bool = False

    def __post_init__(self) -> None:
        if self.ctgan_epochs < 1:
            raise ValueError("ctgan_epochs must be positive")
        if self.ctgan_batch_size < 1:
            raise ValueError("ctgan_batch_size must be positive")
        if self.ctgan_pac < 1 or self.ctgan_batch_size % self.ctgan_pac:
            raise ValueError("ctgan_batch_size must be divisible by ctgan_pac")


class _Synthesizer(Protocol):
    def fit(self, data: pd.DataFrame) -> None: ...

    def sample(self, num_rows: int) -> pd.DataFrame: ...


def synthesize_candidate_data(
    request: GenerationRequest,
    *,
    options: SynthesisOptions | None = None,
) -> GeneratedCandidate:
    """Train the requested adapter and return generated rows in memory."""

    loaded = read_validated_csv(ProfileRequest(source_path=request.source_path))
    profile = build_profile(loaded)
    metadata_dict = build_sdv_metadata(profile, request.column_overrides)

    metadata = Metadata.load_from_dict(metadata_dict)
    synthesizer = _build_synthesizer(request.method, metadata, options or SynthesisOptions())
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


def _build_synthesizer(
    method: GenerationMethod,
    metadata: Metadata,
    options: SynthesisOptions,
) -> _Synthesizer:
    if method is GenerationMethod.GAUSSIAN_COPULA:
        return cast(_Synthesizer, GaussianCopulaSynthesizer(metadata))
    if method is GenerationMethod.CTGAN:
        return cast(
            _Synthesizer,
            CTGANSynthesizer(
                metadata,
                epochs=options.ctgan_epochs,
                batch_size=options.ctgan_batch_size,
                pac=options.ctgan_pac,
                enable_gpu=options.ctgan_enable_gpu,
                verbose=False,
            ),
        )
    raise DataCoreError(
        "UNSUPPORTED_METHOD",
        "The requested synthesis method is not available.",
        {"method": method.value},
    )
