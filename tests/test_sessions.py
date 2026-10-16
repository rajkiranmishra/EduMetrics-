"""Regression and unit tests for session state integrity and isolation.

Covers:
1. Unit tests for centralized session state helper functions.
2. End-to-end Streamlit AppTest regressions for:
   - First-time dataset upload.
   - Uploading Dataset A and running analysis.
   - Replacing Dataset A with Dataset B.
   - Uploading different content using the same filename.
   - Switching from an uploaded file to a built-in sample dataset.
   - Invalid upload after a successful analysis.
   - Changing grading thresholds after analysis.
   - Changing subject maximum marks.
   - Changing selected subject columns.
   - Normal Streamlit reruns without changing the dataset.
   - Complete session reset.
   - Independent sessions with different datasets.
3. Multi-threaded session concurrency isolation.
"""

import concurrent.futures
from unittest.mock import patch, MagicMock
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from core.grading import GradingPolicy, GradeBoundary, evaluate_students
from core.analytics import compute_class_summary
from core.session_state import (
    compute_dataset_fingerprint,
    init_session_state,
    clear_analysis_results,
    replace_active_dataset,
    handle_failed_upload,
    clear_removed_upload,
    reset_complete_workflow,
    create_analysis_config,
    is_analysis_stale,
)


# =============================================================================
# 1. CORE SESSION STATE HELPER UNIT TESTS
# =============================================================================

def test_compute_dataset_fingerprint():
    """Verify dataset fingerprints are deterministic, non-empty, and sensitive to content changes."""
    content1 = b"student_id,name,attendance,score\n1,Alice,90,85\n"
    content2 = b"student_id,name,attendance,score\n1,Alice,90,86\n"
    
    fp1 = compute_dataset_fingerprint(content1)
    fp1_again = compute_dataset_fingerprint(content1)
    fp2 = compute_dataset_fingerprint(content2)
    
    assert fp1 == fp1_again
    assert fp1 != fp2
    assert len(fp1) == 64
    assert compute_dataset_fingerprint(b"") == ""


def test_init_session_state_defaults():
    """Verify session state initializes all expected keys with safe defaults."""
    state = {}
    init_session_state(state)
    assert state["raw_df"] is None
    assert state["dataset_name"] is None
    assert state["dataset_fingerprint"] is None
    assert state["dataset_source"] is None
    assert state["evaluated_df"] is None
    assert state["class_summary"] is None
    assert state["subject_metrics"] is None
    assert state["attention_students"] is None
    assert isinstance(state["policy"], GradingPolicy)
    assert state["subject_configs"] == {}
    assert state["analysis_config"] is None
    assert state["upload_error"] is None
    assert state["uploader_key"] == 0
    assert state["config_stale"] is False


def test_clear_analysis_results():
    """Verify clear_analysis_results clears only calculated outputs without clearing raw data."""
    state = {
        "raw_df": pd.DataFrame({"id": [1]}),
        "dataset_name": "data.csv",
        "evaluated_df": pd.DataFrame({"id": [1], "status": ["PASS"]}),
        "class_summary": "summary_obj",
        "subject_metrics": ["metric"],
        "attention_students": ["att"],
        "analysis_config": {"config": 1},
    }
    clear_analysis_results(state)
    assert state["raw_df"] is not None
    assert state["dataset_name"] == "data.csv"
    assert state["evaluated_df"] is None
    assert state["class_summary"] is None
    assert state["subject_metrics"] is None
    assert state["attention_students"] is None
    assert state["analysis_config"] is None


def test_replace_active_dataset():
    """Verify replacing active dataset clears prior analysis and sets new dataset metadata."""
    state = {
        "raw_df": pd.DataFrame({"id": [1]}),
        "dataset_name": "old.csv",
        "dataset_fingerprint": "fp_old",
        "evaluated_df": pd.DataFrame({"id": [1]}),
        "class_summary": "summary",
        "subject_metrics": ["m"],
        "attention_students": ["a"],
        "analysis_config": {"c": 1},
        "upload_error": "old error",
        "config_stale": True,
        "subject_configs": {"Math": 100.0},
    }
    new_df = pd.DataFrame({"id": [2, 3]})
    replace_active_dataset(new_df, "new.csv", "fp_new", source="upload", state=state)
    assert state["raw_df"].equals(new_df)
    assert state["dataset_name"] == "new.csv"
    assert state["dataset_fingerprint"] == "fp_new"
    assert state["dataset_source"] == "upload"
    assert state["evaluated_df"] is None
    assert state["class_summary"] is None
    assert state["subject_metrics"] is None
    assert state["attention_students"] is None
    assert state["analysis_config"] is None
    assert state["upload_error"] is None
    assert state["config_stale"] is False
    assert state["subject_configs"] == {}


