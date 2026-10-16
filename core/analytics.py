"""Statistical analytics and academic attention engine.

Implements:
1. Class-level summary statistics (mean, median, std dev, min, max, pass rate).
2. Grade distribution counts.
3. Subject-wise metrics (average, pass rate, min, max, difficulty ranking).
4. Departmental comparison metrics.
5. Deterministic top-performer ranking with multi-column tie breaking.
6. Transparent, rule-based academic attention indicators.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import pandas as pd
import numpy as np

from .grading import is_greater_or_close


@dataclass
class ClassSummary:
    """Class-level statistical summary."""
    total_students: int
    passed_students: int
    failed_students: int
    overall_pass_percentage: float
    average_percentage: float
    median_percentage: float
    std_percentage: float
    highest_percentage: float
    lowest_percentage: float
    top_student_name: str
    top_student_id: str
    lowest_student_name: str
    lowest_student_id: str
    average_attendance: float
    median_attendance: float
    attendance_shortage_count: int
    grade_distribution: Dict[str, int]


@dataclass
class SubjectMetric:
    """Individual subject performance analytics."""
    subject_name: str
    max_marks: float
    average_score: float
    median_score: float
    std_score: float
    highest_score: float
    lowest_score: float
    pass_count: int
    fail_count: int
    pass_percentage: float
    average_percentage: float
    difficulty_rank: int = 1


@dataclass
class AcademicAttentionStudent:
    """Student identified by transparent academic attention heuristics."""
    student_id: str
    student_name: str
    department: str
    percentage: float
    attendance: float
    category: str
    rationale: str
    action_item: str


def compute_class_summary(df_evaluated: pd.DataFrame) -> ClassSummary:
    """Compute aggregate class statistics using NumPy and Pandas with full numerical precision."""
    n = len(df_evaluated)
    if n == 0:
        return ClassSummary(
            total_students=0,
            passed_students=0,
            failed_students=0,
            overall_pass_percentage=0.0,
            average_percentage=0.0,
            median_percentage=0.0,
            std_percentage=0.0,
            highest_percentage=0.0,
            lowest_percentage=0.0,
            top_student_name="N/A",
            top_student_id="N/A",
            lowest_student_name="N/A",
            lowest_student_id="N/A",
            average_attendance=0.0,
            median_attendance=0.0,
            attendance_shortage_count=0,
            grade_distribution={},
        )

    pct_col = "raw_percentage" if "raw_percentage" in df_evaluated.columns else "percentage"
    percentages = df_evaluated[pct_col].to_numpy(dtype=float)
    attendances = df_evaluated["attendance"].to_numpy(dtype=float)

    passed_count = int((df_evaluated["status"] == "PASS").sum())
    failed_count = n - passed_count
    pass_rate = round((passed_count / n) * 100.0, 2)

    # NumPy calculations
    avg_pct = round(float(np.mean(percentages)), 2)
    med_pct = round(float(np.median(percentages)), 2)
    std_pct = round(float(np.std(percentages)), 2) if n > 1 else 0.0
    high_pct = round(float(np.max(percentages)), 2)
    low_pct = round(float(np.min(percentages)), 2)

    # Identifiers for highest and lowest based on full unrounded precision
    top_row = df_evaluated.loc[df_evaluated[pct_col].idxmax()]
    low_row = df_evaluated.loc[df_evaluated[pct_col].idxmin()]

    avg_att = round(float(np.mean(attendances)), 2)
    med_att = round(float(np.median(attendances)), 2)
    shortage_count = int(df_evaluated["attendance_warning"].sum())

    # Grade distribution
    grade_counts = df_evaluated["grade"].value_counts().to_dict()

    return ClassSummary(
        total_students=n,
        passed_students=passed_count,
        failed_students=failed_count,
        overall_pass_percentage=pass_rate,
        average_percentage=avg_pct,
        median_percentage=med_pct,
        std_percentage=std_pct,
        highest_percentage=high_pct,
        lowest_percentage=low_pct,
        top_student_name=str(top_row["student_name"]),
        top_student_id=str(top_row["student_id"]),
        lowest_student_name=str(low_row["student_name"]),
        lowest_student_id=str(low_row["student_id"]),
        average_attendance=avg_att,
        median_attendance=med_att,
        attendance_shortage_count=shortage_count,
        grade_distribution=grade_counts,
    )


def compute_subject_analytics(
    df_evaluated: pd.DataFrame,
    subject_configs: Dict[str, float],
    pass_percentage_threshold: float = 40.0,
) -> List[SubjectMetric]:
    """Compute performance distributions and difficulty rankings for all subjects."""
    metrics: List[SubjectMetric] = []
    n = len(df_evaluated)

    for subj, max_m in subject_configs.items():
        if subj not in df_evaluated.columns or n == 0:
            continue

        scores = pd.to_numeric(df_evaluated[subj], errors="coerce").fillna(0.0).to_numpy(dtype=float)

        avg_s = round(float(np.mean(scores)), 2)
        med_s = round(float(np.median(scores)), 2)
        std_s = round(float(np.std(scores)), 2) if n > 1 else 0.0
        high_s = round(float(np.max(scores)), 2)
        low_s = round(float(np.min(scores)), 2)

        pass_mark = (pass_percentage_threshold / 100.0) * max_m
        pass_cnt = int(sum(is_greater_or_close(float(s), pass_mark) for s in scores))
        fail_cnt = n - pass_cnt
        pass_pct = round((pass_cnt / n) * 100.0, 2)
        avg_pct = round((avg_s / max_m) * 100.0, 2) if max_m > 0 else 0.0

        metrics.append(SubjectMetric(
            subject_name=subj,
            max_marks=max_m,
            average_score=avg_s,
            median_score=med_s,
            std_score=std_s,
            highest_score=high_s,
            lowest_score=low_s,
            pass_count=pass_cnt,
            fail_count=fail_cnt,
            pass_percentage=pass_pct,
            average_percentage=avg_pct,
        ))

    # Rank difficulty: lower pass percentage = higher difficulty (Rank 1 = hardest)
    # Tie-break with average percentage ascending
    metrics.sort(key=lambda m: (m.pass_percentage, m.average_percentage))
    for rank, m in enumerate(metrics, start=1):
        m.difficulty_rank = rank

    return metrics


def compute_department_summary(df_evaluated: pd.DataFrame) -> pd.DataFrame:
    """Group statistics by department if present."""
    if "department" not in df_evaluated.columns:
        return pd.DataFrame()

    pct_col = "raw_percentage" if "raw_percentage" in df_evaluated.columns else "percentage"
    dept_rows = []
    for dept_name, group in df_evaluated.groupby("department"):
        n = len(group)
        passed = int((group["status"] == "PASS").sum())
        pass_pct = round((passed / n) * 100.0, 2)
        avg_pct = round(float(group[pct_col].mean()), 2)
        avg_att = round(float(group["attendance"].mean()), 2)

        dept_rows.append({
            "department": str(dept_name),
            "student_count": n,
            "passed_students": passed,
            "pass_percentage": pass_pct,
            "average_percentage": avg_pct,
            "average_attendance": avg_att,
        })

    df_dept = pd.DataFrame(dept_rows)
    if not df_dept.empty:
        df_dept.sort_values(by="average_percentage", ascending=False, inplace=True)
    return df_dept


def get_top_performers(df_evaluated: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Extract top N students with deterministic tie-breaking using full unrounded precision.

    Tie-breaking order:
    1. Percentage (unrounded raw_percentage, descending)
    2. Attendance (descending)
    3. Student ID (ascending, alphabetical)
    """
    if df_evaluated.empty:
        return pd.DataFrame()

    sort_cols = (
        ["raw_percentage", "attendance", "student_id"]
        if "raw_percentage" in df_evaluated.columns
        else ["percentage", "attendance", "student_id"]
    )
    sorted_df = df_evaluated.sort_values(
        by=sort_cols,
        ascending=[False, False, True],
    ).head(n).copy()

    sorted_df.reset_index(drop=True, inplace=True)
    sorted_df.insert(0, "rank", range(1, len(sorted_df) + 1))
    return sorted_df


