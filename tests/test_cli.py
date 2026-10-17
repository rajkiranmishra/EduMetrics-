"""Unit and regression tests for standalone CLI (main.py)."""

import os
import argparse
import tempfile
import pytest
from main import run_cli, infer_subject_configs, format_table
import pandas as pd


def test_infer_subject_configs():
    """Verify that lab/project subjects get 50 max marks and theory subjects get 100."""
    cols = ["student_id", "student_name", "department", "attendance", "Math", "Physics_Lab", "Project_1"]
    excluded = ["student_id", "student_name", "department", "attendance"]
    configs = infer_subject_configs(cols, excluded, "test.csv")
    assert configs == {"Math": 100.0, "Physics_Lab": 50.0, "Project_1": 50.0}


def test_format_table():
    """Verify format_table renders non-empty data without crash."""
    df = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
    text = format_table(df)
    assert "A" in text
    assert "x" in text
    assert format_table(pd.DataFrame()) == "  (No records)"


def test_cli_run_school_dataset(capsys):
    """Verify CLI runs cleanly on sample_school.csv."""
    args = argparse.Namespace(
        file="data/sample_school.csv",
        id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        dept_col="department",
        subject_pass=40.0,
        aggregate_pass=40.0,
        attendance_warning=75.0,
        disable_attendance_warning=False,
        preset=None,
        grade_boundaries=None,
        subject_pass_overrides=None,
        institution="Greenwood High",
        level="School",
        program="Grade 10",
        term="Annual 2026",
        top=5,
        export=None,
    )
    exit_code = run_cli(args)
    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "Greenwood High" in captured
    assert "Class 10" in captured or "Grade 10" in captured
    assert "Ishita Gupta" in captured


def test_cli_run_college_dataset_with_export(capsys):
    """Verify CLI runs cleanly on sample_college.csv with export option."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        export_path = tmp.name

    try:
        args = argparse.Namespace(
            file="data/sample_college.csv",
            id_col="student_id",
            name_col="student_name",
            attendance_col="attendance",
            dept_col="department",
            subject_pass=40.0,
            aggregate_pass=40.0,
            attendance_warning=75.0,
            disable_attendance_warning=False,
            preset="Example College",
            grade_boundaries=None,
            subject_pass_overrides="Algorithms:45.0",
            institution="Tech University",
            level="College",
            program="B.Tech CSE",
            term="Semester IV",
            top=5,
            export=export_path,
        )
        exit_code = run_cli(args)
        assert exit_code == 0
        assert os.path.exists(export_path)
        assert os.path.getsize(export_path) > 0
        captured = capsys.readouterr().out
        assert "Tech University" in captured
        assert "Zeenat Parveen" in captured
    finally:
        if os.path.exists(export_path):
            os.remove(export_path)


def test_cli_missing_file_returns_error(capsys):
    """Verify CLI exits with code 1 when the file does not exist."""
    args = argparse.Namespace(
        file="data/definitely_non_existent_file.csv",
        id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        dept_col="department",
        subject_pass=40.0,
        aggregate_pass=40.0,
        attendance_warning=75.0,
        disable_attendance_warning=False,
        preset=None,
        grade_boundaries=None,
        subject_pass_overrides=None,
        institution="",
        level="",
        program="",
        term="",
        top=5,
        export=None,
    )
    exit_code = run_cli(args)
    assert exit_code == 1
    captured = capsys.readouterr().out
    assert "Specified file not found" in captured


def test_cli_invalid_grade_boundaries_returns_error(capsys):
    """Verify CLI exits with code 1 when grade boundaries are malformed."""
    args = argparse.Namespace(
        file="data/sample_school.csv",
        id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        dept_col="department",
        subject_pass=40.0,
        aggregate_pass=40.0,
        attendance_warning=75.0,
        disable_attendance_warning=False,
        preset=None,
        grade_boundaries="A:80,B:90",  # Invalid order
        subject_pass_overrides=None,
        institution="",
        level="",
        program="",
        term="",
        top=5,
        export=None,
    )
    exit_code = run_cli(args)
    assert exit_code == 1
    captured = capsys.readouterr().out
    assert "POLICY CONFIGURATION ERROR" in captured
