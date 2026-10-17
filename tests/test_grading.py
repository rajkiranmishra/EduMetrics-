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


# =============================================================================
# FIX 02.1 REGRESSION TESTS: NUMERICAL PRECISION & FAIL-SAFE VALIDATION
# =============================================================================

def test_aggregate_percentage_immediately_below_pass_threshold():
    """Verify that actual percentage 39.996% with threshold 40.0% FAILS despite rounding to 40.00%."""
    # Subj1 (max 50) = 20.0 (40.0%, PASS)
    # Subj2 (max 200) = 79.99 (39.995%, PASS subject-level with 35% threshold)
    # Total = 99.99 / 250.0 = 39.996% (strictly below 40.0%)
    df = pd.DataFrame({
        "student_id": ["S_39996"],
        "student_name": ["NearPassStudent"],
        "attendance": ["90.0"],
        "Subj1": ["20.0"],
        "Subj2": ["79.99"],
    })
    subject_configs = {"Subj1": 50.0, "Subj2": 200.0}
    policy = GradingPolicy(
        subject_pass_percentage=35.0,
        aggregate_pass_percentage=40.0,
    )
    df_res = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs=subject_configs,
        policy=policy,
    )
    s = df_res.iloc[0]
    assert s["raw_percentage"] == pytest.approx(39.996, rel=1e-6)
    assert s["percentage"] == 40.0  # Display percentage is rounded
    assert s["failed_subject_count"] == 0  # Both subjects individually passed >= 35%
    assert s["status"] == "FAIL"  # But overall aggregate strictly fails 40.0%
    assert "Overall percentage 39.996% below required 40.0%" in s["failure_reason"]


def test_aggregate_percentage_exactly_at_pass_threshold():
    """Verify that actual percentage exactly 40.0% PASSES."""
    df = pd.DataFrame({
        "student_id": ["S_40000"],
        "student_name": ["ExactPassStudent"],
        "attendance": ["90.0"],
        "Subj1": ["20.0"],
        "Subj2": ["20.0"],
    })
    subject_configs = {"Subj1": 50.0, "Subj2": 50.0}
    policy = GradingPolicy(
        subject_pass_percentage=40.0,
        aggregate_pass_percentage=40.0,
    )
    df_res = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs=subject_configs,
        policy=policy,
    )
    s = df_res.iloc[0]
    assert s["raw_percentage"] == 40.0
    assert s["percentage"] == 40.0
    assert s["status"] == "PASS"
    assert s["failed_subject_count"] == 0


def test_aggregate_percentage_immediately_above_pass_threshold():
    """Verify that actual percentage slightly above 40.0% (40.001%) PASSES."""
    df = pd.DataFrame({
        "student_id": ["S_40001"],
        "student_name": ["JustAbovePassStudent"],
        "attendance": ["90.0"],
        "Subj1": ["40.001"],
    })
    subject_configs = {"Subj1": 100.0}
    policy = GradingPolicy(
        subject_pass_percentage=40.0,
        aggregate_pass_percentage=40.0,
    )
    df_res = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs=subject_configs,
        policy=policy,
    )
    s = df_res.iloc[0]
    assert s["raw_percentage"] == 40.001
    assert s["status"] == "PASS"


def test_grade_assignment_immediately_below_grade_boundary():
    """Verify that actual percentage 79.999% remains below Grade A threshold (receives B+)."""
    # 799.99 out of 1000.0 = 79.999%
    df = pd.DataFrame({
        "student_id": ["S_79999"],
        "student_name": ["NearAStudent"],
        "attendance": ["95.0"],
        "Subj": ["799.99"],
    })
    subject_configs = {"Subj": 1000.0}
    policy = GradingPolicy()
    df_res = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs=subject_configs,
        policy=policy,
    )
    s = df_res.iloc[0]
    assert s["raw_percentage"] == pytest.approx(79.999, rel=1e-6)
    assert s["percentage"] == 80.0  # Rounded display percentage
    assert s["grade"] == "B+"  # Full precision preserves B+, not promoted to A


