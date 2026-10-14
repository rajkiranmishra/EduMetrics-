"""Unit tests for core/grading.py."""

import pytest
import pandas as pd
from core.grading import (
    GradingPolicy,
    GradeBoundary,
    PolicyConfigurationError,
    assign_grade_to_percentage,
    evaluate_students,
)


def test_monotonic_grade_boundaries_validation():
    """Verify that disordered grade boundaries raise PolicyConfigurationError."""
    # Invalid: B (75%) is higher than A (70%)
    invalid_boundaries = [
        GradeBoundary("A", 70.0),
        GradeBoundary("B", 75.0),
        GradeBoundary("F", 0.0),
    ]
    policy = GradingPolicy(grade_boundaries=invalid_boundaries)
    with pytest.raises(PolicyConfigurationError, match="monotonically decreasing"):
        policy.validate()


def test_lowest_grade_must_start_at_zero():
    """Verify that lowest boundary must be 0.0% to avoid unmapped gaps."""
    invalid_boundaries = [
        GradeBoundary("A", 80.0),
        GradeBoundary("B", 60.0),
        GradeBoundary("C", 40.0),  # Missing 0-39% coverage
    ]
    policy = GradingPolicy(grade_boundaries=invalid_boundaries)
    with pytest.raises(PolicyConfigurationError, match="lowest grade boundary must start at 0.0%"):
        policy.validate()


def test_assign_grade_to_percentage():
    """Verify mapping of percentages to correct letter grades."""
    boundaries = [
        GradeBoundary("A+", 90.0),
        GradeBoundary("A", 80.0),
        GradeBoundary("B", 60.0),
        GradeBoundary("F", 0.0),
    ]
    assert assign_grade_to_percentage(95.0, boundaries) == "A+"
    assert assign_grade_to_percentage(90.0, boundaries) == "A+"
    assert assign_grade_to_percentage(89.9, boundaries) == "A"
    assert assign_grade_to_percentage(60.0, boundaries) == "B"
    assert assign_grade_to_percentage(59.9, boundaries) == "F"
    assert assign_grade_to_percentage(0.0, boundaries) == "F"


def test_proportional_normalization_heterogeneous_marks(sample_college_df, default_policy):
    """Verify normalization when subjects have varying maximum marks (100 and 50)."""
    # Student 001: Theory 85/100, Lab 45/50 -> Total 130/150 -> 86.67%
    subject_configs = {"Theory_Course": 100.0, "Lab_Course": 50.0}
    df_res = evaluate_students(
        df=sample_college_df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs=subject_configs,
        policy=default_policy,
        department_col="department",
    )
    s1 = df_res[df_res["student_id"] == "001"].iloc[0]
    assert s1["total_marks"] == 130.0
    assert s1["max_marks"] == 150.0
    assert s1["percentage"] == 86.67
    assert s1["grade"] == "A"
    assert s1["status"] == "PASS"


def test_subject_level_fail_with_high_aggregate(default_policy):
    """Verify that failing ONE subject fails overall status even if aggregate % is high."""
    df = pd.DataFrame({
        "student_id": ["S01"],
        "student_name": ["Alice"],
        "attendance": ["95.0"],
        "Math": ["95.0"],
        "Science": ["25.0"],  # Failed in Science (<40%)
    })
    subject_configs = {"Math": 100.0, "Science": 100.0}
    df_res = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs=subject_configs,
        policy=default_policy,
    )
    s = df_res.iloc[0]
    assert s["percentage"] == 60.0   # Aggregate percentage is 60% (normally Grade B)
    assert s["status"] == "FAIL"     # But overall status is FAIL
    assert "Science" in s["failure_reason"]


def test_attendance_warning_flag(default_policy):
    """Verify attendance warning triggers when attendance < threshold."""
    df = pd.DataFrame({
        "student_id": ["S01", "S02"],
        "student_name": ["Alice", "Bob"],
        "attendance": ["80.0", "70.0"],  # S02 is below 75%
        "Math": ["80.0", "80.0"],
    })
    df_res = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
        policy=default_policy,
    )
    assert not df_res.iloc[0]["attendance_warning"]
    assert bool(df_res.iloc[1]["attendance_warning"]) is True
