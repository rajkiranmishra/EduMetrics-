"""Reporting and export generation with CSV formula injection defusion.

Implements:
1. Formula injection defusion across all exported textual cells.
2. Formatted CSV report generation with audit metadata.
3. High-readability ASCII terminal and text summary formatting.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
import io
import pandas as pd

from security.upload_checks import defuse_formula_injection
from .analytics import ClassSummary, SubjectMetric, AcademicAttentionStudent
from .grading import GradingPolicy, InstitutionMetadata


def generate_sanitized_csv(df_evaluated: pd.DataFrame) -> bytes:
    """Generate a CSV byte stream where all string cells are sanitized against formula injection."""
    # Create a clean copy to avoid mutating the original DataFrame
    df_export = df_evaluated.copy()

    # Apply defuse_formula_injection to every object/string column
    for col in df_export.select_dtypes(include=["object"]).columns:
        df_export[col] = df_export[col].apply(defuse_formula_injection)

    # Convert to CSV string with standard UTF-8 encoding
    csv_buffer = io.StringIO()
    df_export.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue().encode("utf-8")


def generate_text_summary(
    class_summary: ClassSummary,
    subject_metrics: list[SubjectMetric],
    attention_students: list[AcademicAttentionStudent],
    policy: GradingPolicy,
    dataset_name: str = "Uploaded Dataset",
    institution_metadata: Optional[InstitutionMetadata] = None,
) -> str:
    """Produce a structured, readable plain-text report for CLI and summary views."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = []
    separator = "=" * 78

    lines.append(separator)
    lines.append(f"                 EDUMETRICS ACADEMIC PERFORMANCE REPORT")
    lines.append(f"                       Generated: {now_str}")
    lines.append(separator)
    lines.append(f"Dataset: {dataset_name} | Total Records: {class_summary.total_students}")
    lines.append("")

    # Section 0: Institution Details (if provided)
    if institution_metadata and not institution_metadata.is_empty():
        lines.append("[0] INSTITUTION DETAILS")
        if institution_metadata.institution_name:
            lines.append(f"  * Institution Name : {institution_metadata.institution_name}")
        if institution_metadata.academic_level:
            lines.append(f"  * Academic Level   : {institution_metadata.academic_level}")
        if institution_metadata.program_name:
            lines.append(f"  * Program / Class  : {institution_metadata.program_name}")
        if institution_metadata.term:
            lines.append(f"  * Term / Semester  : {institution_metadata.term}")
        lines.append("-" * 78)

    # Section 1: Academic Policy Snapshot
    lines.append("[1] APPLIED ACADEMIC POLICY")
    lines.append(f"  * Subject Pass Threshold   : {policy.subject_pass_percentage:.1f}%")
    if policy.subject_pass_overrides:
        overrides_str = ", ".join([f"{k}: {v:.1f}%" for k, v in sorted(policy.subject_pass_overrides.items())])
        lines.append(f"  * Subject Pass Overrides   : {overrides_str}")
    lines.append(f"  * Aggregate Pass Threshold : {policy.aggregate_pass_percentage:.1f}%")
    if policy.enable_attendance_warning:
        lines.append(f"  * Attendance Warning Level : < {policy.attendance_warning_threshold:.1f}% (Enabled)")
    else:
        lines.append("  * Attendance Warning Level : Disabled")
    scale_str = ", ".join([f"{b.label} (>={b.min_percentage:.0f}%)" for b in policy.grade_boundaries])
    lines.append(f"  * Grade Boundaries         : {scale_str}")
    lines.append("-" * 78)

    # Section 2: Class Performance Summary
    lines.append("[2] CLASS PERFORMANCE SUMMARY")
    lines.append(f"  * Total Students        : {class_summary.total_students}")
    lines.append(f"  * Passed Students       : {class_summary.passed_students} ({class_summary.overall_pass_percentage:.1f}%)")
    lines.append(f"  * Failed Students       : {class_summary.failed_students} ({100.0 - class_summary.overall_pass_percentage:.1f}%)")
    lines.append(f"  * Class Average Score   : {class_summary.average_percentage:.2f}%")
    lines.append(f"  * Class Median Score    : {class_summary.median_percentage:.2f}%")
    lines.append(f"  * Std Deviation         : {class_summary.std_percentage:.2f}%")
    lines.append(f"  * Highest Performer     : {class_summary.top_student_name} ({class_summary.top_student_id}) - {class_summary.highest_percentage:.1f}%")
    lines.append(f"  * Lowest Performer      : {class_summary.lowest_student_name} ({class_summary.lowest_student_id}) - {class_summary.lowest_percentage:.1f}%")
    lines.append(f"  * Class Mean Attendance : {class_summary.average_attendance:.1f}%")
    lines.append(f"  * Attendance Warnings   : {class_summary.attendance_shortage_count} students")
    lines.append("-" * 78)

    # Section 3: Grade Distribution
    lines.append("[3] GRADE DISTRIBUTION")
    if class_summary.grade_distribution:
        for grade, count in sorted(class_summary.grade_distribution.items()):
            bar = "#" * count
            pct = (count / class_summary.total_students) * 100.0 if class_summary.total_students > 0 else 0.0
            lines.append(f"  Grade {grade:<3}: {count:>3} students ({pct:>5.1f}%) {bar}")
    else:
        lines.append("  No grade distribution available.")
    lines.append("-" * 78)

    # Section 4: Subject Analytics
    lines.append("[4] SUBJECT-WISE PERFORMANCE & DIFFICULTY RANKING")
    header = f"  {'Subject':<18} {'Max':<5} {'Pass Cut':<9} {'Avg Score':<10} {'Pass %':<8} {'Min':<6} {'Max':<6} {'Rank':<5}"
    lines.append(header)
    lines.append("  " + "-" * 74)
    for sm in subject_metrics:
        row_str = (
            f"  {sm.subject_name:<18} "
            f"{sm.max_marks:<5.0f} "
            f"{sm.pass_threshold:<9.1f} "
            f"{sm.average_score:<10.1f} "
            f"{sm.pass_percentage:<8.1f} "
            f"{sm.lowest_score:<6.1f} "
            f"{sm.highest_score:<6.1f} "
            f"#{sm.difficulty_rank:<4}"
        )
        lines.append(row_str)
    lines.append("  *(Rank 1 indicates the most challenging subject based on pass rate & average score)")
    lines.append("-" * 78)

    # Section 5: Academic Attention
    lines.append(f"[5] ACADEMIC ATTENTION INDICATORS ({len(attention_students)} Students Flagged)")
    if attention_students:
        for idx, s in enumerate(attention_students, start=1):
            lines.append(f"  {idx}. [{s.category.upper()}] {s.student_name} ({s.student_id}) - Dept: {s.department}")
            lines.append(f"     Score: {s.percentage:.1f}% | Attendance: {s.attendance:.1f}%")
            lines.append(f"     Rationale  : {s.rationale}")
            lines.append(f"     Action Item: {s.action_item}")
            lines.append("")
    else:
        lines.append("  No students flagged under current attention heuristics.")

    lines.append(separator)
    lines.append("                          END OF REPORT")
    lines.append(separator)

    return "\n".join(lines)