def test_grade_assignment_exactly_at_grade_boundary():
    """Verify that actual percentage exactly 80.0% receives Grade A."""
    df = pd.DataFrame({
        "student_id": ["S_80000"],
        "student_name": ["ExactAStudent"],
        "attendance": ["95.0"],
        "Subj": ["800.0"],
    })
    subject_configs = {"Subj": 1000.0}
    policy = GradingPolicy()
    df_res = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs=subject_configs,
        policy=policy,
    )
    s = df_res.iloc[0]
    assert s["raw_percentage"] == 80.0
    assert s["grade"] == "A"


def test_subject_passing_immediately_below_threshold():
    """Verify that scoring 19.999 out of 50.0 (39.998%) fails a 40.0% subject threshold."""
    df = pd.DataFrame({
        "student_id": ["S_SubjFail"],
        "student_name": ["NearSubjectPass"],
        "attendance": ["90.0"],
        "Lab": ["19.999"],
    })
    subject_configs = {"Lab": 50.0}
    policy = GradingPolicy(subject_pass_percentage=40.0, aggregate_pass_percentage=40.0)
    df_res = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs=subject_configs,
        policy=policy,
    )
    s = df_res.iloc[0]
    assert s["failed_subject_count"] == 1
    assert s["status"] == "FAIL"
    assert "Lab" in s["failure_reason"]


def test_subject_passing_exactly_at_threshold():
    """Verify that scoring 20.0 out of 50.0 (40.0%) passes a 40.0% subject threshold."""
    df = pd.DataFrame({
        "student_id": ["S_SubjPass"],
        "student_name": ["ExactSubjectPass"],
        "attendance": ["90.0"],
        "Lab": ["20.0"],
    })
    subject_configs = {"Lab": 50.0}
    policy = GradingPolicy(subject_pass_percentage=40.0, aggregate_pass_percentage=40.0)
    df_res = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs=subject_configs,
        policy=policy,
    )
    s = df_res.iloc[0]
    assert s["failed_subject_count"] == 0
    assert s["status"] == "PASS"


def test_mixed_subject_maximum_marks_weighted_percentage():
    """Verify weighted normalization across heterogeneous subject maximum marks."""
    # Theory 80/100, Lab 40/50 -> Total 120/150 -> 80.00%
    df = pd.DataFrame({
        "student_id": ["S_Mixed"],
        "student_name": ["MixedStudent"],
        "attendance": ["90.0"],
        "Theory": ["80.0"],
        "Lab": ["40.0"],
    })
    subject_configs = {"Theory": 100.0, "Lab": 50.0}
    policy = GradingPolicy()
    df_res = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs=subject_configs,
        policy=policy,
    )
    s = df_res.iloc[0]
    assert s["total_marks"] == 120.0
    assert s["max_marks"] == 150.0
    assert s["raw_percentage"] == 80.0
    assert s["percentage"] == 80.0
    assert s["grade"] == "A"
    assert s["status"] == "PASS"


def test_direct_evaluation_rejects_non_numeric_marks(default_policy):
    """Verify direct evaluate_students call rejects unparseable strings with ValueError."""
    df = pd.DataFrame({
        "student_id": ["S01"],
        "student_name": ["Alice"],
        "attendance": ["90.0"],
        "Math": ["not_a_number"],
    })
    with pytest.raises(ValueError, match="Non-numeric mark 'not_a_number'"):
        evaluate_students(
            df=df,
            student_id_col="student_id",
            name_col="student_name",
            attendance_col="attendance",
            subject_configs={"Math": 100.0},
            policy=default_policy,
        )


