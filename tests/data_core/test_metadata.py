from __future__ import annotations

from pathlib import Path

import pytest
from sdv.metadata import Metadata

from synthguard.data_core import DataCoreError, ProfileRequest, SemanticType, profile_csv
from synthguard.data_core.metadata import build_sdv_metadata

FIXTURE = Path(__file__).parent / "fixtures" / "mixed_types.csv"


def test_metadata_contains_each_source_column_once() -> None:
    profile = profile_csv(ProfileRequest(source_path=FIXTURE))

    metadata = build_sdv_metadata(profile)

    columns = metadata["tables"]["table"]["columns"]
    assert list(columns) == [column.name for column in profile.columns]
    assert len(columns) == profile.column_count
    assert metadata["METADATA_SPEC_VERSION"] == "V1"


def test_valid_override_updates_metadata_without_mutating_profile() -> None:
    profile = profile_csv(ProfileRequest(source_path=FIXTURE))
    original = profile.model_copy(deep=True)

    metadata = build_sdv_metadata(profile, {"email": SemanticType.IDENTIFIER})

    assert metadata["tables"]["table"]["columns"]["email"] == {"sdtype": "id"}
    assert profile == original
    assert profile.inferred_metadata["columns"]["email"] == {"sdtype": "categorical"}


def test_unknown_override_column_fails_with_stable_error() -> None:
    profile = profile_csv(ProfileRequest(source_path=FIXTURE))

    with pytest.raises(DataCoreError) as caught:
        build_sdv_metadata(profile, {"missing_column": SemanticType.CATEGORICAL})

    assert caught.value.code == "INVALID_OVERRIDE"
    assert caught.value.details == {"column_name": "missing_column"}


def test_incompatible_override_fails_with_stable_error() -> None:
    profile = profile_csv(ProfileRequest(source_path=FIXTURE))

    with pytest.raises(DataCoreError) as caught:
        build_sdv_metadata(profile, {"age": SemanticType.DATETIME})

    assert caught.value.code == "INVALID_OVERRIDE"
    assert caught.value.details == {
        "column_name": "age",
        "semantic_type": "datetime",
    }


def test_generated_metadata_validates_with_locked_sdv() -> None:
    profile = profile_csv(ProfileRequest(source_path=FIXTURE))

    metadata = Metadata.load_from_dict(build_sdv_metadata(profile))

    assert metadata.validate() is None
