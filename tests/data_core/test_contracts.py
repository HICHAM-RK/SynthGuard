from pathlib import Path

import pytest
from pydantic import ValidationError

import synthguard.data_core as data_core
from synthguard.data_core import DataCoreError, GenerationMethod, GenerationRequest, ProfileRequest


def test_profile_request_rejects_empty_source_path() -> None:
    with pytest.raises(ValidationError):
        ProfileRequest(source_path="")


@pytest.mark.parametrize("row_count", [0, 100_001])
def test_generation_request_rejects_out_of_range_row_count(row_count: int) -> None:
    with pytest.raises(ValidationError):
        GenerationRequest(
            source_path=Path("customers.csv"),
            output_directory=Path("runs"),
            method=GenerationMethod.GAUSSIAN_COPULA,
            row_count=row_count,
            random_seed=42,
        )


def test_generation_request_rejects_unknown_method() -> None:
    with pytest.raises(ValidationError):
        GenerationRequest(
            source_path=Path("customers.csv"),
            output_directory=Path("runs"),
            method="made-up-method",
            row_count=10,
            random_seed=42,
        )


def test_generation_request_rejects_empty_output_path() -> None:
    with pytest.raises(ValidationError):
        GenerationRequest(
            source_path=Path("customers.csv"),
            output_directory="",
            method=GenerationMethod.CTGAN,
            row_count=10,
            random_seed=42,
        )


def test_data_core_error_exposes_machine_readable_payload() -> None:
    error = DataCoreError(
        code="INVALID_CSV",
        message="The CSV structure is invalid.",
        details={"column_count": 0},
    )

    assert str(error) == "The CSV structure is invalid."
    assert error.to_dict() == {
        "code": "INVALID_CSV",
        "message": "The CSV structure is invalid.",
        "details": {"column_count": 0},
    }


def test_package_exports_only_the_contract_surface() -> None:
    assert set(data_core.__all__) == {
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
    }
