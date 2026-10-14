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
        "student_id": ["S01"],
        "student_name": ["Alice"],
        "attendance": ["90"],
        "Math": ["ABS"],
    })
    res = validate_dataset(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
    )
    assert res.is_valid is True
