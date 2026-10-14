"""Unit tests for core/reports.py."""

import pytest
import pandas as pd
from core.grading import evaluate_students, GradingPolicy
from core.analytics import (
    compute_class_summary,
    compute_subject_analytics,
    identify_academic_attention_cases,
)
from core.reports import generate_text_summary, generate_sanitized_csv


def test_generate_text_summary_contains_all_sections(sample_school_df, default_policy):
    """Verify that generated text report contains all required academic sections."""
    subject_configs = {"Math": 100.0, "Science": 100.0}
    df_eval = evaluate_students(
        df=sample_school_df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs=subject_configs,
        policy=default_policy,
        department_col="department",
    )
    summary = compute_class_summary(df_eval)
    subj_metrics = compute_subject_analytics(df_eval, subject_configs)
    attention = identify_academic_attention_cases(df_eval, subject_configs)

    report = generate_text_summary(
        class_summary=summary,
        subject_metrics=subj_metrics,
        attention_students=attention,
        policy=default_policy,
        dataset_name="Test School",
    )

    assert "EDUMETRICS ACADEMIC PERFORMANCE REPORT" in report
    assert "[1] APPLIED ACADEMIC POLICY" in report
    assert "[2] CLASS PERFORMANCE SUMMARY" in report
    assert "[3] GRADE DISTRIBUTION" in report
    assert "[4] SUBJECT-WISE PERFORMANCE & DIFFICULTY RANKING" in report
    assert "[5] ACADEMIC ATTENTION INDICATORS" in report
    assert "END OF REPORT" in report


def test_sanitized_csv_roundtrip(sample_school_df, default_policy):
    """Verify sanitized CSV generation produces parseable output."""
    subject_configs = {"Math": 100.0, "Science": 100.0}
    df_eval = evaluate_students(
        df=sample_school_df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs=subject_configs,
        policy=default_policy,
    )
    csv_bytes = generate_sanitized_csv(df_eval)
    assert len(csv_bytes) > 0

    # Parse back with pandas
    import io
    df_parsed = pd.read_csv(io.BytesIO(csv_bytes))
    assert len(df_parsed) == len(df_eval)
    assert "percentage" in df_parsed.columns
    assert "grade" in df_parsed.columns
    assert "status" in df_parsed.columns
