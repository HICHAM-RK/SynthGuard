from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from synthguard.data_core import DataCoreError, ProfileRequest
from synthguard.data_core.ingestion import read_validated_csv

FIXTURE = Path(__file__).parent / "fixtures" / "customers.csv"


def test_reads_valid_csv_and_preserves_column_order() -> None:
    loaded = read_validated_csv(ProfileRequest(source_path=FIXTURE))

    assert loaded.frame.columns.tolist() == [
        "customer_id",
        "age",
        "income",
        "is_member",
        "joined_at",
        "segment",
    ]
    assert len(loaded.frame) == 3
    assert loaded.dataset_fingerprint == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()


def test_accepts_utf8_with_bom(tmp_path: Path) -> None:
    source = tmp_path / "bom.csv"
    source.write_bytes("name,city\nAda,Paris\n".encode("utf-8-sig"))

    loaded = read_validated_csv(ProfileRequest(source_path=source))

    assert loaded.frame.columns.tolist() == ["name", "city"]
    assert loaded.frame.iloc[0].to_dict() == {"name": "Ada", "city": "Paris"}


@pytest.mark.parametrize(
    ("content", "expected_code"),
    [
        (b"", "EMPTY_DATASET"),
        (b"name,city\nAda,Paris,extra\n", "INVALID_CSV"),
        (b'name,city\n"Ada,Paris\n', "INVALID_CSV"),
        (b"\xff\xfe\x00\x00", "UNSUPPORTED_ENCODING"),
    ],
)
def test_rejects_invalid_sources(tmp_path: Path, content: bytes, expected_code: str) -> None:
    source = tmp_path / "invalid.csv"
    source.write_bytes(content)

    with pytest.raises(DataCoreError) as caught:
        read_validated_csv(ProfileRequest(source_path=source))

    assert caught.value.code == expected_code


def test_rejects_missing_source_without_exposing_path(tmp_path: Path) -> None:
    source = tmp_path / "private" / "customers.csv"

    with pytest.raises(DataCoreError) as caught:
        read_validated_csv(ProfileRequest(source_path=source))

    assert caught.value.code == "FILE_NOT_FOUND"
    assert str(source) not in str(caught.value)
    assert str(source) not in repr(caught.value.to_dict())


def test_rejects_file_above_byte_limit() -> None:
    with pytest.raises(DataCoreError) as caught:
        read_validated_csv(ProfileRequest(source_path=FIXTURE, max_bytes=10))

    assert caught.value.code == "FILE_TOO_LARGE"
    assert caught.value.details["max_bytes"] == 10


def test_rejects_file_above_row_limit() -> None:
    with pytest.raises(DataCoreError) as caught:
        read_validated_csv(ProfileRequest(source_path=FIXTURE, max_rows=2))

    assert caught.value.code == "ROW_LIMIT_EXCEEDED"
    assert caught.value.details["max_rows"] == 2


def test_rejection_does_not_echo_source_values(tmp_path: Path) -> None:
    secret_value = "private-person@example.test"
    source = tmp_path / "malformed.csv"
    source.write_text(f"name,email\nAda,{secret_value},extra\n", encoding="utf-8")

    with pytest.raises(DataCoreError) as caught:
        read_validated_csv(ProfileRequest(source_path=source))

    assert secret_value not in str(caught.value)
    assert secret_value not in repr(caught.value.to_dict())


def test_reading_does_not_modify_source() -> None:
    before = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()

    read_validated_csv(ProfileRequest(source_path=FIXTURE))

    after = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert after == before