def test_direct_evaluation_rejects_missing_marks(default_policy):
    """Verify direct evaluate_students call rejects missing or empty marks with ValueError."""
    for empty_val in ["", "   ", None, float("nan")]:
        df = pd.DataFrame({
            "student_id": ["S01"],
            "student_name": ["Alice"],
            "attendance": ["90.0"],
            "Math": [empty_val],
        })
        with pytest.raises(ValueError, match="Missing mark for subject 'Math'"):
            evaluate_students(
                df=df,
                student_id_col="student_id",
                name_col="student_name",
                attendance_col="attendance",
                subject_configs={"Math": 100.0},
                policy=default_policy,
            )


def test_direct_evaluation_rejects_nan_and_infinity(default_policy):
    """Verify direct evaluate_students call rejects NaN and Inf marks with ValueError."""
    for bad_mark in [float("nan"), float("inf"), float("-inf"), "NaN", "Inf", "-Infinity", "infinity"]:
        df = pd.DataFrame({
            "student_id": ["S01"],
            "student_name": ["Alice"],
            "attendance": ["90.0"],
            "Math": [bad_mark],
        })
        with pytest.raises(ValueError, match="(Missing mark|Non-finite mark)"):
            evaluate_students(
                df=df,
                student_id_col="student_id",
                name_col="student_name",
                attendance_col="attendance",
                subject_configs={"Math": 100.0},
                policy=default_policy,
            )


def test_direct_evaluation_rejects_negative_marks(default_policy):
    """Verify direct evaluate_students call rejects negative marks with ValueError."""
    df = pd.DataFrame({
        "student_id": ["S01"],
        "student_name": ["Alice"],
        "attendance": ["90.0"],
        "Math": ["-15.0"],
    })
    with pytest.raises(ValueError, match="Negative mark -15.0"):
        evaluate_students(
            df=df,
            student_id_col="student_id",
            name_col="student_name",
            attendance_col="attendance",
            subject_configs={"Math": 100.0},
            policy=default_policy,
        )


def test_direct_evaluation_rejects_marks_exceeding_maximum(default_policy):
    """Verify direct evaluate_students call rejects scores > subject max with ValueError."""
    df = pd.DataFrame({
        "student_id": ["S01"],
        "student_name": ["Alice"],
        "attendance": ["90.0"],
        "Math": ["105.0"],
    })
    with pytest.raises(ValueError, match="exceeds maximum possible marks"):
        evaluate_students(
            df=df,
            student_id_col="student_id",
            name_col="student_name",
            attendance_col="attendance",
            subject_configs={"Math": 100.0},
            policy=default_policy,
        )


def test_direct_evaluation_rejects_invalid_attendance(default_policy):
    """Verify direct evaluate_students call rejects missing, non-numeric, or out-of-range attendance."""
    bad_attendances = ["", "None", None, "abc", "-5.0", "105.0", float("nan"), float("inf")]
    for bad_att in bad_attendances:
        df = pd.DataFrame({
            "student_id": ["S01"],
            "student_name": ["Alice"],
            "attendance": [bad_att],
            "Math": ["80.0"],
        })
        with pytest.raises(ValueError, match="(Attendance|Missing mandatory Attendance)"):
            evaluate_students(
                df=df,
                student_id_col="student_id",
                name_col="student_name",
                attendance_col="attendance",
                subject_configs={"Math": 100.0},
                policy=default_policy,
            )


def test_direct_evaluation_rejects_missing_mandatory_identifiers(default_policy):
    """Verify direct evaluate_students call rejects missing student IDs and names."""
    # Missing ID
    df_no_id = pd.DataFrame({
        "student_id": [""],
        "student_name": ["Alice"],
        "attendance": ["90.0"],
        "Math": ["80.0"],
    })
    with pytest.raises(ValueError, match="Missing mandatory Student ID"):
        evaluate_students(
            df=df_no_id,
            student_id_col="student_id",
            name_col="student_name",
            attendance_col="attendance",
            subject_configs={"Math": 100.0},
            policy=default_policy,
        )

    # Missing Name
    df_no_name = pd.DataFrame({
        "student_id": ["S01"],
        "student_name": [None],
        "attendance": ["90.0"],
        "Math": ["80.0"],
    })
    with pytest.raises(ValueError, match="Missing mandatory Student Name"):
        evaluate_students(
            df=df_no_name,
            student_id_col="student_id",
            name_col="student_name",
            attendance_col="attendance",
            subject_configs={"Math": 100.0},
            policy=default_policy,
        )


