from __future__ import annotations

import json
from pathlib import Path

from synthguard.data_core import PhysicalType, ProfileRequest, SemanticType, profile_csv

FIXTURE = Path(__file__).parent / "fixtures" / "mixed_types.csv"


def test_profile_is_deterministic_and_preserves_column_order() -> None:
    request = ProfileRequest(source_path=FIXTURE)

    first = profile_csv(request)
    second = profile_csv(request)

    assert first == second
    assert [column.name for column in first.columns] == [
        "customer_id",
        "age",
        "income",
        "is_member",
        "joined_at",
        "segment",
        "email",
    ]
    assert first.row_count == 4
    assert first.column_count == 7
    json.loads(first.model_dump_json())


def test_profile_infers_physical_and_semantic_types() -> None:
    profile = profile_csv(ProfileRequest(source_path=FIXTURE))
    columns = {column.name: column for column in profile.columns}

    assert columns["customer_id"].physical_type is PhysicalType.STRING
    assert columns["customer_id"].semantic_type is SemanticType.IDENTIFIER
    assert columns["age"].physical_type is PhysicalType.INTEGER
    assert columns["age"].semantic_type is SemanticType.NUMERICAL
    assert columns["income"].physical_type is PhysicalType.FLOAT
    assert columns["is_member"].physical_type is PhysicalType.BOOLEAN
    assert columns["is_member"].semantic_type is SemanticType.BOOLEAN
    assert columns["joined_at"].physical_type is PhysicalType.STRING
    assert columns["joined_at"].semantic_type is SemanticType.DATETIME
    assert columns["segment"].semantic_type is SemanticType.CATEGORICAL


def test_profile_reports_nulls_cardinality_and_safe_summaries() -> None:
    profile = profile_csv(ProfileRequest(source_path=FIXTURE))
    columns = {column.name: column for column in profile.columns}

    assert columns["income"].null_rate == 0.25
    assert columns["segment"].cardinality == 2
    assert columns["customer_id"].unique_rate == 1.0

    serialized = profile.model_dump_json()
    assert "CUST-101" not in serialized
    assert "ada@example.test" not in serialized
    assert columns["segment"].safe_summary == {
        "category_count": 2,
        "most_frequent_count": 2,
    }


def test_sensitive_and_identifier_flags_are_advisory() -> None:
    profile = profile_csv(ProfileRequest(source_path=FIXTURE))
    columns = {column.name: column for column in profile.columns}

    assert columns["email"].is_sensitive_candidate is True
    assert columns["email"].sensitivity_reason == "column name suggests personal data"
    assert columns["customer_id"].semantic_type is SemanticType.IDENTIFIER
    assert {warning.code for warning in profile.warnings} == {
        "IDENTIFIER_CANDIDATE",
        "SENSITIVE_COLUMN_CANDIDATE",
    }


def test_profile_contains_reviewable_inferred_metadata() -> None:
    profile = profile_csv(ProfileRequest(source_path=FIXTURE))

    assert profile.inferred_metadata["columns"]["customer_id"] == {"sdtype": "id"}
    assert profile.inferred_metadata["columns"]["age"] == {"sdtype": "numerical"}
    assert profile.inferred_metadata["columns"]["joined_at"] == {"sdtype": "datetime"}
