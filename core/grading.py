"""Academic grading and institutional pass/fail evaluation engine.

Implements:
1. Heterogeneous subject weight normalization:
   Percentage = (Total Marks Obtained / Total Maximum Possible Marks) * 100
2. Configurable grade boundaries with monotonicity and finiteness validation.
3. Full numerical precision evaluation separating calculation percentage from display percentage.
4. Independent subject-level and aggregate-level pass/fail evaluation.
5. Exact boundary and passing threshold preservation without premature rounding.
6. Fail-safe input validation on direct invocation without silent coercion.
7. Attendance shortage threshold flagging.
8. Actionable failure diagnostics distinguishing explicit absence from low scores.
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set, Any
import pandas as pd
import numpy as np


class PolicyConfigurationError(Exception):
    """Raised when an academic grading policy or evaluation configuration is invalid."""
    pass


# Machine precision comparison tolerance for IEEE 754 floating-point representations.
# Defends exact mathematical boundaries against binary representation artifacts (e.g. 39.99999999999999 vs 40.0)
# while strictly rejecting genuinely below-threshold scores (such as 39.996% or 79.999%).
MACHINE_EPSILON_TOLERANCE: float = 1e-12

SUPPORTED_ABSENCE_CODES: Set[str] = {"ABS", "ABSENT"}


@dataclass
class InstitutionMetadata:
    """Metadata representing the academic institution, level, program, and term."""
    institution_name: str = ""
    academic_level: str = "School"  # "School" | "College" | "University" | "Other"
    program_name: str = ""
    academic_term: str = ""
    term: Optional[str] = None

    def __post_init__(self):
        if self.term and not self.academic_term:
            self.academic_term = self.term
        elif self.academic_term and not self.term:
            self.term = self.academic_term

    def is_empty(self) -> bool:
        """Check if all descriptive institutional fields are unpopulated."""
        t = (self.term or self.academic_term or "").strip()
        return not any([
            (self.institution_name or "").strip(),
            (self.program_name or "").strip(),
            t,
        ]) and self.academic_level in ("Other", "School", "")

    def to_dict(self) -> Dict[str, str]:
        """Convert metadata to dictionary representation."""
        t = (self.term or self.academic_term or "").strip()
        return {
            "institution_name": (self.institution_name or "").strip(),
            "academic_level": (self.academic_level or "").strip(),
            "program_name": (self.program_name or "").strip(),
            "academic_term": t,
            "term": t,
        }


def is_greater_or_close(val: float, threshold: float, tol: float = MACHINE_EPSILON_TOLERANCE) -> bool:
    """Evaluate whether val >= threshold using full numerical precision with float artifact protection.

    Parameters:
        val: The calculated percentage or score value.
        threshold: The target boundary or pass threshold.
        tol: Absolute and relative comparison tolerance (default 1e-12).

    Returns:
        True if val >= threshold or mathematically equivalent within machine epsilon.
    """
    if val >= threshold:
        return True
    return math.isclose(val, threshold, rel_tol=tol, abs_tol=tol)


@dataclass(frozen=True)
class GradeBoundary:
    """Represents a single grade bracket (e.g. Grade A: >= 80%)."""
    label: str
    min_percentage: float

    def __post_init__(self):
        clean_label = str(self.label).strip()
        if not clean_label:
            raise PolicyConfigurationError("Grade boundary label cannot be empty.")
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


# Illustrative reference presets (not official universal regulations)
GRADING_PRESETS: Dict[str, List[GradeBoundary]] = {
    "Default EduMetrics": [
        GradeBoundary("A+", 90.0),
        GradeBoundary("A", 80.0),
        GradeBoundary("B+", 70.0),
        GradeBoundary("B", 60.0),
        GradeBoundary("C", 50.0),
        GradeBoundary("D", 40.0),
        GradeBoundary("F", 0.0),
    ],
    "Example School": [
        GradeBoundary("A+", 90.0),
        GradeBoundary("A", 80.0),
        GradeBoundary("B", 70.0),
        GradeBoundary("C", 60.0),
        GradeBoundary("D", 40.0),
        GradeBoundary("F", 0.0),
    ],
    "Example College": [
        GradeBoundary("O", 90.0),
        GradeBoundary("E", 80.0),
        GradeBoundary("A", 70.0),
        GradeBoundary("B", 60.0),
        GradeBoundary("C", 50.0),
        GradeBoundary("P", 40.0),
        GradeBoundary("F", 0.0),
    ],
}


def parse_grade_boundaries_string(spec: str) -> List[GradeBoundary]:
    """Parse a formatted grade boundaries string (e.g. 'A+:90,A:80,B:70,F:0')."""
    parts = [p.strip() for p in spec.split(",") if p.strip()]
    if not parts:
        raise PolicyConfigurationError("Grade boundary specification cannot be empty.")
    boundaries = []
    for part in parts:
        if ":" not in part:
            raise PolicyConfigurationError(
                f"Invalid grade boundary format '{part}'. Expected 'Label:Percentage' (e.g. 'A:80')."
            )
        lbl, pct_str = part.split(":", 1)
        lbl = lbl.strip()
        try:
            pct = float(pct_str.strip())
        except (ValueError, TypeError):
            raise PolicyConfigurationError(f"Non-numeric percentage '{pct_str.strip()}' for grade '{lbl}'.")
        boundaries.append(GradeBoundary(label=lbl, min_percentage=pct))
    return boundaries


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
    subject_pass_percentage: float = 40.0       # Minimum % needed in each individual subject by default
    subject_pass_overrides: Dict[str, float] = field(default_factory=dict)  # Subject-specific pass %
    aggregate_pass_percentage: float = 40.0     # Minimum overall % needed across all subjects
    attendance_warning_threshold: float = 75.0  # Attendance % below which a warning is issued
    enable_attendance_warning: bool = True      # Whether attendance is used as an academic warning indicator

    def get_subject_pass_threshold(self, subject: str) -> float:
        """Return the effective pass threshold percentage for a subject."""
        if self.subject_pass_overrides and subject in self.subject_pass_overrides:
            return float(self.subject_pass_overrides[subject])
        return float(self.subject_pass_percentage)

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

        if not isinstance(self.enable_attendance_warning, bool):
            raise PolicyConfigurationError("enable_attendance_warning must be a boolean.")

        if not isinstance(self.subject_pass_overrides, dict):
            raise PolicyConfigurationError("subject_pass_overrides must be a dictionary.")

        for subj, thresh in self.subject_pass_overrides.items():
            if not isinstance(thresh, (int, float)) or not math.isfinite(thresh):
                raise PolicyConfigurationError(
                    f"Subject pass threshold override for '{subj}' must be a finite number, got {thresh}."
                )
            if not (0.0 <= float(thresh) <= 100.0):
                raise PolicyConfigurationError(
                    f"Subject pass threshold override for '{subj}' must be in [0.0, 100.0], got {thresh}."
                )

        if not self.grade_boundaries or len(self.grade_boundaries) < 2:
            raise PolicyConfigurationError("At least two grade boundaries are required (e.g. Pass and Fail).")

        # Reject duplicate grade labels (case-insensitive check)
        labels_seen: Set[str] = set()
        for b in self.grade_boundaries:
            clean_label = b.label.strip()
            if not clean_label:
                raise PolicyConfigurationError("Grade boundary label cannot be empty.")
            norm_label = clean_label.upper()
            if norm_label in labels_seen:
                raise PolicyConfigurationError(f"Duplicate grade label '{b.label}' found. All grade boundary labels must be distinct.")
            labels_seen.add(norm_label)

        # Boundaries must be strictly sorted in descending order of min_percentage
        prev_pct = 101.0
        for b in self.grade_boundaries:
            if b.min_percentage >= prev_pct:
                raise PolicyConfigurationError(
                    f"Grade boundaries must be strictly monotonically decreasing. "
                    f"Grade boundary '{b.label}' ({b.min_percentage}%) must be strictly lower than preceding boundary ({prev_pct}%). "
                    f"Duplicate or increasing percentage boundaries are rejected."
                )
            prev_pct = b.min_percentage

        # The lowest boundary must start at 0.0 to ensure every percentage is covered
        if self.grade_boundaries[-1].min_percentage > 0.0:
            raise PolicyConfigurationError(
                f"The lowest grade boundary must start at 0.0% and must begin at 0.0%, "
                f"got {self.grade_boundaries[-1].min_percentage}% for '{self.grade_boundaries[-1].label}'."
            )


def assign_grade_to_percentage(percentage: float, boundaries: List[GradeBoundary]) -> str:
    """Map a percentage score to a letter grade based on ordered boundaries using full precision.

    Parameters:
        percentage: Unrounded percentage score (or display score).
        boundaries: List of GradeBoundary objects in strictly descending order.

    Returns:
        Letter grade label.
    """
    if not isinstance(percentage, (int, float)) or not math.isfinite(percentage):
        raise ValueError(f"Percentage must be a finite number, got {percentage}.")

    # Defensively clamp percentage for grading lookup
    clamped_pct = max(0.0, min(100.0, float(percentage)))
    for boundary in boundaries:
        if is_greater_or_close(clamped_pct, boundary.min_percentage):
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

    Guarantees:
    1. Input DataFrame is never mutated.
    2. Full numerical precision is preserved for grade assignments, subject passing,
       aggregate passing, and ranking.
    3. Premature rounding is prevented: rounded percentages are reserved solely for display.
    4. Fail-safe input validation rejects missing, non-numeric, non-finite, negative, or
       exceeding marks, invalid attendance, and missing student IDs/names with descriptive errors.
    5. Documented absence markers ('ABS', 'ABSENT') are preserved and evaluated as 0.0 marks.

    Returns:
        New DataFrame with standardized student performance columns.
    """
    if not isinstance(policy, GradingPolicy):
        raise PolicyConfigurationError(f"policy must be an instance of GradingPolicy, got {type(policy)}.")
    policy.validate()

    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"df must be a pandas DataFrame, got {type(df)}.")

    # Verify structural columns exist in DataFrame
    required_cols = [
        (student_id_col, "Student ID"),
        (name_col, "Student Name"),
        (attendance_col, "Attendance"),
    ]
    for col_name, col_role in required_cols:
        if not col_name or not isinstance(col_name, str):
            raise PolicyConfigurationError(f"Invalid column name for {col_role}: {col_name!r}")
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
            "total_marks", "max_marks", "average_marks",
            "percentage", "raw_percentage",
            "grade", "status", "failed_subject_count", "absent_subject_count",
            "absent_subjects", "failure_reason", "attendance_warning",
        ])

    evaluated_records = []

    for idx, row in df.iterrows():
        row_num = idx + 2  # 1-indexed, accounting for header row

        # 1. Validate mandatory Student ID
        val_id = row[student_id_col]
        if val_id is None or pd.isna(val_id):
            raise ValueError(f"Missing mandatory Student ID at row {row_num}.")
        sid = str(val_id).strip()
        if not sid or sid.lower() in ("nan", "none", "null"):
            raise ValueError(f"Missing mandatory Student ID at row {row_num}.")

        # 2. Validate mandatory Student Name
        val_name = row[name_col]
        if val_name is None or pd.isna(val_name):
            raise ValueError(f"Missing mandatory Student Name at row {row_num} (Student ID '{sid}').")
        sname = str(val_name).strip()
        if not sname or sname.lower() in ("nan", "none", "null"):
            raise ValueError(f"Missing mandatory Student Name at row {row_num} (Student ID '{sid}').")

        # 3. Department (optional)
        dept = (
            str(row[department_col]).strip()
            if (department_col and department_col in df.columns and str(row[department_col]).strip().lower() not in ("", "nan", "none", "null"))
            else "General"
        )

        # 4. Validate Attendance: must be present, finite, and in [0.0, 100.0]
        val_att = row[attendance_col]
        if val_att is None or pd.isna(val_att):
            raise ValueError(f"Missing mandatory Attendance value at row {row_num} (Student '{sid}').")
        att_raw = str(val_att).strip().rstrip("%")
        if not att_raw or att_raw.lower() in ("nan", "none", "null", "inf", "-inf", "+inf", "infinity", "-infinity", "+infinity"):
            raise ValueError(f"Invalid non-finite or empty Attendance '{val_att}' at row {row_num} (Student '{sid}').")
        try:
            att_num = float(att_raw)
        except (ValueError, TypeError):
            raise ValueError(f"Non-numeric Attendance '{val_att}' at row {row_num} (Student '{sid}').")
        if not math.isfinite(att_num):
            raise ValueError(f"Non-finite Attendance '{val_att}' at row {row_num} (Student '{sid}').")
        if not (0.0 <= att_num <= 100.0):
            raise ValueError(
                f"Attendance {att_num}% out of valid range [0.0, 100.0] at row {row_num} (Student '{sid}')."
            )
        att_val = float(att_num)

        # 5. Validate and calculate Subject scores
        subj_obtained = {}
        failed_subjects = []
        absent_subjects = []
        total_obtained = 0.0

        for subj, max_m in subject_configs.items():
            val_subj = row[subj]
            if val_subj is None or pd.isna(val_subj):
                raise ValueError(
                    f"Missing mark for subject '{subj}' at row {row_num} (Student '{sid}')."
                )
            val_str = str(val_subj).strip()
            if not val_str or val_str.lower() in ("nan", "none", "null"):
                raise ValueError(
                    f"Missing mark for subject '{subj}' at row {row_num} (Student '{sid}')."
                )

            # Check explicit documented absence markers
            if val_str.upper() in SUPPORTED_ABSENCE_CODES:
                score = 0.0
                is_absent = True
                absent_subjects.append(subj)
            else:
                if val_str.lower() in ("inf", "-inf", "+inf", "infinity", "-infinity", "+infinity"):
                    raise ValueError(
                        f"Non-finite mark '{val_subj}' for subject '{subj}' at row {row_num} (Student '{sid}')."
                    )
                try:
                    s_num = float(val_str)
                except (ValueError, TypeError):
                    raise ValueError(
                        f"Non-numeric mark '{val_subj}' for subject '{subj}' at row {row_num} (Student '{sid}')."
                    )
                if not math.isfinite(s_num):
                    raise ValueError(
                        f"Non-finite mark '{val_subj}' for subject '{subj}' at row {row_num} (Student '{sid}')."
                    )
                if s_num < 0.0:
                    raise ValueError(
                        f"Negative mark {s_num} for subject '{subj}' at row {row_num} (Student '{sid}')."
                    )
                if s_num > max_m:
                    raise ValueError(
                        f"Mark {s_num} exceeds maximum possible marks ({max_m}) for subject '{subj}' at row {row_num} (Student '{sid}')."
                    )
                score = float(s_num)
                is_absent = False

            subj_obtained[subj] = score
            total_obtained += score

            # Subject-level pass evaluation using full precision:
            raw_subj_pct = (score / max_m) * 100.0 if max_m > 0 else 0.0
            subj_thresh = policy.get_subject_pass_threshold(subj)
            if not is_greater_or_close(raw_subj_pct, subj_thresh):
                if is_absent:
                    failed_subjects.append(f"{subj} (ABSENT/{max_m:.0f})")
                else:
                    failed_subjects.append(f"{subj} ({score:.1f}/{max_m:.0f})")

        # Proportional percentage calculation using full precision
        raw_percentage = (total_obtained / total_possible_marks) * 100.0
        # Display percentage (rounded to 2 decimal places strictly for presentation)
        display_percentage = round(raw_percentage, 2)
        average_mark = round(total_obtained / len(subject_configs), 2)

        # Grade assignment using full available numerical precision (raw_percentage):
        grade = assign_grade_to_percentage(raw_percentage, policy.grade_boundaries)

        # Aggregate pass/fail evaluation using full available precision (raw_percentage):
        agg_pass = is_greater_or_close(raw_percentage, policy.aggregate_pass_percentage)
        subj_pass = len(failed_subjects) == 0

        is_passed = agg_pass and subj_pass
        status = "PASS" if is_passed else "FAIL"

        reasons = []
        if absent_subjects:
            reasons.append(f"Absent in: {', '.join(absent_subjects)}")
        if not subj_pass:
            reasons.append(f"Failed in: {', '.join(failed_subjects)}")
        if not agg_pass:
            pct_display = f"{raw_percentage:.3f}".rstrip("0").rstrip(".") if raw_percentage < policy.aggregate_pass_percentage else f"{raw_percentage:.2f}"
            reasons.append(
                f"Overall percentage {pct_display}% below required {policy.aggregate_pass_percentage:.1f}%"
            )
        failure_reason = " | ".join(reasons) if reasons else "None"

        att_warning = bool(policy.enable_attendance_warning and (att_val < policy.attendance_warning_threshold))

        record = {
            "student_id": sid,
            "student_name": sname,
            "department": dept,
            "attendance": round(att_val, 2),
            **subj_obtained,
            "total_marks": round(total_obtained, 2),
            "max_marks": round(total_possible_marks, 2),
            "average_marks": average_mark,
            "percentage": display_percentage,
            "raw_percentage": raw_percentage,
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
