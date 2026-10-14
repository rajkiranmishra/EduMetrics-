"""Academic dataset schema and value validation.

Performs deterministic, row-and-column-level validation:
1. Verifies presence of mandatory columns.
2. Enforces unique, non-null Student Identifiers (preserving leading zeros).
3. Validates Attendance percentages within [0.0, 100.0].
4. Validates Subject scores within [0.0, SubjectMaxMark].
5. Flags missing or unparseable numeric values with human-friendly row references.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import pandas as pd
import numpy as np


@dataclass(frozen=True)
class ValidationError:
    """Represents a specific validation finding."""
    message: str
    row: Optional[int] = None       # 1-indexed spreadsheet row number
    column: Optional[str] = None
    severity: str = "ERROR"        # "ERROR" or "WARNING"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row": self.row,
            "column": self.column,
            "message": self.message,
            "severity": self.severity,
        }

    def __str__(self) -> str:
        loc = []
        if self.row is not None:
            loc.append(f"Row {self.row}")
        if self.column is not None:
            loc.append(f"Column '{self.column}'")
        loc_str = f"[{', '.join(loc)}] " if loc else ""
        return f"{self.severity}: {loc_str}{self.message}"


@dataclass
class ValidationResult:
    """Aggregated validation findings for a dataset."""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def summary(self) -> str:
        if self.is_valid:
            return f"Validation Passed: 0 errors, {self.warning_count} warnings."
        return f"Validation Failed: {self.error_count} errors, {self.warning_count} warnings."


def validate_required_columns(
    df: pd.DataFrame,
    student_id_col: str,
    name_col: str,
    attendance_col: str,
    subject_cols: List[str],
    department_col: Optional[str] = None,
) -> List[ValidationError]:
    """Check that all required mapped columns exist in the DataFrame."""
    errors: List[ValidationError] = []
    df_cols = set(df.columns)

    if student_id_col not in df_cols:
        errors.append(ValidationError(
            message=f"Mandatory Student ID column '{student_id_col}' not found in dataset.",
            column=student_id_col,
        ))
    if name_col not in df_cols:
        errors.append(ValidationError(
            message=f"Mandatory Student Name column '{name_col}' not found in dataset.",
            column=name_col,
        ))
    if attendance_col not in df_cols:
        errors.append(ValidationError(
            message=f"Mandatory Attendance column '{attendance_col}' not found in dataset.",
            column=attendance_col,
        ))
    if not subject_cols:
        errors.append(ValidationError(
            message="At least one subject column must be mapped for academic analysis.",
        ))
    for subj in subject_cols:
        if subj not in df_cols:
            errors.append(ValidationError(
                message=f"Mapped subject column '{subj}' not found in dataset.",
                column=subj,
            ))
    if department_col and department_col not in df_cols:
        errors.append(ValidationError(
            message=f"Mapped Department column '{department_col}' not found in dataset.",
            column=department_col,
            severity="WARNING",
        ))

    return errors


def validate_student_ids(df: pd.DataFrame, student_id_col: str) -> List[ValidationError]:
    """Verify that student IDs are non-null, non-empty, and unique."""
    errors: List[ValidationError] = []
    series = df[student_id_col].astype(str).str.strip()

    # Check for empty / whitespace / "nan" strings
    for idx, val in enumerate(series):
        row_num = idx + 2  # 1-indexed, accounting for header row
        if not val or val.lower() in ("nan", "none", "null"):
            errors.append(ValidationError(
                message="Missing or empty Student ID.",
                row=row_num,
                column=student_id_col,
            ))

    # Check for duplicates
    duplicates = series[series.duplicated(keep=False)]
    if not duplicates.empty:
        seen = set()
        for idx, val in duplicates.items():
            row_num = idx + 2
            errors.append(ValidationError(
                message=f"Duplicate Student ID detected: '{val}'.",
                row=row_num,
                column=student_id_col,
            ))

    return errors


def validate_attendance(df: pd.DataFrame, attendance_col: str) -> List[ValidationError]:
    """Verify that attendance values are valid numeric percentages [0.0, 100.0]."""
    errors: List[ValidationError] = []
    raw_series = df[attendance_col]

    for idx, val in enumerate(raw_series):
        row_num = idx + 2
        val_str = str(val).strip().rstrip("%")
        try:
            num = float(val_str)
            if np.isnan(num):
                errors.append(ValidationError(
                    message="Missing attendance value.",
                    row=row_num,
                    column=attendance_col,
                ))
            elif num < 0.0 or num > 100.0:
                errors.append(ValidationError(
                    message=f"Attendance percentage out of range [0.0, 100.0]: {num}%.",
                    row=row_num,
                    column=attendance_col,
                ))
        except (ValueError, TypeError):
            errors.append(ValidationError(
                message=f"Invalid non-numeric attendance value: '{val}'.",
                row=row_num,
                column=attendance_col,
            ))

    return errors


def validate_subject_scores(
    df: pd.DataFrame,
    subject_configs: Dict[str, float],
) -> List[ValidationError]:
    """Verify that subject marks are numeric and within [0.0, MaxMark]."""
    errors: List[ValidationError] = []

    for subject, max_mark in subject_configs.items():
        if max_mark <= 0:
            errors.append(ValidationError(
                message=f"Invalid maximum mark for subject '{subject}': {max_mark}. Must be > 0.",
                column=subject,
            ))
            continue

        raw_series = df[subject]
        for idx, val in enumerate(raw_series):
            row_num = idx + 2
            val_str = str(val).strip()
            # Handle common absence markers gracefully as warnings or errors
            if val_str.upper() in ("ABS", "ABSENT", "A"):
                # Absent marks can be treated as 0 with an academic warning
                continue

            try:
                score = float(val_str)
                if np.isnan(score):
                    errors.append(ValidationError(
                        message=f"Missing score in subject '{subject}'.",
                        row=row_num,
                        column=subject,
                    ))
                elif score < 0.0 or score > max_mark:
                    errors.append(ValidationError(
                        message=(
                            f"Score {score} out of valid range [0.0, {max_mark}] "
                            f"for subject '{subject}'."
                        ),
                        row=row_num,
                        column=subject,
                    ))
            except (ValueError, TypeError):
                errors.append(ValidationError(
                    message=f"Invalid non-numeric score: '{val}' in subject '{subject}'.",
                    row=row_num,
                    column=subject,
                ))

    return errors


def validate_dataset(
    df: pd.DataFrame,
    student_id_col: str,
    name_col: str,
    attendance_col: str,
    subject_configs: Dict[str, float],
    department_col: Optional[str] = None,
) -> ValidationResult:
    """Execute the full validation battery against the dataset.

    Returns:
        ValidationResult containing pass/fail status and all structured findings.
    """
    all_errors: List[ValidationError] = []
    all_warnings: List[ValidationError] = []

    # 1. Structural column check
    col_findings = validate_required_columns(
        df=df,
        student_id_col=student_id_col,
        name_col=name_col,
        attendance_col=attendance_col,
        subject_cols=list(subject_configs.keys()),
        department_col=department_col,
    )
    for f in col_findings:
        if f.severity == "WARNING":
            all_warnings.append(f)
        else:
            all_errors.append(f)

    # If critical structural columns are missing, halt further deep row validation
    if any(f.column in (student_id_col, name_col, attendance_col) for f in all_errors):
        return ValidationResult(is_valid=False, errors=all_errors, warnings=all_warnings)

    # 2. Student ID uniqueness and format
    id_errors = validate_student_ids(df, student_id_col)
    all_errors.extend(id_errors)

    # 3. Attendance checks
    att_errors = validate_attendance(df, attendance_col)
    all_errors.extend(att_errors)

    # 4. Subject score range checks
    score_errors = validate_subject_scores(df, subject_configs)
    all_errors.extend(score_errors)

    is_valid = len(all_errors) == 0
    return ValidationResult(
        is_valid=is_valid,
        errors=all_errors,
        warnings=all_warnings,
    )