def test_direct_evaluation_rejects_invalid_configurations(default_policy):
    """Verify direct evaluate_students call rejects invalid policies, subjects, and missing columns."""
    df = pd.DataFrame({
        "student_id": ["S01"],
        "student_name": ["Alice"],
        "attendance": ["90.0"],
        "Math": ["80.0"],
    })

    # Empty subject_configs
    with pytest.raises(PolicyConfigurationError, match="At least one subject must be configured"):
        evaluate_students(
            df=df,
            student_id_col="student_id",
            name_col="student_name",
            attendance_col="attendance",
            subject_configs={},
            policy=default_policy,
        )

    # Non-positive max marks
    with pytest.raises(PolicyConfigurationError, match="must be a finite number > 0"):
        evaluate_students(
            df=df,
            student_id_col="student_id",
            name_col="student_name",
            attendance_col="attendance",
            subject_configs={"Math": 0.0},
            policy=default_policy,
        )

    # Missing column
    with pytest.raises(PolicyConfigurationError, match="Student ID column 'wrong_id' not found"):
        evaluate_students(
            df=df,
            student_id_col="wrong_id",
            name_col="student_name",
            attendance_col="attendance",
            subject_configs={"Math": 100.0},
            policy=default_policy,
        )


def test_direct_evaluation_preserves_input_dataframe(default_policy):
    """Verify that evaluate_students does not mutate the caller's DataFrame in any way."""
    df_orig = pd.DataFrame({
        "student_id": ["S01", "S02"],
        "student_name": ["Alice", "Bob"],
        "attendance": ["90.0", "80.0"],
        "Math": ["85.0", "75.0"],
    })
    df_copy = df_orig.copy(deep=True)

    df_evaluated = evaluate_students(
        df=df_orig,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
        policy=default_policy,
    )

    # Verify input DataFrame is completely unchanged
    pd.testing.assert_frame_equal(df_orig, df_copy)
    # Output DataFrame has newly computed columns
    assert "raw_percentage" in df_evaluated.columns
    assert "percentage" in df_evaluated.columns


def test_unsupported_absence_indicators_rejected_in_direct_evaluation(default_policy):
    """Verify that unsupported absence strings (e.g. 'EXCUSED', '-') raise ValueError."""
    for bad_code in ["EXCUSED", "AB", "-", "MISSING", "NA"]:
        df = pd.DataFrame({
            "student_id": ["S01"],
            "student_name": ["Alice"],
            "attendance": ["90.0"],
            "Math": [bad_code],
        })
        with pytest.raises(ValueError, match="Non-numeric mark"):
            evaluate_students(
                df=df,
                student_id_col="student_id",
                name_col="student_name",
                attendance_col="attendance",
                subject_configs={"Math": 100.0},
                policy=default_policy,
            )


def test_top_performers_ranking_uses_unrounded_precision(default_policy):
    """Verify that get_top_performers ranks by unrounded raw_percentage when display percentage matches."""
    from core.analytics import get_top_performers

    # Student 1: 799.99 / 1000 = 79.999% (display: 80.00%)
    # Student 2: 799.95 / 1000 = 79.995% (display: 80.00%)
    # Both have identical attendance (90.0%)
    df = pd.DataFrame({
        "student_id": ["S_LOWER", "S_HIGHER"],
        "student_name": ["LowerPrecisionStudent", "HigherPrecisionStudent"],
        "attendance": ["90.0", "90.0"],
        "Subj": ["799.95", "799.99"],
    })
    df_eval = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Subj": 1000.0},
        policy=default_policy,
    )
    top = get_top_performers(df_eval, n=2)
    # S_HIGHER (79.999%) must rank #1 over S_LOWER (79.995%)
    assert top.iloc[0]["student_id"] == "S_HIGHER"
    assert top.iloc[1]["student_id"] == "S_LOWER"


