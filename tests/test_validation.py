"""Unit tests for core/validation.py."""

import pytest
import pandas as pd
from core.validation import (
    validate_dataset,
    validate_student_ids,
    validate_attendance,
    validate_subject_scores,
    validate_required_columns,
)


def test_valid_dataset_passes_validation(sample_school_df):
    """Verify that a well-formed dataset passes with 0 errors."""
    subject_configs = {"Math": 100.0, "Science": 100.0}
    res = validate_dataset(
        df=sample_school_df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs=subject_configs,
        department_col="department",
    )
    assert res.is_valid is True
    assert res.error_count == 0


def test_missing_required_column(sample_school_df):
    """Verify error when mandatory column is missing."""
    subject_configs = {"Math": 100.0, "Science": 100.0}
    res = validate_dataset(
        df=sample_school_df,
        student_id_col="non_existent_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs=subject_configs,
    )
    assert res.is_valid is False
    assert any("non_existent_id" in err.message for err in res.errors)


def test_duplicate_student_id_rejected():
    """Verify detection of duplicate student IDs."""
    df = pd.DataFrame({
        "student_id": ["S01", "S01", "S02"],
        "student_name": ["Alice", "Bob", "Charlie"],
        "attendance": ["90", "85", "80"],
        "Math": ["75", "80", "85"],
    })
    res = validate_dataset(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
    )
    assert res.is_valid is False
    assert any("Duplicate Student ID detected: 'S01'" in err.message for err in res.errors)


def test_out_of_range_attendance():
    """Verify detection of attendance outside [0.0, 100.0] or non-numeric."""
    df = pd.DataFrame({
        "student_id": ["S01", "S02", "S03"],
        "student_name": ["Alice", "Bob", "Charlie"],
        "attendance": ["105.0", "-5.0", "eighty"],
        "Math": ["75", "80", "85"],
    })
    res = validate_dataset(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
    )
    assert res.is_valid is False
    assert res.error_count == 3


def test_out_of_range_subject_score():
    """Verify detection of scores > max mark or < 0."""
    df = pd.DataFrame({
        "student_id": ["S01", "S02"],
        "student_name": ["Alice", "Bob"],
        "attendance": ["90", "85"],
        "Lab": ["55.0", "-2.0"],  # Max is 50.0
    })
    res = validate_dataset(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Lab": 50.0},
    )
    assert res.is_valid is False
    assert res.error_count == 2
    assert any("out of valid range [0.0, 50.0]" in err.message for err in res.errors)


def test_absent_mark_allowed_without_error():
    """Verify that 'ABS' / 'ABSENT' marks are accepted gracefully."""
    df = pd.DataFrame({
        "student_id": ["S01", "S02"],
        "student_name": ["Alice", "Bob"],
        "attendance": ["90", "85"],
        "Math": ["ABS", "ABSENT"],
    })
    res = validate_dataset(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
    )
    assert res.is_valid is True


def test_missing_subject_column_does_not_crash_keyerror():
    """Verify that a subject present in config but missing from DataFrame is caught cleanly without KeyError."""
    df = pd.DataFrame({
        "student_id": ["S01"],
        "student_name": ["Alice"],
        "attendance": ["90"],
        "Math": ["85"],
    })
    # Subject 'Physics' is not in DataFrame
    res = validate_dataset(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0, "Physics": 100.0},
    )
    assert res.is_valid is False
    assert any("Physics" in err.message for err in res.errors)
    assert any("not found in dataset" in err.message for err in res.errors)


def test_empty_student_name_rejected():
    """Verify that empty, whitespace-only, or null student names are flagged with row numbers."""
    df = pd.DataFrame({
        "student_id": ["S01", "S02", "S03"],
        "student_name": ["", "   ", "nan"],
        "attendance": ["90", "85", "80"],
        "Math": ["80", "85", "90"],
    })
    res = validate_dataset(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
    )
    assert res.is_valid is False
    assert res.error_count == 3
    assert all("Missing or empty Student Name" in err.message for err in res.errors)
    assert [err.row for err in res.errors] == [2, 3, 4]