def identify_academic_attention_cases(
    df_evaluated: pd.DataFrame,
    subject_configs: Dict[str, float],
    pass_percentage_threshold: float = 40.0,
) -> List[AcademicAttentionStudent]:
    """Identify students requiring targeted academic support via transparent rules.

    Indicators:
    1. CONCEPTUAL_SUPPORT_NEEDED: Attendance >= 85% and Percentage < 50%.
    2. CHRONIC_ABSENTEEISM_CRITICAL: Attendance < 75% and Percentage < 50%.
    3. SUBJECT_SPECIFIC_OUTLIER: Failed in exactly 1 subject, while other subjects average >= 65%.
    4. BORDERLINE_AT_RISK: Status is PASS, but 40.0% <= Percentage < 45.0%.
    """
    flagged: List[AcademicAttentionStudent] = []

    for _, row in df_evaluated.iterrows():
        sid = str(row["student_id"])
        sname = str(row["student_name"])
        dept = str(row.get("department", "General"))
        pct = float(row["raw_percentage"]) if "raw_percentage" in row else float(row["percentage"])
        display_pct = float(row["percentage"]) if "percentage" in row else round(pct, 2)
        att = float(row["attendance"])
        status = str(row["status"])

        # Rule 1: High Attendance but Low Score
        if att >= 85.0 and pct < 50.0:
            flagged.append(AcademicAttentionStudent(
                student_id=sid,
                student_name=sname,
                department=dept,
                percentage=display_pct,
                attendance=att,
                category="Conceptual Support Needed",
                rationale="High class attendance (>=85%) but low score (<50%). Student is engaged but struggling with concept mastery.",
                action_item="Schedule 1-on-1 concept tutoring and targeted practice assignments.",
            ))
            continue

        # Rule 2: Low Attendance and Low Score
        if att < 75.0 and pct < 50.0:
            flagged.append(AcademicAttentionStudent(
                student_id=sid,
                student_name=sname,
                department=dept,
                percentage=display_pct,
                attendance=att,
                category="Critical Intervention (Attendance & Academic)",
                rationale="Chronic absenteeism (<75%) compounded by failing academic performance (<50%).",
                action_item="Initiate student counseling and parent/guardian attendance review.",
            ))
            continue

        # Rule 3: Single-Subject Stumbling Block Outlier
        failed_count = int(row.get("failed_subject_count", 0))
        if failed_count == 1:
            failed_subj_name = None
            other_percentages = []
            for subj, max_m in subject_configs.items():
                if subj not in row:
                    continue
                s_score = float(row[subj])
                s_pct = (s_score / max_m) * 100.0 if (max_m and max_m > 0) else 0.0
                if not is_greater_or_close(s_pct, pass_percentage_threshold):
                    failed_subj_name = subj
                else:
                    other_percentages.append(s_pct)

            other_avg = np.mean(other_percentages) if other_percentages else 0.0
            if other_avg >= 65.0 and failed_subj_name is not None:
                flagged.append(AcademicAttentionStudent(
                    student_id=sid,
                    student_name=sname,
                    department=dept,
                    percentage=display_pct,
                    attendance=att,
                    category="Subject-Specific Remediation",
                    rationale=f"Academically strong overall ({other_avg:.1f}% avg in other subjects) but failed exclusively in '{failed_subj_name}'.",
                    action_item=f"Provide dedicated remedial modules and problem sets for '{failed_subj_name}'.",
                ))
                continue

        # Rule 4: Borderline Passing (At-Risk)
        if status == "PASS" and is_greater_or_close(pct, 40.0) and pct < 45.0:
            flagged.append(AcademicAttentionStudent(
                student_id=sid,
                student_name=sname,
                department=dept,
                percentage=display_pct,
                attendance=att,
                category="Borderline / At-Risk",
                rationale="Passed, but within 5 percentage points of failing threshold (40.0%).",
                action_item="Monitor weekly progress to prevent regression into failure.",
            ))

    return flagged