def test_handle_failed_upload():
    """Verify failed upload resets active dataset and analysis to prevent inconsistent state."""
    state = {
        "raw_df": pd.DataFrame({"id": [1]}),
        "dataset_name": "valid.csv",
        "dataset_fingerprint": "fp_valid",
        "evaluated_df": pd.DataFrame({"id": [1]}),
        "class_summary": "summary",
        "subject_metrics": ["m"],
        "attention_students": ["a"],
        "analysis_config": {"c": 1},
        "upload_error": None,
        "config_stale": False,
    }
    handle_failed_upload("File rejected: binary detected", state=state)
    assert state["raw_df"] is None
    assert state["dataset_name"] is None
    assert state["dataset_fingerprint"] is None
    assert state["dataset_source"] is None
    assert state["evaluated_df"] is None
    assert state["class_summary"] is None
    assert state["subject_metrics"] is None
    assert state["attention_students"] is None
    assert state["analysis_config"] is None
    assert state["upload_error"] == "File rejected: binary detected"
    assert state["config_stale"] is False


def test_reset_complete_workflow():
    """Verify reset_complete_workflow cleans state and increments the uploader key version."""
    state = {
        "raw_df": pd.DataFrame({"id": [1]}),
        "dataset_name": "file.csv",
        "uploader_key": 2,
        "evaluated_df": pd.DataFrame({"id": [1]}),
    }
    reset_complete_workflow(state)
    assert state["raw_df"] is None
    assert state["dataset_name"] is None
    assert state["evaluated_df"] is None
    assert state["uploader_key"] == 3


def test_create_analysis_config_and_staleness():
    """Verify config tracking and precise change detection."""
    cfg1 = create_analysis_config(
        dataset_fingerprint="fp123",
        student_id_col="student_id",
        name_col="name",
        attendance_col="att",
        department_col="dept",
        selected_subjects=["Math", "Science"],
        subject_configs={"Math": 100.0, "Science": 100.0},
        subject_pass_percentage=40.0,
        aggregate_pass_percentage=40.0,
        attendance_warning_threshold=75.0,
    )
    # Identical config
    cfg1_same = create_analysis_config(
        dataset_fingerprint="fp123",
        student_id_col="student_id",
        name_col="name",
        attendance_col="att",
        department_col="dept",
        selected_subjects=["Science", "Math"],  # Different order but sorted inside
        subject_configs={"Science": 100.0, "Math": 100.0},
        subject_pass_percentage=40.0,
        aggregate_pass_percentage=40.0,
        attendance_warning_threshold=75.0,
    )
    assert cfg1 == cfg1_same
    assert not is_analysis_stale(cfg1_same, cfg1)

    # Change subject threshold
    cfg_thresh = dict(cfg1)
    cfg_thresh["subject_pass_percentage"] = 50.0
    assert is_analysis_stale(cfg_thresh, cfg1)

    # Change max marks
    cfg_max = dict(cfg1)
    cfg_max["subject_configs"] = {"Math": 80.0, "Science": 100.0}
    assert is_analysis_stale(cfg_max, cfg1)

    # Change subjects
    cfg_subjs = dict(cfg1)
    cfg_subjs["selected_subjects"] = ["Math"]
    assert is_analysis_stale(cfg_subjs, cfg1)

    # Different dataset
    cfg_diff_df = dict(cfg1)
    cfg_diff_df["dataset_fingerprint"] = "fp_other"
    assert is_analysis_stale(cfg_diff_df, cfg1)


# =============================================================================
# 2. STREAMLIT APPTEST REGRESSION TESTS
# =============================================================================

