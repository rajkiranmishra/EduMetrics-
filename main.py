#!/usr/bin/env python3
"""EduMetrics — Standalone Academic Performance Analytics CLI.

Executes core academic performance analytics independently of the web dashboard.
Fully satisfies EWB Courses Assignment requirements using pure Python, NumPy, and Pandas.
"""

import sys
import os
import argparse
from typing import Dict, List, Optional
import pandas as pd

from core.loader import load_csv_from_path, IngestionError
from core.validation import validate_dataset
from core.grading import (
    GradingPolicy,
    GradeBoundary,
    InstitutionMetadata,
    GRADING_PRESETS,
    parse_grade_boundaries_string,
    evaluate_students,
    PolicyConfigurationError,
)
from core.analytics import (
    compute_class_summary,
    compute_subject_analytics,
    compute_department_summary,
    identify_academic_attention_cases,
    get_top_performers,
)
from core.reports import generate_text_summary, generate_sanitized_csv


def infer_subject_configs(
    columns: List[str],
    excluded: List[str],
    dataset_name: str,
) -> Dict[str, float]:
    """Infer subject columns and assign default maximum marks.

    For datasets like sample_college.csv, labs and projects default to 50 marks,
    while theory subjects default to 100 marks.
    """
    subjects: Dict[str, float] = {}
    for col in columns:
        if col.lower() not in [e.lower() for e in excluded if e]:
            # College lab / project heuristic (or 100 by default)
            col_lower = col.lower()
            if "lab" in col_lower or "project" in col_lower or "practical" in col_lower:
                subjects[col] = 50.0
            else:
                subjects[col] = 100.0
    return subjects


def format_table(df: pd.DataFrame, max_cols: int = 10) -> str:
    """Format a DataFrame into a clean text table without external dependencies."""
    if df.empty:
        return "  (No records)"
    display_df = df.iloc[:, :max_cols].copy()
    return display_df.to_string(index=False)