def test_legitimate_international_student_names_accepted():
    """Verify that diverse international characters, accents, hyphens, and apostrophes are accepted."""
    df = pd.DataFrame({
        "student_id": ["S01", "S02", "S03", "S04"],
        "student_name": ["Renée Müller", "José-María O'Connor", "Aarav Sharma", "李小龙"],
        "attendance": ["95.0", "90.0", "88.0", "92.0"],
        "Math": ["90.0", "85.0", "92.0", "98.0"],
    })
    res = validate_dataset(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
    )
    assert res.is_valid is True
    assert res.error_count == 0


def test_duplicate_student_id_case_insensitive():
    """Verify case-insensitive collision detection for student IDs ('S01' vs 's01')."""
    df = pd.DataFrame({
        "student_id": ["S01", "s01"],
        "student_name": ["Alice", "Bob"],
        "attendance": ["90", "85"],
        "Math": ["80", "85"],
    })
    res = validate_dataset(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
    )
    assert res.is_valid is False
    assert any("Duplicate Student ID detected" in err.message for err in res.errors)


def test_marks_containing_nan_rejected():
    """Verify that 'NaN', 'null', and empty mark cells are rejected as missing scores."""
    df = pd.DataFrame({
        "student_id": ["S01", "S02", "S03"],
        "student_name": ["Alice", "Bob", "Charlie"],
        "attendance": ["90", "85", "80"],
        "Math": ["NaN", "", "null"],
    })
    res = validate_dataset(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
    )
    assert res.is_valid is False
    assert res.error_count == 3
    assert all("Missing score in subject 'Math'" in err.message for err in res.errors)


def test_marks_containing_positive_and_negative_infinity_rejected():
    """Verify that positive and negative infinity in marks are rejected as non-finite."""
    df = pd.DataFrame({
        "student_id": ["S01", "S02", "S03"],
        "student_name": ["Alice", "Bob", "Charlie"],
        "attendance": ["90", "85", "80"],
        "Math": ["inf", "-inf", "Infinity"],
    })
    res = validate_dataset(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
    )
    assert res.is_valid is False
    assert res.error_count == 3
    assert all("Scores must be finite numbers" in err.message for err in res.errors)


def test_attendance_containing_infinity_rejected():
    """Verify that infinity values in attendance percentages are rejected."""
    df = pd.DataFrame({
        "student_id": ["S01", "S02"],
        "student_name": ["Alice", "Bob"],
        "attendance": ["inf", "-Infinity"],
        "Math": ["90", "85"],
    })
    res = validate_dataset(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
    )
    assert res.is_valid is False
    assert res.error_count == 2
    assert all("Invalid non-numeric attendance value" in err.message for err in res.errors)


def test_invalid_subject_max_marks_rejected():
    """Verify that non-finite, zero, or negative max marks are caught in validation."""
    df = pd.DataFrame({
        "student_id": ["S01"],
        "student_name": ["Alice"],
        "attendance": ["90"],
        "Math": ["80"],
    })
    # Non-finite or negative max marks
    for bad_max in [-10.0, 0.0, float("nan"), float("inf")]:
        res = validate_dataset(
            df=df,
            student_id_col="student_id",
            name_col="student_name",
            attendance_col="attendance",
            subject_configs={"Math": bad_max},
        )
        assert res.is_valid is False
        assert any("Invalid maximum mark" in err.message for err in res.errors)


def test_unsupported_absence_indicators_rejected():
    """Verify that unsupported absence strings (e.g. 'EXC', 'MED', 'A') are rejected."""
    df = pd.DataFrame({
        "student_id": ["S01", "S02", "S03"],
        "student_name": ["Alice", "Bob", "Charlie"],
        "attendance": ["90", "85", "80"],
        "Math": ["EXC", "MED", "A"],
    })
    res = validate_dataset(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
    )
    assert res.is_valid is False
    assert res.error_count == 3
    assert all("Invalid non-numeric score" in err.message for err in res.errors)


def test_empty_dataset_fails_validation():
    """Verify that an empty DataFrame fails validation cleanly."""
    empty_df = pd.DataFrame(columns=["student_id", "student_name", "attendance", "Math"])
    res = validate_dataset(
        df=empty_df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
    )
    assert res.is_valid is False
    assert any("0 data rows" in err.message for err in res.errors)