# =============================================================================
# FIX 03: INSTITUTION CONFIGURATION & CUSTOM GRADING SYSTEM TESTS
# =============================================================================

def test_institution_metadata_data_class():
    """Verify InstitutionMetadata fields, term aliasing, empty check, and dictionary export."""
    from core.grading import InstitutionMetadata

    meta_empty = InstitutionMetadata()
    assert meta_empty.is_empty() is True

    meta1 = InstitutionMetadata(
        institution_name="Apex Global Academy",
        academic_level="School",
        program_name="Grade 10",
        academic_term="Term 1",
    )
    assert meta1.is_empty() is False
    assert meta1.term == "Term 1"
    d = meta1.to_dict()
    assert d["institution_name"] == "Apex Global Academy"
    assert d["academic_level"] == "School"
    assert d["academic_term"] == "Term 1"

    # Alias term in constructor
    meta2 = InstitutionMetadata(institution_name="Test College", term="Semester 2")
    assert meta2.academic_term == "Semester 2"
    assert meta2.term == "Semester 2"


def test_grading_presets_integrity():
    """Verify built-in reference presets are valid, monotonic, and start at 0.0%."""
    from core.grading import GRADING_PRESETS

    assert "Default EduMetrics" in GRADING_PRESETS
    assert "Example School" in GRADING_PRESETS
    assert "Example College" in GRADING_PRESETS

    for preset_name, boundaries in GRADING_PRESETS.items():
        pol = GradingPolicy(grade_boundaries=boundaries)
        pol.validate()
        assert boundaries[-1].min_percentage == 0.0
        assert boundaries[-1].label == "F"


def test_custom_school_and_college_grading_policies():
    """Verify evaluating datasets with Example School and Example College presets."""
    from core.grading import GRADING_PRESETS

    df = pd.DataFrame({
        "student_id": ["S1", "S2", "S3"],
        "student_name": ["Alice", "Bob", "Charlie"],
        "attendance": ["95.0", "90.0", "85.0"],
        "Math": ["92.0", "84.0", "72.0"],
    })

    # School policy evaluation
    school_policy = GradingPolicy(grade_boundaries=GRADING_PRESETS["Example School"])
    df_school = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
        policy=school_policy,
    )
    assert list(df_school["grade"]) == ["A+", "A", "B"]

    # College policy evaluation
    college_policy = GradingPolicy(grade_boundaries=GRADING_PRESETS["Example College"])
    df_college = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
        policy=college_policy,
    )
    assert list(df_college["grade"]) == ["O", "E", "A"]


def test_custom_grade_labels_and_evaluation():
    """Verify arbitrary custom grade labels evaluate accurately according to configured thresholds."""
    custom_bounds = [
        GradeBoundary("First Class with Distinction", 75.0),
        GradeBoundary("First Class", 60.0),
        GradeBoundary("Second Class", 50.0),
        GradeBoundary("Pass Class", 40.0),
        GradeBoundary("Unsuccessful", 0.0),
    ]
    policy = GradingPolicy(grade_boundaries=custom_bounds)
    policy.validate()

    df = pd.DataFrame({
        "student_id": ["1", "2", "3", "4", "5"],
        "student_name": ["A", "B", "C", "D", "E"],
        "attendance": ["90", "90", "90", "90", "90"],
        "Theory": ["80.0", "65.0", "55.0", "42.0", "30.0"],
    })
    df_eval = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Theory": 100.0},
        policy=policy,
    )
    assert list(df_eval["grade"]) == [
        "First Class with Distinction",
        "First Class",
        "Second Class",
        "Pass Class",
        "Unsuccessful",
    ]