def run_cli(args: argparse.Namespace) -> int:
    """Execute the end-to-end analytics workflow."""
    print("=" * 78)
    print("             EDUMETRICS — ACADEMIC PERFORMANCE ANALYTICS CLI")
    print("=" * 78)

    file_path = args.file
    if not os.path.exists(file_path):
        # Also check relative to script directory as fallback
        base_fallback = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)
        if os.path.exists(base_fallback):
            file_path = base_fallback
        else:
            print(f"\n[ERROR] Specified file not found: '{file_path}'")
            return 1

    print(f"[*] Ingesting academic dataset: {file_path}")

    # 1. Load CSV
    try:
        df_raw, raw_headers = load_csv_from_path(file_path)
        print(f"[+] Successfully loaded {len(df_raw)} records across {len(raw_headers)} columns.")
    except IngestionError as err:
        print(f"\n[SECURITY/INGESTION ERROR] {err}")
        return 1

    # 2. Determine subject columns
    excluded = [args.id_col, args.name_col, args.attendance_col]
    if args.dept_col:
        excluded.append(args.dept_col)

    subject_configs = infer_subject_configs(raw_headers, excluded, os.path.basename(file_path))
    if not subject_configs:
        print("\n[ERROR] No subject mark columns could be identified in the dataset.")
        return 1

    print(f"[+] Identified {len(subject_configs)} subjects: "
          f"{', '.join([f'{s} (Max: {m:.0f})' for s, m in subject_configs.items()])}")

    # 3. Validate dataset
    print("[*] Validating dataset records against academic integrity constraints...")
    val_result = validate_dataset(
        df=df_raw,
        student_id_col=args.id_col,
        name_col=args.name_col,
        attendance_col=args.attendance_col,
        subject_configs=subject_configs,
        department_col=args.dept_col if args.dept_col in df_raw.columns else None,
    )

    if not val_result.is_valid:
        print(f"\n[VALIDATION FAILED] Found {val_result.error_count} error(s):")
        for err in val_result.errors[:10]:
            print(f"  - {err}")
        if val_result.error_count > 10:
            print(f"  ... and {val_result.error_count - 10} additional errors.")
        return 1

    print(f"[+] Validation Passed cleanly with 0 errors and {val_result.warning_count} warning(s).")

    # 4. Grading policy configuration
    boundaries = None
    if args.grade_boundaries:
        try:
            boundaries = parse_grade_boundaries_string(args.grade_boundaries)
        except Exception as e:
            print(f"\n[POLICY CONFIGURATION ERROR] Invalid grade boundaries: {e}")
            return 1
    elif args.preset:
        preset_key = args.preset.lower()
        if "school" in preset_key:
            boundaries = GRADING_PRESETS["Example School"]
        elif "college" in preset_key:
            boundaries = GRADING_PRESETS["Example College"]
        else:
            boundaries = GRADING_PRESETS["Default EduMetrics"]

    overrides = {}
    if args.subject_pass_overrides:
        try:
            for pair in args.subject_pass_overrides.split(","):
                if not pair.strip():
                    continue
                subj, val = pair.split(":")
                overrides[subj.strip()] = float(val.strip())
        except Exception as e:
            print(f"\n[POLICY CONFIGURATION ERROR] Invalid subject pass overrides: {e}")
            return 1

    try:
        policy = GradingPolicy(
            subject_pass_percentage=args.subject_pass,
            aggregate_pass_percentage=args.aggregate_pass,
            attendance_warning_threshold=args.attendance_warning,
            grade_boundaries=boundaries if boundaries else GradingPolicy().grade_boundaries,
            subject_pass_overrides=overrides,
            enable_attendance_warning=not args.disable_attendance_warning,
        )
        policy.validate()
    except (PolicyConfigurationError, ValueError) as err:
        print(f"\n[POLICY CONFIGURATION ERROR] {err}")
        return 1

    inst_meta = InstitutionMetadata(
        institution_name=args.institution or "",
        academic_level=args.level or "",
        program_name=args.program or "",
        term=args.term or "",
    )

    # 5. Evaluate student performance
    print("[*] Computing normalized scores, grades, and pass/fail statuses...")
    try:
        df_evaluated = evaluate_students(
            df=df_raw,
            student_id_col=args.id_col,
            name_col=args.name_col,
            attendance_col=args.attendance_col,
            subject_configs=subject_configs,
            policy=policy,
            department_col=args.dept_col if args.dept_col in df_raw.columns else None,
        )
    except (PolicyConfigurationError, ValueError) as err:
        print(f"\n[EVALUATION ERROR] {err}")
        return 1

    # 6. Analytics
    pass_thresh_arg = policy.subject_pass_overrides if policy.subject_pass_overrides else policy.subject_pass_percentage
    class_summary = compute_class_summary(df_evaluated)
    subject_metrics = compute_subject_analytics(df_evaluated, subject_configs, pass_thresh_arg)
    dept_summary = compute_department_summary(df_evaluated)
    attention_students = identify_academic_attention_cases(
        df_evaluated,
        subject_configs,
        pass_thresh_arg,
        aggregate_pass_threshold=policy.aggregate_pass_percentage,
        attendance_warning_threshold=policy.attendance_warning_threshold,
    )
    top_performers = get_top_performers(df_evaluated, n=args.top)

    # 7. Print Report
    report_text = generate_text_summary(
        class_summary=class_summary,
        subject_metrics=subject_metrics,
        attention_students=attention_students,
        policy=policy,
        dataset_name=os.path.basename(file_path),
        institution_metadata=inst_meta,
    )
    print("\n" + report_text)

    # 8. Print Top Performers Leaderboard
    print("\n" + "=" * 78)
    print(f"  TOP {args.top} PERFORMERS LEADERBOARD (DETERMINISTIC RANKING)")
    print("=" * 78)
    leaderboard_cols = ["rank", "student_id", "student_name", "department", "percentage", "grade", "attendance"]
    avail_cols = [c for c in leaderboard_cols if c in top_performers.columns]
    print(format_table(top_performers[avail_cols]))

    # 9. Print Department Summary if available
    if not dept_summary.empty:
        print("\n" + "=" * 78)
        print("  DEPARTMENT-WISE COMPARISON")
        print("=" * 78)
        print(format_table(dept_summary))

    # 10. Optional CSV Export
    if args.export:
        print(f"\n[*] Sanitizing and exporting evaluated report to: {args.export}")
        sanitized_bytes = generate_sanitized_csv(df_evaluated)
        try:
            with open(args.export, "wb") as f_out:
                f_out.write(sanitized_bytes)
            print(f"[+] Successfully exported {len(df_evaluated)} sanitized student records.")
        except OSError as e:
            print(f"[ERROR] Failed to write export file: {e}")
            return 1

    print("\n[+] Analysis complete.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="EduMetrics: Standalone Academic Performance Analytics Engine",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--file", "-f",
        default="data/sample_school.csv",
        help="Path to the academic marks CSV dataset",
    )
    parser.add_argument(
        "--id-col",
        default="student_id",
        help="Column header for Student Identifier",
    )
    parser.add_argument(
        "--name-col",
        default="student_name",
        help="Column header for Student Name",
    )
    parser.add_argument(
        "--attendance-col",
        default="attendance",
        help="Column header for Attendance Percentage",
    )
    parser.add_argument(
        "--dept-col",
        default="department",
        help="Column header for Department / Section (optional)",
    )
    parser.add_argument(
        "--subject-pass",
        type=float,
        default=40.0,
        help="Minimum percentage required to pass each individual subject",
    )
    parser.add_argument(
        "--aggregate-pass",
        type=float,
        default=40.0,
        help="Minimum overall aggregate percentage required to pass",
    )
    parser.add_argument(
        "--attendance-warning",
        type=float,
        default=75.0,
        help="Attendance percentage threshold below which warnings are triggered",
    )
    parser.add_argument(
        "--disable-attendance-warning",
        action="store_true",
        help="Disable attendance warning indicator completely",
    )
    parser.add_argument(
        "--preset",
        choices=["Default", "School", "College", "Default EduMetrics", "Example School", "Example College"],
        default=None,
        help="Predefined sample grading preset to apply",
    )
    parser.add_argument(
        "--grade-boundaries",
        default=None,
        help="Custom grade boundaries, e.g. 'A+:90,A:80,B:70,C:60,D:40,F:0'",
    )
    parser.add_argument(
        "--subject-pass-overrides",
        default=None,
        help="Per-subject pass percentages, e.g. 'Physics:45,Chemistry:50'",
    )
    parser.add_argument(
        "--institution",
        default="",
        help="Institution name (optional)",
    )
    parser.add_argument(
        "--level",
        default="",
        choices=["", "School", "College", "University", "Other"],
        help="Academic level (optional)",
    )
    parser.add_argument(
        "--program",
        default="",
        help="Class, course, or program name (optional)",
    )
    parser.add_argument(
        "--term",
        default="",
        help="Academic term or semester (optional)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Number of top-performing students to display",
    )
    parser.add_argument(
        "--export", "-e",
        default=None,
        help="Optional path to save evaluated and formula-defused CSV report",
    )

    args = parser.parse_args()
    sys.exit(run_cli(args))


if __name__ == "__main__":
    main()
