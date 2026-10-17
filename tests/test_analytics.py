"""Unit tests for core/analytics.py."""

import pytest
import pandas as pd
from core.grading import evaluate_students, GradingPolicy
from core.analytics import (
    compute_class_summary,
    compute_subject_analytics,
    compute_department_summary,
    get_top_performers,
    identify_academic_attention_cases,
)


@pytest.fixture
def evaluated_df(sample_school_df, default_policy) -> pd.DataFrame:
    """Pre-evaluated DataFrame fixture for analytics tests."""
    return evaluate_students(
        df=sample_school_df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0, "Science": 100.0},
        policy=default_policy,
        department_col="department",
    )


def test_class_summary_metrics(evaluated_df):
    """Verify class-level statistical calculations."""
    summary = compute_class_summary(evaluated_df)
    assert summary.total_students == 5
    assert summary.passed_students == 3
    assert summary.failed_students == 2
    assert summary.overall_pass_percentage == 60.0
    assert summary.top_student_name == "Alice"
    assert summary.top_student_id == "S01"
    assert summary.lowest_student_name == "Bob"
    assert summary.lowest_student_id == "S02"
    assert summary.attendance_shortage_count == 1  # Bob has 60% attendance


def test_subject_analytics_and_difficulty_ranking(evaluated_df):
    """Verify subject distributions and difficulty rankings."""
    subject_configs = {"Math": 100.0, "Science": 100.0}
    metrics = compute_subject_analytics(evaluated_df, subject_configs)
    assert len(metrics) == 2
    # Verify difficulty rank assignment (Rank 1 is hardest)
    ranks = [m.difficulty_rank for m in metrics]
    assert 1 in ranks
    assert 2 in ranks


def test_deterministic_top_performers_tie_breaking(default_policy):
    """Verify multi-key tie breaking: Percentage -> Attendance -> Student ID."""
    df = pd.DataFrame({
        "student_id": ["S03", "S01", "S02"],
        "student_name": ["Charlie", "Alice", "Bob"],
        "attendance": ["95.0", "90.0", "95.0"],
        "Math": ["80.0", "80.0", "80.0"],
    })
    df_eval = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
        policy=default_policy,
    )
    # All have 80.0% score.
    # Charlie (S03) and Bob (S02) have 95.0% attendance.
    # Between Bob (S02) and Charlie (S03), Bob comes first by student_id ascending.
    # Alice (S01) has 90.0% attendance, so comes 3rd.
    top = get_top_performers(df_eval, n=3)
    assert top.iloc[0]["student_id"] == "S02"  # Bob
    assert top.iloc[1]["student_id"] == "S03"  # Charlie
    assert top.iloc[2]["student_id"] == "S01"  # Alice


def test_academic_attention_indicators(default_policy):
    """Verify transparent heuristics identify all 4 attention categories correctly."""
    df = pd.DataFrame({
        "student_id": ["S01", "S02", "S03", "S04"],
        "student_name": ["HighAttLowScore", "LowAttLowScore", "SubjectOutlier", "BorderlinePass"],
        "attendance": ["92.0", "60.0", "85.0", "78.0"],
        "Math": ["45.0", "40.0", "90.0", "42.0"],
        "Science": ["48.0", "38.0", "30.0", "44.0"],
    })
    subject_configs = {"Math": 100.0, "Science": 100.0}
    df_eval = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs=subject_configs,
        policy=default_policy,
    )
    flagged = identify_academic_attention_cases(df_eval, subject_configs)
    categories = [f.category for f in flagged]

    assert "Conceptual Support Needed" in categories          # S01 (Att 92%, Score 46.5%)
    assert "Critical Intervention (Attendance & Academic)" in categories # S02 (Att 60%, Score 39%)
    assert "Subject-Specific Remediation" in categories      # S03 (Math 90, Science 30)
    assert "Borderline / At-Risk" in categories              # S04 (Score 43%, Passed)


def test_department_summary(evaluated_df):
    """Verify department grouping statistics."""
    df_dept = compute_department_summary(evaluated_df)
    assert len(df_dept) == 2  # Dept A and Dept B
    assert "average_percentage" in df_dept.columns
    assert "pass_percentage" in df_dept.columns


def test_empty_dataframe_analytics():
    """Verify that all analytics functions handle an empty DataFrame gracefully without errors."""
    empty_df = pd.DataFrame()
    summary = compute_class_summary(empty_df)
    assert summary.total_students == 0
    assert summary.overall_pass_percentage == 0.0
    assert summary.top_student_name == "N/A"

    subj_metrics = compute_subject_analytics(empty_df, {"Math": 100.0})
    assert subj_metrics == []

    dept_summary = compute_department_summary(empty_df)
    assert dept_summary.empty

    top_p = get_top_performers(empty_df, n=5)
    assert top_p.empty

    attention = identify_academic_attention_cases(empty_df, {"Math": 100.0})
    assert attention == []


def test_single_student_analytics(default_policy):
    """Verify statistical analytics for a single-student cohort (n = 1)."""
    df = pd.DataFrame({
        "student_id": ["S01"],
        "student_name": ["Alice"],
        "attendance": ["95.0"],
        "Math": ["90.0"],
    })
    df_eval = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
        policy=default_policy,
    )
    summary = compute_class_summary(df_eval)
    assert summary.total_students == 1
    assert summary.passed_students == 1
    assert summary.failed_students == 0
    assert summary.std_percentage == 0.0
    assert summary.top_student_id == "S01"
    assert summary.lowest_student_id == "S01"

    metrics = compute_subject_analytics(df_eval, {"Math": 100.0})
    assert len(metrics) == 1
    assert metrics[0].std_score == 0.0