def _make_mock_file(filename: str, content: bytes):
    """Create a mock UploadedFile for testing file uploads."""
    mock = MagicMock()
    mock.name = filename
    mock.getvalue.return_value = content
    return mock


def test_first_time_dataset_upload():
    """Verify first-time upload sets raw_df without generating unprompted analysis."""
    content = b"student_id,student_name,attendance,Math\nS01,Alice,95.0,90.0\nS02,Bob,85.0,75.0\n"
    mock_file = _make_mock_file("first_upload.csv", content)

    with patch("streamlit.file_uploader", return_value=mock_file):
        at = AppTest.from_file("app.py")
        at.run()
        assert not at.exception
        assert at.session_state["raw_df"] is not None
        assert len(at.session_state["raw_df"]) == 2
        assert at.session_state["dataset_name"] == "first_upload.csv"
        assert at.session_state["evaluated_df"] is None
        assert at.session_state["class_summary"] is None


def test_upload_dataset_a_and_run_analysis():
    """Verify uploading Dataset A and executing analysis populates evaluated outputs cleanly."""
    content = b"student_id,student_name,attendance,Math\nS01,Alice,95.0,90.0\nS02,Bob,85.0,75.0\n"
    mock_file = _make_mock_file("dataset_a.csv", content)

    with patch("streamlit.file_uploader", return_value=mock_file):
        at = AppTest.from_file("app.py")
        at.run()
        run_btn = [b for b in at.button if "Run Academic Analysis" in b.label][0]
        run_btn.click().run()

        assert not at.exception
        assert at.session_state["evaluated_df"] is not None
        assert len(at.session_state["evaluated_df"]) == 2
        assert at.session_state["class_summary"] is not None
        assert at.session_state["class_summary"].total_students == 2
        assert at.session_state["analysis_config"] is not None


def test_replace_dataset_a_with_dataset_b():
    """Verify replacing Dataset A with Dataset B clears Dataset A results immediately."""
    content_a = b"student_id,student_name,attendance,Math\nS01,Alice,95.0,90.0\nS02,Bob,85.0,75.0\n"
    file_a = _make_mock_file("dataset_a.csv", content_a)

    with patch("streamlit.file_uploader", return_value=file_a):
        at = AppTest.from_file("app.py")
        at.run()
        run_btn = [b for b in at.button if "Run Academic Analysis" in b.label][0]
        run_btn.click().run()
        assert at.session_state["evaluated_df"] is not None
        assert at.session_state["dataset_name"] == "dataset_a.csv"

    # Replace with Dataset B
    content_b = b"student_id,student_name,attendance,Math\nC01,Charlie,90.0,80.0\nC02,Diana,92.0,85.0\nC03,Eve,94.0,90.0\n"
    file_b = _make_mock_file("dataset_b.csv", content_b)

    with patch("streamlit.file_uploader", return_value=file_b):
        at.run()
        assert not at.exception
        # Dataset A's analysis MUST be discarded
        assert at.session_state["evaluated_df"] is None
        assert at.session_state["class_summary"] is None
        assert at.session_state["subject_metrics"] is None
        assert at.session_state["dataset_name"] == "dataset_b.csv"
        assert len(at.session_state["raw_df"]) == 3


def test_upload_different_content_same_filename():
    """Verify uploading different content under the exact same filename invalidates previous analysis."""
    content_v1 = b"student_id,student_name,attendance,Math\nS01,Alice,95.0,90.0\n"
    file_v1 = _make_mock_file("grades.csv", content_v1)

    with patch("streamlit.file_uploader", return_value=file_v1):
        at = AppTest.from_file("app.py")
        at.run()
        run_btn = [b for b in at.button if "Run Academic Analysis" in b.label][0]
        run_btn.click().run()
        assert at.session_state["evaluated_df"] is not None
        assert len(at.session_state["evaluated_df"]) == 1

    # Upload different content under the same filename "grades.csv"
    content_v2 = b"student_id,student_name,attendance,Math\nS01,Alice,95.0,90.0\nS02,Bob,70.0,60.0\n"
    file_v2 = _make_mock_file("grades.csv", content_v2)

    with patch("streamlit.file_uploader", return_value=file_v2):
        at.run()
        assert not at.exception
        # Old analysis must be cleared even though filename matches
        assert at.session_state["evaluated_df"] is None
        assert len(at.session_state["raw_df"]) == 2


