"""Unit tests for core/loader.py."""

import pytest
import pandas as pd
from core.loader import load_csv_from_path, load_csv_from_bytes, IngestionError, detect_encoding


def test_sample_datasets_load_successfully():
    """Verify both baseline assignment datasets load without errors."""
    school_df, school_cols = load_csv_from_path("data/sample_school.csv")
    assert len(school_df) == 20
    assert "student_id" in school_cols
    assert "attendance" in school_cols

    college_df, college_cols = load_csv_from_path("data/sample_college.csv")
    assert len(college_df) == 25
    assert "Data_Structures" in college_cols
    assert "Database_Lab" in college_cols


def test_leading_zero_preservation():
    """Verify that student IDs with leading zeros ('001', '002') are preserved as strings."""
    college_df, _ = load_csv_from_path("data/sample_college.csv")
    first_id = college_df["student_id"].iloc[0]
    assert first_id == "001"
    assert isinstance(first_id, str)
    assert len(first_id) == 3


def test_duplicate_column_headers_rejected():
    """Verify that CSV with duplicate column names raises an IngestionError."""
    csv_bytes = b"student_id,name,attendance,Math,Math\nS01,Alice,90,80,85\n"
    with pytest.raises(IngestionError, match="duplicate column headers"):
        load_csv_from_bytes(csv_bytes, filename="dup.csv")


def test_empty_file_rejected():
    """Verify that 0-byte upload is rejected."""
    with pytest.raises(IngestionError, match="empty"):
        load_csv_from_bytes(b"", filename="empty.csv")


def test_encoding_detection():
    """Verify detection of UTF-8, UTF-8-BOM, and Latin-1."""
    utf8_bytes = "student_id,name\n1,Aarav".encode("utf-8")
    bom_bytes = b"\xef\xbb\xbf" + utf8_bytes
    latin1_bytes = "student_id,name\n1,Ren\xe9e".encode("latin-1")

    assert detect_encoding(utf8_bytes) == "utf-8"
    assert detect_encoding(bom_bytes) == "utf-8-sig"
    assert detect_encoding(latin1_bytes) == "latin-1"

    # Verify Latin-1 decodes properly in loader
    df, _ = load_csv_from_bytes(b"student_id,name,attendance\nS01,Ren\xe9e,90\n", "latin.csv")
    assert df["name"].iloc[0] == "Renée"


def test_missing_file_raises_ingestion_error():
    """Verify clean exception when file does not exist."""
    with pytest.raises(IngestionError, match="Could not open file"):
        load_csv_from_path("data/non_existent_file.csv")


def test_empty_column_header_rejected():
    """Verify that CSV with an empty column header raises IngestionError."""
    csv_bytes = b"student_id,name,,Math\nS01,Alice,90,80\n"
    with pytest.raises(IngestionError, match="empty or whitespace-only column header"):
        load_csv_from_bytes(csv_bytes, filename="empty_header.csv")


def test_duplicate_headers_after_whitespace_normalization_rejected():
    """Verify that column headers identical after trimming whitespace are rejected."""
    csv_bytes = b"student_id,name,Math, Math \nS01,Alice,90,80\n"
    with pytest.raises(IngestionError, match="duplicate column headers"):
        load_csv_from_bytes(csv_bytes, filename="dup_whitespace.csv")


def test_whitespace_only_file_rejected():
    """Verify that file containing only whitespace or blank lines is rejected."""
    csv_bytes = b"   \n\t\n   \r\n"
    with pytest.raises(IngestionError, match="contains no readable content"):
        load_csv_from_bytes(csv_bytes, filename="blank.csv")


def test_malformed_quoted_csv_rejected():
    """Verify that unclosed or malformed quotes in CSV raise an IngestionError."""
    csv_bytes = b'student_id,name,attendance\n"S01,Alice,90\n'
    with pytest.raises(IngestionError, match="Failed to parse CSV|Malformed CSV|Inconsistent row length"):
        load_csv_from_bytes(csv_bytes, filename="bad_quote.csv")


def test_inconsistent_row_length_rejected():
    """Verify that rows with mismatched number of columns raise IngestionError."""
    csv_bytes = b"student_id,name,attendance\nS01,Alice,90,ExtraColumnValue\n"
    with pytest.raises(IngestionError, match="Inconsistent row length|Failed to parse CSV"):
        load_csv_from_bytes(csv_bytes, filename="inconsistent_cols.csv")


def test_csv_with_no_data_rows_rejected():
    """Verify that CSV with only a header row and 0 data rows is rejected."""
    csv_bytes = b"student_id,student_name,attendance,Math\n"
    with pytest.raises(IngestionError, match="0 data rows"):
        load_csv_from_bytes(csv_bytes, filename="header_only.csv")

