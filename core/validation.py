"""Academic dataset schema and value validation.

Performs deterministic, row-and-column-level validation:
1. Verifies presence of mandatory columns (including mapped subject columns).
2. Enforces unique, non-null Student Identifiers (preserving leading zeros, case-insensitive collision check).
3. Enforces non-null, non-empty Student Names (supporting international characters).
4. Enforces bounds on string field lengths to prevent layout and memory DoS.
5. Rejects unprintable ASCII control characters and bidirectional Unicode overrides.
6. Validates Attendance percentages within [0.0, 100.0] as finite numbers.
7. Validates Subject scores within [0.0, SubjectMaxMark] as finite numbers or explicit absence markers ('ABS', 'ABSENT').
8. Flags missing or unparseable numeric values with human-friendly row references.
9. Rejects non-finite numbers (NaN, Inf, -Inf, Infinity).
10. Caps maximum error collection to prevent resource exhaustion from adversarial inputs.
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, Tuple
import pandas as pd
import numpy as np

from security.upload_checks import (
    has_prohibited_characters,
    MAX_STUDENT_ID_LENGTH,
    MAX_STUDENT_NAME_LENGTH,
    MAX_DEPARTMENT_LENGTH,
    MAX_VALIDATION_ERRORS,
)

SUPPORTED_ABSENCE_MARKERS: Set[str] = {"ABS", "ABSENT"}


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


def is_finite_number(val: Any) -> Tuple[bool, Optional[float]]:
    """Determine if a value can be converted to a finite float.

    Rejects NaN, positive/negative infinity, None, and unparseable strings.
    """
    if val is None or pd.isna(val):
        return False, None
    try:
        val_str = str(val).strip()
        # Reject non-finite strings explicitly before or after float conversion
        if val_str.lower() in ("nan", "none", "null", "inf", "-inf", "+inf", "infinity", "-infinity", "+infinity"):
            return False, None
        num = float(val_str)
        if math.isfinite(num):
            return True, num
        return False, None
    except (ValueError, TypeError):
        return False, None


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
    """Verify that student IDs are non-null, non-empty, and unique with case-insensitive collision check."""
    errors: List[ValidationError] = []
    if student_id_col not in df.columns:
        return errors

    raw_series = df[student_id_col]
    seen_ids: Dict[str, int] = {}  # normalized upper -> first row number

    for idx, val in enumerate(raw_series):
        row_num = idx + 2  # 1-indexed, accounting for header row
        val_str = str(val).strip() if val is not None and not pd.isna(val) else ""

        if not val_str or val_str.lower() in ("nan", "none", "null"):
            errors.append(ValidationError(
                message="Missing or empty Student ID.",
                row=row_num,
                column=student_id_col,
            ))
            continue

        if len(val_str) > MAX_STUDENT_ID_LENGTH:
            errors.append(ValidationError(
                message=f"Student ID exceeds maximum allowed length of {MAX_STUDENT_ID_LENGTH} characters ({len(val_str)} characters detected).",
                row=row_num,
                column=student_id_col,
            ))
            continue

        if has_prohibited_characters(val_str):
            errors.append(ValidationError(
                message="Student ID contains unprintable control characters or prohibited Unicode sequences.",
                row=row_num,
                column=student_id_col,
            ))
            continue

        norm_id = val_str.upper()
        if norm_id in seen_ids:
            first_row = seen_ids[norm_id]
            errors.append(ValidationError(
                message=f"Duplicate Student ID detected: '{val_str}' (first seen at row {first_row}).",
                row=row_num,
                column=student_id_col,
            ))
        else:
            seen_ids[norm_id] = row_num

    return errors


def validate_student_names(df: pd.DataFrame, name_col: str) -> List[ValidationError]:
    """Verify that student names are non-null and non-empty.

    Accepts arbitrary legitimate international names (e.g. Unicode, accented characters,
    hyphens, apostrophes) while rejecting empty, whitespace-only, unprintable, or oversized values.
    """
    errors: List[ValidationError] = []
    if name_col not in df.columns:
        return errors

    for idx, val in enumerate(df[name_col]):
        row_num = idx + 2
        val_str = str(val).strip() if val is not None and not pd.isna(val) else ""
        if not val_str or val_str.lower() in ("nan", "none", "null"):
            errors.append(ValidationError(
                message="Missing or empty Student Name.",
                row=row_num,
                column=name_col,
            ))
            continue

        if len(val_str) > MAX_STUDENT_NAME_LENGTH:
            errors.append(ValidationError(
                message=f"Student Name exceeds maximum allowed length of {MAX_STUDENT_NAME_LENGTH} characters ({len(val_str)} characters detected).",
                row=row_num,
                column=name_col,
            ))
            continue

        if has_prohibited_characters(val_str):
            errors.append(ValidationError(
                message="Student Name contains unprintable control characters or prohibited Unicode sequences.",
                row=row_num,
                column=name_col,
            ))
            continue

    return errors


def validate_attendance(df: pd.DataFrame, attendance_col: str) -> List[ValidationError]:
    """Verify that attendance values are finite numeric percentages [0.0, 100.0]."""
    errors: List[ValidationError] = []
    if attendance_col not in df.columns:
        return errors

    raw_series = df[attendance_col]

    for idx, val in enumerate(raw_series):
        row_num = idx + 2
        if val is None or pd.isna(val):
            errors.append(ValidationError(
                message="Missing attendance value.",
                row=row_num,
                column=attendance_col,
            ))
            continue

        val_str = str(val).strip().rstrip("%")
        if not val_str or val_str.lower() in ("nan", "none", "null"):
            errors.append(ValidationError(
                message="Missing attendance value.",
                row=row_num,
                column=attendance_col,
            ))
            continue

        ok, num = is_finite_number(val_str)
        if not ok:
            errors.append(ValidationError(
                message=f"Invalid non-numeric attendance value: '{val}'.",
                row=row_num,
                column=attendance_col,
            ))
        elif num < 0.0 or num > 100.0:
            errors.append(ValidationError(
                message=f"Attendance percentage out of range [0.0, 100.0]: {num}%.",
                row=row_num,
                column=attendance_col,
            ))

    return errors


def validate_subject_scores(
    df: pd.DataFrame,
    subject_configs: Dict[str, float],
) -> List[ValidationError]:
    """Verify that subject marks are numeric finite numbers within [0.0, MaxMark] or valid absence markers ('ABS'/'ABSENT')."""
    errors: List[ValidationError] = []

    for subject, max_mark in subject_configs.items():
        if subject not in df.columns:
            errors.append(ValidationError(
                message=f"Subject column '{subject}' not found in dataset.",
                column=subject,
            ))
            continue

        ok_max, max_m_val = is_finite_number(max_mark)
        if not ok_max or max_m_val <= 0:
            errors.append(ValidationError(
                message=f"Invalid maximum mark for subject '{subject}': {max_mark}. Must be a finite number > 0.",
                column=subject,
            ))
            continue

        raw_series = df[subject]
        for idx, val in enumerate(raw_series):
            row_num = idx + 2
            if val is None or pd.isna(val):
                errors.append(ValidationError(
                    message=f"Missing score in subject '{subject}'. Empty cells are not permitted; specify a valid score or explicit absence marker ('ABS'/'ABSENT').",
                    row=row_num,
                    column=subject,
                ))
                continue

            val_str = str(val).strip()
            if not val_str or val_str.lower() in ("nan", "none", "null"):
                errors.append(ValidationError(
                    message=f"Missing score in subject '{subject}'. Empty cells are not permitted; specify a valid score or explicit absence marker ('ABS'/'ABSENT').",
                    row=row_num,
                    column=subject,
                ))
                continue

            # Supported absence markers: ABS, ABSENT
            if val_str.upper() in SUPPORTED_ABSENCE_MARKERS:
                continue

            ok_score, score = is_finite_number(val_str)
            if not ok_score:
                if val_str.lower() in ("inf", "-inf", "+inf", "infinity", "-infinity", "+infinity"):
                    errors.append(ValidationError(
                        message=f"Invalid non-finite score '{val}' in subject '{subject}'. Scores must be finite numbers.",
                        row=row_num,
                        column=subject,
                    ))
                else:
                    errors.append(ValidationError(
                        message=f"Invalid non-numeric score: '{val}' in subject '{subject}'.",
                        row=row_num,
                        column=subject,
                    ))
            elif score < 0.0 or score > max_m_val:
                errors.append(ValidationError(
                    message=(
                        f"Score {score} out of valid range [0.0, {max_m_val}] "
                        f"for subject '{subject}'."
                    ),
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

    # 0. Check for empty DataFrame
    if df.empty:
        return ValidationResult(
            is_valid=False,
            errors=[ValidationError(message="Dataset contains 0 data rows.")],
            warnings=[],
        )

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

    # If ANY structural column is missing (including subject columns), HALT immediately.
    # Do NOT proceed to deep row-level validation to prevent KeyErrors or misleading errors.
    if all_errors:
        return ValidationResult(is_valid=False, errors=all_errors, warnings=all_warnings)

    # 2. Student ID uniqueness and format
    id_errors = validate_student_ids(df, student_id_col)
    all_errors.extend(id_errors)

    # 3. Student Name non-empty check
    name_errors = validate_student_names(df, name_col)
    all_errors.extend(name_errors)

    # 4. Attendance checks
    att_errors = validate_attendance(df, attendance_col)
    all_errors.extend(att_errors)

    # 5. Subject score range checks
    score_errors = validate_subject_scores(df, subject_configs)
    all_errors.extend(score_errors)

    # 6. Optional Department checks
    if department_col and department_col in df.columns:
        for idx, val in enumerate(df[department_col]):
            row_num = idx + 2
            val_str = str(val).strip() if val is not None and not pd.isna(val) else ""
            if len(val_str) > MAX_DEPARTMENT_LENGTH:
                all_errors.append(ValidationError(
                    message=f"Department name exceeds maximum allowed length of {MAX_DEPARTMENT_LENGTH} characters.",
                    row=row_num,
                    column=department_col,
                ))
            elif has_prohibited_characters(val_str):
                all_errors.append(ValidationError(
                    message="Department name contains unprintable control characters or prohibited Unicode sequences.",
                    row=row_num,
                    column=department_col,
                ))
            elif not val_str or val_str.lower() in ("nan", "none", "null"):
                all_warnings.append(ValidationError(
                    message="Missing Department value; will default to 'General'.",
                    row=row_num,
                    column=department_col,
                    severity="WARNING",
                ))

    # Error collection capping to prevent memory/UI exhaustion under adversarial payloads
    if len(all_errors) > MAX_VALIDATION_ERRORS:
        capped_errors = all_errors[:MAX_VALIDATION_ERRORS]
        capped_errors.append(ValidationError(
            message=f"Validation error limit reached ({MAX_VALIDATION_ERRORS} errors). Halting further validation display to prevent resource exhaustion."
        ))
        all_errors = capped_errors

    is_valid = len(all_errors) == 0
    return ValidationResult(
        is_valid=is_valid,
        errors=all_errors,
        warnings=all_warnings,
    )