def test_switch_from_upload_to_builtin_sample_dataset():
    """Verify switching from custom upload to built-in sample clears prior custom analysis."""
    custom_content = b"student_id,student_name,attendance,Math\nCUST_01,Custom_Student,90.0,85.0\n"
    custom_file = _make_mock_file("custom.csv", custom_content)

    def mock_uploader(*args, **kwargs):
        # Key starts at csv_uploader_0; when sample dataset is clicked, uploader_key is incremented to 1
        if kwargs.get("key") == "csv_uploader_0":
            return custom_file
        return None

    with patch("streamlit.file_uploader", side_effect=mock_uploader):
        at = AppTest.from_file("app.py")
        at.run()
        run_btn = [b for b in at.button if "Run Academic Analysis" in b.label][0]
        run_btn.click().run()
        assert at.session_state["dataset_name"] == "custom.csv"
        assert at.session_state["evaluated_df"] is not None

        # Now click the button to load the built-in School sample dataset
        school_btn = [b for b in at.button if "Load Sample School Dataset" in b.label][0]
        school_btn.click().run()

        assert not at.exception
        assert at.session_state["dataset_name"] == "sample_school.csv"
        # Prior custom analysis must be invalidated
        assert at.session_state["evaluated_df"] is None
        assert at.session_state["class_summary"] is None
        assert len(at.session_state["raw_df"]) == 20


def test_invalid_upload_after_successful_analysis():
    """Verify submitting an invalid upload after analysis clears stale results and raw data safely."""
    valid_content = b"student_id,student_name,attendance,Math\nS01,Alice,95.0,90.0\n"
    valid_file = _make_mock_file("valid.csv", valid_content)

    with patch("streamlit.file_uploader", return_value=valid_file):
        at = AppTest.from_file("app.py")
        at.run()
        run_btn = [b for b in at.button if "Run Academic Analysis" in b.label][0]
        run_btn.click().run()
        assert at.session_state["evaluated_df"] is not None

    # Now upload an invalid CSV with duplicate header names
    invalid_content = b"student_id,student_name,student_name\n1,Alice,Alice\n"
    invalid_file = _make_mock_file("invalid.csv", invalid_content)

    with patch("streamlit.file_uploader", return_value=invalid_file):
        at.run()
        assert not at.exception
        # Stale results must NOT be visible under the rejected file
        assert at.session_state["evaluated_df"] is None
        assert at.session_state["raw_df"] is None
        assert at.session_state["dataset_name"] is None
        assert at.session_state["upload_error"] is not None
        assert "duplicate column headers" in at.session_state["upload_error"].lower()


def test_changing_grading_thresholds_invalidates_analysis():
    """Verify editing passing thresholds after analysis invalidates results and prompts re-analysis."""
    at = AppTest.from_file("app.py")
    at.run()
    # Load sample school dataset
    at.button[0].click().run()
    run_btn = [b for b in at.button if "Run Academic Analysis" in b.label][0]
    run_btn.click().run()
    assert at.session_state["evaluated_df"] is not None

    # Change subject passing threshold from 40 to 50
    thresh_input = [ni for ni in at.number_input if "Subject Passing Threshold" in ni.label][0]
    thresh_input.set_value(50.0).run()

    assert not at.exception
    assert at.session_state["evaluated_df"] is None
    assert at.session_state["config_stale"] is True
    # Warning message displayed
    assert len(at.warning) > 0


def test_changing_subject_maximum_marks_invalidates_analysis():
    """Verify modifying a subject's maximum marks invalidates previously evaluated results."""
    at = AppTest.from_file("app.py")
    at.run()
    at.button[0].click().run()
    run_btn = [b for b in at.button if "Run Academic Analysis" in b.label][0]
    run_btn.click().run()
    assert at.session_state["evaluated_df"] is not None

    # Change Mathematics Max from 100 to 75
    math_max_input = [ni for ni in at.number_input if "Mathematics Max" in ni.label][0]
    math_max_input.set_value(75.0).run()

    assert not at.exception
    assert at.session_state["evaluated_df"] is None
    assert at.session_state["config_stale"] is True


