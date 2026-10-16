"""Academic grading and institutional pass/fail evaluation engine.

Implements:
1. Heterogeneous subject weight normalization:
   Percentage = (Total Marks Obtained / Total Maximum Possible Marks) * 100
2. Configurable grade boundaries with monotonicity and finiteness validation.
3. Independent subject-level and aggregate-level pass/fail evaluation.
4. Attendance shortage threshold flagging.
5. Actionable failure diagnostics distinguishing explicit absence from low scores.
6. Exact grade boundary and passing threshold preservation without floating point artifacts.
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
import pandas as pd
import numpy as np


class PolicyConfigurationError(Exception):
    """Raised when an academic grading policy has invalid boundaries or thresholds."""
    pass


@dataclass(frozen=True)
class GradeBoundary:
    """Represents a single grade bracket (e.g. Grade A: >= 80%)."""
    label: str
    min_percentage: float

    def __post_init__(self):
        if not isinstance(self.min_percentage, (int, float)) or not math.isfinite(self.min_percentage):
            raise PolicyConfigurationError(
                f"Grade boundary percentage for '{self.label}' must be a finite number, "
                f"got {self.min_percentage}."
            )
        if not (0.0 <= self.min_percentage <= 100.0):
            raise PolicyConfigurationError(
                f"Grade boundary percentage for '{self.label}' must be in [0.0, 100.0], "
                f"got {self.min_percentage}."
            )


@dataclass
class GradingPolicy:
    """Institutional grading and pass/fail policy configuration."""
    grade_boundaries: List[GradeBoundary] = field(default_factory=lambda: [
        GradeBoundary("A+", 90.0),
        GradeBoundary("A", 80.0),
        GradeBoundary("B+", 70.0),
        GradeBoundary("B", 60.0),
        GradeBoundary("C", 50.0),
        GradeBoundary("D", 40.0),
        GradeBoundary("F", 0.0),
    ])
    subject_pass_percentage: float = 40.0       # Minimum % needed in each individual subject
    aggregate_pass_percentage: float = 40.0     # Minimum overall % needed across all subjects
    attendance_warning_threshold: float = 75.0  # Attendance % below which a warning is issued

    def validate(self) -> None:
        """Validate that grade boundaries and pass thresholds are sound and finite."""
        for threshold_val, threshold_name in [
            (self.subject_pass_percentage, "Subject pass percentage"),
            (self.aggregate_pass_percentage, "Aggregate pass percentage"),
            (self.attendance_warning_threshold, "Attendance warning threshold"),
        ]:
            if not isinstance(threshold_val, (int, float)) or not math.isfinite(threshold_val):
                raise PolicyConfigurationError(
                    f"{threshold_name} must be a finite number, got {threshold_val}."
                )
            if not (0.0 <= float(threshold_val) <= 100.0):
                raise PolicyConfigurationError(
                    f"{threshold_name} must be in [0.0, 100.0], got {threshold_val}."
                )

        if not self.grade_boundaries:
            raise PolicyConfigurationError("Grade boundaries list cannot be empty.")

        # Boundaries must be strictly sorted in descending order of min_percentage
        prev_pct = 101.0
        for b in self.grade_boundaries:
            if b.min_percentage >= prev_pct:
                raise PolicyConfigurationError(
                    f"Grade boundaries must be strictly monotonically decreasing. "
                    f"Boundary '{b.label}' ({b.min_percentage}%) violates order after {prev_pct}%."
                )
            prev_pct = b.min_percentage

        # The lowest boundary must start at 0.0 to ensure every percentage is covered
        if self.grade_boundaries[-1].min_percentage > 0.0:
            raise PolicyConfigurationError(
                f"The lowest grade boundary must start at 0.0%, "
                f"got {self.grade_boundaries[-1].min_percentage}% for '{self.grade_boundaries[-1].label}'."
            )


def assign_grade_to_percentage(percentage: float, boundaries: List[GradeBoundary]) -> str:
    """Map a percentage score to a letter grade based on ordered boundaries."""
    if not isinstance(percentage, (int, float)) or not math.isfinite(percentage):
        raise ValueError(f"Percentage must be a finite number, got {percentage}.")

    # Defensively clamp percentage for grading lookup
    clamped_pct = max(0.0, min(100.0, float(percentage)))
    for boundary in boundaries:
        if clamped_pct >= boundary.min_percentage:
            return boundary.label
    return boundaries[-1].label


def evaluate_students(
    df: pd.DataFrame,
    student_id_col: str,
    name_col: str,
    attendance_col: str,
    subject_configs: Dict[str, float],
    policy: GradingPolicy,
    department_col: Optional[str] = None,
) -> pd.DataFrame:
    """Calculate totals, normalized percentages, grades, pass/fail status, and diagnostics.

    Returns:
        New DataFrame with standardized student performance columns.
    """
    policy.validate()

    # Verify structural columns exist in DataFrame
    required_cols = [
        (student_id_col, "Student ID"),
        (name_col, "Student Name"),
        (attendance_col, "Attendance"),
    ]
    for col_name, col_role in required_cols:
        if col_name not in df.columns:
            raise PolicyConfigurationError(f"{col_role} column '{col_name}' not found in DataFrame.")

    if not subject_configs:
        raise PolicyConfigurationError("At least one subject must be configured for evaluation.")

    for subj, max_m in subject_configs.items():
        if subj not in df.columns:
            raise PolicyConfigurationError(f"Subject column '{subj}' not found in DataFrame.")
        if not isinstance(max_m, (int, float)) or not math.isfinite(max_m) or max_m <= 0:
            raise PolicyConfigurationError(
                f"Maximum mark for subject '{subj}' must be a finite number > 0, got {max_m}."
            )

    total_possible_marks = sum(subject_configs.values())
    if not math.isfinite(total_possible_marks) or total_possible_marks <= 0:
        raise PolicyConfigurationError("Total possible marks across all subjects must be a finite number > 0.")

    if df.empty:
        return pd.DataFrame(columns=[
            "student_id", "student_name", "department", "attendance",
            *subject_configs.keys(),
            "total_marks", "max_marks", "average_marks", "percentage",
            "grade", "status", "failed_subject_count", "absent_subject_count",
            "absent_subjects", "failure_reason", "attendance_warning",
        ])

    evaluated_records = []

    for _, row in df.iterrows():
        sid = str(row[student_id_col]).strip()
        sname = str(row[name_col]).strip()
        dept = (
            str(row[department_col]).strip()
            if (department_col and department_col in df.columns and str(row[department_col]).strip().lower() not in ("", "nan", "none", "null"))
            else "General"
        )

        # Clean attendance
        att_raw = str(row[attendance_col]).strip().rstrip("%")
        try:
            att_num = float(att_raw) if att_raw else 0.0
            att_val = att_num if math.isfinite(att_num) else 0.0
        except (ValueError, TypeError):
            att_val = 0.0

        # Calculate subject scores and pass/fail
        subj_obtained = {}
        failed_subjects = []
        absent_subjects = []
        total_obtained = 0.0

        for subj, max_m in subject_configs.items():
            val_str = str(row[subj]).strip()
            is_absent = val_str.upper() in ("ABS", "ABSENT")

            if is_absent:
                score = 0.0
                absent_subjects.append(subj)
            else:
                try:
                    s_num = float(val_str)
                    score = s_num if math.isfinite(s_num) else 0.0
                except (ValueError, TypeError):
                    score = 0.0

            subj_obtained[subj] = score
            total_obtained += score

            # Check individual subject pass threshold (defend against floating-point epsilon)
            subj_pct = round((score / max_m) * 100.0, 4) if max_m > 0 else 0.0
            if subj_pct < policy.subject_pass_percentage:
                if is_absent:
                    failed_subjects.append(f"{subj} (ABSENT/{max_m:.0f})")
                else:
                    failed_subjects.append(f"{subj} ({score:.1f}/{max_m:.0f})")

        # Proportional percentage calculation
        raw_percentage = (total_obtained / total_possible_marks) * 100.0
        # Prevent floating-point epsilon artifacts from unfairly failing an exact pass threshold
        percentage = round(raw_percentage, 2)
        average_mark = round(total_obtained / len(subject_configs), 2)

        # Grade assignment
        grade = assign_grade_to_percentage(percentage, policy.grade_boundaries)

        # Pass / Fail evaluation (exact thresholds honored)
        agg_pass = (percentage >= policy.aggregate_pass_percentage) or (raw_percentage >= policy.aggregate_pass_percentage)
        subj_pass = len(failed_subjects) == 0

        is_passed = agg_pass and subj_pass
        status = "PASS" if is_passed else "FAIL"

        reasons = []
        if absent_subjects:
            reasons.append(f"Absent in: {', '.join(absent_subjects)}")
        if not subj_pass:
            reasons.append(f"Failed in: {', '.join(failed_subjects)}")
        if not agg_pass:
            reasons.append(
                f"Overall percentage {percentage:.1f}% below required {policy.aggregate_pass_percentage:.1f}%"
            )
        failure_reason = " | ".join(reasons) if reasons else "None"

        att_warning = bool(att_val < policy.attendance_warning_threshold)

        record = {
            "student_id": sid,
            "student_name": sname,
            "department": dept,
            "attendance": round(att_val, 2),
            **subj_obtained,
            "total_marks": round(total_obtained, 2),
            "max_marks": round(total_possible_marks, 2),
            "average_marks": average_mark,
            "percentage": percentage,
            "grade": grade,
            "status": status,
            "failed_subject_count": len(failed_subjects),
            "absent_subject_count": len(absent_subjects),
            "absent_subjects": ", ".join(absent_subjects) if absent_subjects else "None",
            "failure_reason": failure_reason,
            "attendance_warning": att_warning,
        }
        evaluated_records.append(record)

    return pd.DataFrame(evaluated_records)
