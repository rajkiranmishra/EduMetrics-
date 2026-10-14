"""Unit tests for concurrency and session state isolation."""

import concurrent.futures
import pandas as pd
from core.grading import GradingPolicy, GradeBoundary, evaluate_students
from core.analytics import compute_class_summary


def simulate_user_session(dataset_id: int) -> dict:
    """Simulate an independent user session performing an academic evaluation."""
    if dataset_id == 1:
        # Session 1: High-performing cohort
        df = pd.DataFrame({
            "student_id": [f"U1_S0{i}" for i in range(1, 6)],
            "student_name": [f"User1_Student_{i}" for i in range(1, 6)],
            "attendance": [95.0] * 5,
            "Math": [90.0, 92.0, 94.0, 96.0, 98.0],
        })
        policy = GradingPolicy(subject_pass_percentage=50.0, aggregate_pass_percentage=50.0)
    else:
        # Session 2: Lower-performing cohort
        df = pd.DataFrame({
            "student_id": [f"U2_S0{i}" for i in range(1, 6)],
            "student_name": [f"User2_Student_{i}" for i in range(1, 6)],
            "attendance": [65.0] * 5,
            "Math": [35.0, 38.0, 42.0, 45.0, 48.0],
        })
        policy = GradingPolicy(subject_pass_percentage=40.0, aggregate_pass_percentage=40.0)

    df_eval = evaluate_students(
        df=df,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
        policy=policy,
    )
    summary = compute_class_summary(df_eval)

    return {
        "dataset_id": dataset_id,
        "total": summary.total_students,
        "pass_rate": summary.overall_pass_percentage,
        "avg_pct": summary.average_percentage,
        "student_ids": df_eval["student_id"].tolist(),
    }


def test_concurrent_session_isolation():
    """Verify concurrent thread execution guarantees complete isolation without cross-contamination."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        # Launch interleaved simulated user sessions
        futures = [executor.submit(simulate_user_session, 1 if i % 2 == 0 else 2) for i in range(10)]
        results = [f.result() for f in futures]

    for res in results:
        if res["dataset_id"] == 1:
            assert res["pass_rate"] == 100.0
            assert res["avg_pct"] == 94.0
            assert all(sid.startswith("U1_") for sid in res["student_ids"])
        else:
            assert res["pass_rate"] == 60.0  # 3 passed, 2 failed
            assert res["avg_pct"] == 41.6
            assert all(sid.startswith("U2_") for sid in res["student_ids"])