def test_changing_selected_subject_columns_invalidates_analysis():
    """Verify deselecting a subject column invalidates prior analysis results."""
    at = AppTest.from_file("app.py")
    at.run()
    at.button[0].click().run()
    run_btn = [b for b in at.button if "Run Academic Analysis" in b.label][0]
    run_btn.click().run()
    assert at.session_state["evaluated_df"] is not None

    # Remove one subject from multiselect
    subj_multiselect = at.multiselect[0]
    current_subjs = subj_multiselect.value
    subj_multiselect.set_value(current_subjs[:-1]).run()

    assert not at.exception
    assert at.session_state["evaluated_df"] is None
    assert at.session_state["config_stale"] is True


def test_normal_rerun_preserves_analysis():
    """Verify regular Streamlit reruns without configuration changes do NOT reset analysis."""
    at = AppTest.from_file("app.py")
    at.run()
    at.button[0].click().run()
    run_btn = [b for b in at.button if "Run Academic Analysis" in b.label][0]
    run_btn.click().run()
    assert at.session_state["evaluated_df"] is not None
    pass_pct = at.session_state["class_summary"].overall_pass_percentage

    # Trigger multiple ordinary reruns
    at.run()
    assert at.session_state["evaluated_df"] is not None
    assert at.session_state["class_summary"].overall_pass_percentage == pass_pct

    at.run()
    assert at.session_state["evaluated_df"] is not None
    assert at.session_state["class_summary"].overall_pass_percentage == pass_pct


def test_complete_session_reset():
    """Verify 'Start New Analysis / Reset' button clears all analysis and bumps uploader key."""
    at = AppTest.from_file("app.py")
    at.run()
    at.button[0].click().run()
    run_btn = [b for b in at.button if "Run Academic Analysis" in b.label][0]
    run_btn.click().run()
    assert at.session_state["evaluated_df"] is not None

    # Click Reset in sidebar
    prev_key = at.session_state["uploader_key"]
    reset_btn = [b for b in at.sidebar.button if "Reset" in b.label][0]
    reset_btn.click().run()

    assert not at.exception
    assert at.session_state["evaluated_df"] is None
    assert at.session_state["raw_df"] is None
    assert at.session_state["dataset_name"] is None
    assert at.session_state["uploader_key"] == prev_key + 1


def test_independent_sessions_with_different_datasets():
    """Verify distinct AppTest sessions operate with total isolation and zero data crossover."""
    at_school = AppTest.from_file("app.py")
    at_college = AppTest.from_file("app.py")

    at_school.run()
    at_college.run()

    # Session 1: School
    at_school.button[0].click().run()
    run_school = [b for b in at_school.button if "Run Academic Analysis" in b.label][0]
    run_school.click().run()

    # Session 2: College
    at_college.button[1].click().run()
    run_college = [b for b in at_college.button if "Run Academic Analysis" in b.label][0]
    run_college.click().run()

    # Verify Session 1
    assert at_school.session_state["dataset_name"] == "sample_school.csv"
    assert len(at_school.session_state["evaluated_df"]) == 20
    assert at_school.session_state["evaluated_df"].iloc[0]["student_id"].startswith("SCH-")

    # Verify Session 2
    assert at_college.session_state["dataset_name"] == "sample_college.csv"
    assert len(at_college.session_state["evaluated_df"]) == 25
    assert at_college.session_state["evaluated_df"].iloc[0]["student_id"] == "001"


# =============================================================================
# 3. MULTI-THREAD CONCURRENCY ISOLATION
# =============================================================================

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
        futures = [executor.submit(simulate_user_session, 1 if i % 2 == 0 else 2) for i in range(10)]
        results = [f.result() for f in futures]

    for res in results:
        if res["dataset_id"] == 1:
            assert res["pass_rate"] == 100.0
            assert res["avg_pct"] == 94.0
            assert all(sid.startswith("U1_") for sid in res["student_ids"])
        else:
            assert res["pass_rate"] == 60.0
            assert res["avg_pct"] == 41.6
            assert all(sid.startswith("U2_") for sid in res["student_ids"])