def test_validation_rejects_duplicate_grade_labels():
    """Verify policy rejects duplicate grade labels (including case-insensitive matches)."""
    # Identical label
    with pytest.raises(PolicyConfigurationError, match="Duplicate grade label 'A' found"):
        GradingPolicy(grade_boundaries=[
            GradeBoundary("A", 90.0),
            GradeBoundary("A", 80.0),
            GradeBoundary("F", 0.0),
        ]).validate()

    # Case-insensitive match
    with pytest.raises(PolicyConfigurationError, match="Duplicate grade label 'a' found"):
        GradingPolicy(grade_boundaries=[
            GradeBoundary("A", 90.0),
            GradeBoundary("a", 80.0),
            GradeBoundary("F", 0.0),
        ]).validate()


def test_validation_rejects_duplicate_percentage_boundaries():
    """Verify policy rejects identical percentage thresholds across tiers."""
    with pytest.raises(PolicyConfigurationError, match="must be strictly lower than preceding boundary"):
        GradingPolicy(grade_boundaries=[
            GradeBoundary("A+", 80.0),
            GradeBoundary("A", 80.0),
            GradeBoundary("F", 0.0),
        ]).validate()


def test_validation_rejects_incorrect_boundary_ordering():
    """Verify policy rejects non-monotonic or inverted boundary percentage order."""
    with pytest.raises(PolicyConfigurationError, match="must be strictly lower than preceding boundary"):
        GradingPolicy(grade_boundaries=[
            GradeBoundary("A", 70.0),
            GradeBoundary("B", 80.0),
            GradeBoundary("F", 0.0),
        ]).validate()


def test_validation_rejects_missing_zero_percent_boundary():
    """Verify policy rejects boundary sets where the lowest boundary does not start at 0.0%."""
    with pytest.raises(PolicyConfigurationError, match="must begin at 0.0%"):
        GradingPolicy(grade_boundaries=[
            GradeBoundary("A", 90.0),
            GradeBoundary("B", 70.0),
            GradeBoundary("F", 35.0),
        ]).validate()


def test_validation_rejects_empty_grade_labels_and_fewer_than_two_boundaries():
    """Verify boundary labels cannot be empty and at least two boundaries are required."""
    with pytest.raises(PolicyConfigurationError, match="Grade boundary label cannot be empty"):
        GradeBoundary("   ", 50.0)

    with pytest.raises(PolicyConfigurationError, match="At least two grade boundaries are required"):
        GradingPolicy(grade_boundaries=[GradeBoundary("F", 0.0)]).validate()


def test_parse_grade_boundaries_string_utility():
    """Verify parse_grade_boundaries_string parses valid strings and raises on invalid formats."""
    from core.grading import parse_grade_boundaries_string

    spec = "A+:90, A:80, B:70, C:60, D:40, F:0"
    parsed = parse_grade_boundaries_string(spec)
    assert len(parsed) == 6
    assert parsed[0].label == "A+"
    assert parsed[0].min_percentage == 90.0
    assert parsed[-1].label == "F"
    assert parsed[-1].min_percentage == 0.0

    # Invalid specs
    with pytest.raises(PolicyConfigurationError, match="specification cannot be empty"):
        parse_grade_boundaries_string("   ")

    with pytest.raises(PolicyConfigurationError, match="Invalid grade boundary format"):
        parse_grade_boundaries_string("A+90,A80")

    with pytest.raises(PolicyConfigurationError, match="Non-numeric percentage"):
        parse_grade_boundaries_string("A:ninety,F:0")


