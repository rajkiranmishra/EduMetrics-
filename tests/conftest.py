"""Shared pytest fixtures for EduMetrics tests."""

import io
import pytest
import pandas as pd
from core.grading import GradingPolicy, GradeBoundary


@pytest.fixture
def sample_school_df() -> pd.DataFrame:
    """Standardized 5-student in-memory school DataFrame."""
    return pd.DataFrame({
        "student_id": ["S01", "S02", "S03", "S04", "S05"],
        "student_name": ["Alice", "Bob", "Charlie", "David", "Eve"],
        "department": ["A", "A", "B", "B", "B"],
        "attendance": ["95.0", "60.0", "88.0", "92.0", "90.0"],
        "Math": ["90.0", "30.0", "75.0", "42.0", "85.0"],
        "Science": ["95.0", "35.0", "80.0", "44.0", "32.0"],
    })


@pytest.fixture
def sample_college_df() -> pd.DataFrame:
    """Standardized DataFrame with heterogeneous max marks and leading zeros."""
    return pd.DataFrame({
        "student_id": ["001", "002", "003"],
        "student_name": ["John", "Jane", "Mark"],
        "department": ["CSE", "IT", "ECE"],
        "attendance": ["90.0", "72.0", "95.0"],
        "Theory_Course": ["85.0", "42.0", "92.0"],   # Max: 100
        "Lab_Course": ["45.0", "18.0", "48.0"],      # Max: 50
    })


@pytest.fixture
def default_policy() -> GradingPolicy:
    """Standard institutional grading policy fixture."""
    return GradingPolicy(
        subject_pass_percentage=40.0,
        aggregate_pass_percentage=40.0,
        attendance_warning_threshold=75.0,
    )
