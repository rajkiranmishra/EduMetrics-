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


def test_non_finite_grade_boundary_percentage_raises_error():
    """Verify that non-finite numbers (NaN, Inf) in GradeBoundary raise PolicyConfigurationError."""
    for bad_pct in [float("nan"), float("inf"), float("-inf")]:
        with pytest.raises(PolicyConfigurationError, match="must be a finite number"):
            GradeBoundary("A", bad_pct)


def test_non_finite_grading_policy_thresholds_raise_error():
    """Verify that non-finite numbers in policy thresholds raise PolicyConfigurationError."""
    # NaN in subject_pass_percentage
    p1 = GradingPolicy(subject_pass_percentage=float("nan"))
    with pytest.raises(PolicyConfigurationError, match="must be a finite number"):
        p1.validate()

    # Inf in aggregate_pass_percentage
    p2 = GradingPolicy(aggregate_pass_percentage=float("inf"))
    with pytest.raises(PolicyConfigurationError, match="must be a finite number"):
        p2.validate()

    # -Inf in attendance_warning_threshold
    p3 = GradingPolicy(attendance_warning_threshold=float("-inf"))
    with pytest.raises(PolicyConfigurationError, match="must be a finite number"):
        p3.validate()


def test_exact_grade_boundaries_mapping(default_policy):
    """Verify exact boundary values map precisely to expected grades."""
    boundaries = default_policy.grade_boundaries
    assert assign_grade_to_percentage(90.0, boundaries) == "A+"
    assert assign_grade_to_percentage(89.99, boundaries) == "A"
    assert assign_grade_to_percentage(80.0, boundaries) == "A"
    assert assign_grade_to_percentage(79.99, boundaries) == "B+"
    assert assign_grade_to_percentage(70.0, boundaries) == "B+"
    assert assign_grade_to_percentage(69.99, boundaries) == "B"
    assert assign_grade_to_percentage(60.0, boundaries) == "B"
    assert assign_grade_to_percentage(59.99, boundaries) == "C"
    assert assign_grade_to_percentage(50.0, boundaries) == "C"
    assert assign_grade_to_percentage(49.99, boundaries) == "D"
    assert assign_grade_to_percentage(40.0, boundaries) == "D"
    assert assign_grade_to_percentage(39.99, boundaries) == "F"
    assert assign_grade_to_percentage(0.0, boundaries) == "F"


def test_exact_passing_threshold_on_50_mark_subject(default_policy):
    """Verify that achieving exactly the 40.0% pass mark (20/50) passes without precision artifacts."""
    df = pd.DataFrame({
        "student_id": ["S01"],
        "student_name": ["Alice"],
        "attendance": ["90.0"],
        "Lab": ["20.0"],  # Exactly 20 out of 50 = 40.0%
    })
    df_res = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Lab": 50.0},
        policy=default_policy,
    )
    s = df_res.iloc[0]
    assert s["percentage"] == 40.0
    assert s["status"] == "PASS"
    assert s["failed_subject_count"] == 0


def test_missing_subject_column_in_evaluate_students_raises_policy_error(default_policy):
    """Verify that missing subject columns raise PolicyConfigurationError rather than KeyError."""
    df = pd.DataFrame({
        "student_id": ["S01"],
        "student_name": ["Alice"],
        "attendance": ["90.0"],
        "Math": ["80.0"],
    })
    with pytest.raises(PolicyConfigurationError, match="Subject column 'Science' not found"):
        evaluate_students(
            df=df,
            student_id_col="student_id",
            name_col="student_name",
            attendance_col="attendance",
            subject_configs={"Math": 100.0, "Science": 100.0},
            policy=default_policy,
        )


def test_empty_dataframe_in_evaluate_students(default_policy):
    """Verify that evaluate_students returns an empty DataFrame with expected columns if input is empty."""
    empty_df = pd.DataFrame(columns=["student_id", "student_name", "attendance", "Math"])
    df_res = evaluate_students(
        df=empty_df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
        policy=default_policy,
    )
    assert df_res.empty
    assert "percentage" in df_res.columns
    assert "status" in df_res.columns
    assert "absent_subjects" in df_res.columns


def test_single_student_dataset_in_evaluate_students(default_policy):
    """Verify evaluation on a single-student dataset."""
    df = pd.DataFrame({
        "student_id": ["S01"],
        "student_name": ["Solo"],
        "attendance": ["95.0"],
        "Math": ["85.0"],
    })
    df_res = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
        policy=default_policy,
    )
    assert len(df_res) == 1
    assert df_res.iloc[0]["percentage"] == 85.0
    assert df_res.iloc[0]["grade"] == "A"
    assert df_res.iloc[0]["status"] == "PASS"


def test_distinguish_absent_mark_from_attended_zero_score(default_policy):
    """Verify that calculations and record diagnostics clearly distinguish absent students from zero scores."""
    df = pd.DataFrame({
        "student_id": ["S01", "S02"],
        "student_name": ["ZeroScoreStudent", "AbsentStudent"],
        "attendance": ["90.0", "90.0"],
        "Math": ["0.0", "ABS"],
    })
    df_res = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
        policy=default_policy,
    )
    s_zero = df_res.iloc[0]
    s_absent = df_res.iloc[1]

    # Both have 0 marks and status FAIL
    assert s_zero["total_marks"] == 0.0
    assert s_zero["status"] == "FAIL"
    assert s_zero["absent_subject_count"] == 0
    assert s_zero["absent_subjects"] == "None"
    assert "Absent in" not in s_zero["failure_reason"]

    assert s_absent["total_marks"] == 0.0
    assert s_absent["status"] == "FAIL"
    assert s_absent["absent_subject_count"] == 1
    assert s_absent["absent_subjects"] == "Math"
    assert "Absent in: Math" in s_absent["failure_reason"]