def test_per_subject_passing_threshold_overrides():
    """Verify that custom per-subject passing thresholds enforce specific cutoffs per course."""
    policy = GradingPolicy(
        subject_pass_percentage=40.0,
        aggregate_pass_percentage=40.0,
        subject_pass_overrides={"Practical_Lab": 50.0},
    )
    policy.validate()

    # Student 1: 45/100 in Theory (>=40 -> PASS), 22/50 (44%) in Practical_Lab (<50 -> FAIL)
    # Student 2: 45/100 in Theory (>=40 -> PASS), 26/50 (52%) in Practical_Lab (>=50 -> PASS)
    df = pd.DataFrame({
        "student_id": ["S1", "S2"],
        "student_name": ["Alice", "Bob"],
        "attendance": ["90.0", "90.0"],
        "Theory": ["45.0", "45.0"],
        "Practical_Lab": ["22.0", "26.0"],
    })
    df_eval = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Theory": 100.0, "Practical_Lab": 50.0},
        policy=policy,
    )
    assert df_eval.loc[df_eval["student_id"] == "S1", "status"].iloc[0] == "FAIL"
    assert "Practical_Lab" in df_eval.loc[df_eval["student_id"] == "S1", "failure_reason"].iloc[0]
    assert df_eval.loc[df_eval["student_id"] == "S2", "status"].iloc[0] == "PASS"


def test_attendance_warning_toggle_and_separation_from_academic_pass():
    """Verify attendance shortage warning can be disabled and never fails a student academically."""
    # Policy with attendance warning enabled
    policy_warn_on = GradingPolicy(
        attendance_warning_threshold=75.0,
        enable_attendance_warning=True,
    )
    # Policy with attendance warning disabled
    policy_warn_off = GradingPolicy(
        attendance_warning_threshold=75.0,
        enable_attendance_warning=False,
    )

    df = pd.DataFrame({
        "student_id": ["S1"],
        "student_name": ["Alice"],
        "attendance": ["60.0"],  # Below 75%
        "Math": ["90.0"],        # Excellent academic score
    })

    df_warn_on = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
        policy=policy_warn_on,
    )
    assert bool(df_warn_on["attendance_warning"].iloc[0]) is True
    # Crucial rule: Low attendance does NOT cause academic failure
    assert df_warn_on["status"].iloc[0] == "PASS"

    df_warn_off = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
        policy=policy_warn_off,
    )
    assert bool(df_warn_off["attendance_warning"].iloc[0]) is False
    assert df_warn_off["status"].iloc[0] == "PASS"


def test_report_text_summary_includes_institution_metadata_and_policy():
    """Verify generate_text_summary includes metadata and detailed policy snapshot."""
    from core.reports import generate_text_summary
    from core.grading import InstitutionMetadata
    from core.analytics import compute_class_summary, compute_subject_analytics, identify_academic_attention_cases

    meta = InstitutionMetadata(
        institution_name="St. Xavier's International",
        academic_level="School",
        program_name="Class 10-A",
        academic_term="Mid-Term 2026",
    )
    policy = GradingPolicy(
        subject_pass_percentage=40.0,
        aggregate_pass_percentage=45.0,
        attendance_warning_threshold=80.0,
        subject_pass_overrides={"Science": 50.0},
    )

    df = pd.DataFrame({
        "student_id": ["1"],
        "student_name": ["Alice"],
        "attendance": ["85.0"],
        "Math": ["90.0"],
        "Science": ["80.0"],
    })
    sub_cfgs = {"Math": 100.0, "Science": 100.0}
    df_eval = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs=sub_cfgs,
        policy=policy,
    )
    summary = compute_class_summary(df_eval)
    metrics = compute_subject_analytics(df_eval, sub_cfgs, policy.subject_pass_overrides)
    attention = identify_academic_attention_cases(df_eval, sub_cfgs, policy.subject_pass_overrides)

    rep = generate_text_summary(
        class_summary=summary,
        subject_metrics=metrics,
        attention_students=attention,
        policy=policy,
        dataset_name="marks.csv",
        institution_metadata=meta,
    )
    assert "[0] INSTITUTION DETAILS" in rep
    assert "St. Xavier's International" in rep
    assert "Class 10-A" in rep
    assert "Mid-Term 2026" in rep
    assert "Subject Pass Overrides   : Science: 50.0%" in rep
    assert "Aggregate Pass Threshold : 45.0%" in rep


