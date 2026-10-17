"""Regression and unit tests for session state integrity and isolation.

Covers:
1. Unit tests for centralized session state helper functions.
2. End-to-end Streamlit AppTest regressions for:
   - Sidebar navigation across all 8 destinations.
   - School and College 1-click quick demo onboarding.
   - Direct upload navigation from homepage.
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
   - Preserving edits in custom grade boundary editor.
   - Literal regex-safe student search.
   - Reports and export downloads.
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
    PAGE_OVERVIEW,
    PAGE_CONFIG,
    PAGE_DASHBOARD,
    PAGE_SUBJECTS,
    PAGE_STUDENTS,
    PAGE_ATTENTION,
    PAGE_REPORTS,
    PAGE_HELP,
    ALL_NAV_PAGES,
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
    assert state["current_page"] == PAGE_OVERVIEW
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
        "current_page": PAGE_DASHBOARD,
    }
    reset_complete_workflow(state)
    assert state["raw_df"] is None
    assert state["dataset_name"] is None
    assert state["evaluated_df"] is None
    assert state["uploader_key"] == 3
    assert state["current_page"] == PAGE_OVERVIEW


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
    cfg1_same = create_analysis_config(
        dataset_fingerprint="fp123",
        student_id_col="student_id",
        name_col="name",
        attendance_col="att",
        department_col="dept",
        selected_subjects=["Science", "Math"],
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


def select_page(at: AppTest, page_name: str) -> AppTest:
    """Select a sidebar navigation destination and rerun."""
    at.sidebar.radio[0].set_value(page_name).run()
    return at


def get_button(at: AppTest, label_substr: str):
    """Find a button semantically by case-insensitive substring."""
    matches = [b for b in at.button if label_substr.lower() in b.label.lower()]
    if not matches:
        raise ValueError(
            f"Button matching '{label_substr}' not found. Available buttons: {[b.label for b in at.button]}"
        )
    return matches[0]


def get_sidebar_button(at: AppTest, label_substr: str):
    """Find a sidebar button semantically by case-insensitive substring."""
    matches = [b for b in at.sidebar.button if label_substr.lower() in b.label.lower()]
    if not matches:
        raise ValueError(
            f"Sidebar button matching '{label_substr}' not found. Available: {[b.label for b in at.sidebar.button]}"
        )
    return matches[0]


def test_sidebar_navigation_destinations():
    """Verify that user can navigate across all 8 destinations via sidebar radio."""
    at = AppTest.from_file("app.py")
    at.run()
    assert at.session_state["current_page"] == PAGE_OVERVIEW

    for page in ALL_NAV_PAGES:
        select_page(at, page)
        assert not at.exception
        assert at.session_state["current_page"] == page


def test_school_quick_demo_onboarding():
    """Verify 1-click School Demo on Homepage loads 20 students, runs analysis and lands on Dashboard."""
    at = AppTest.from_file("app.py")
    at.run()
    assert at.session_state["current_page"] == PAGE_OVERVIEW

    school_demo_btn = get_button(at, "Load & Analyze School Model")
    school_demo_btn.click().run()

    assert not at.exception
    assert at.session_state["current_page"] == PAGE_DASHBOARD
    assert at.session_state["dataset_name"] == "sample_school.csv"
    assert at.session_state["evaluated_df"] is not None
    assert len(at.session_state["evaluated_df"]) == 20
    assert at.session_state["class_summary"].overall_pass_percentage == 80.0


def test_college_quick_demo_onboarding():
    """Verify 1-click College Demo on Homepage loads 25 students, applies college preset and evaluates."""
    at = AppTest.from_file("app.py")
    at.run()
    assert at.session_state["current_page"] == PAGE_OVERVIEW

    college_demo_btn = get_button(at, "Load & Analyze College Model")
    college_demo_btn.click().run()

    assert not at.exception
    assert at.session_state["current_page"] == PAGE_DASHBOARD
    assert at.session_state["dataset_name"] == "sample_college.csv"
    assert at.session_state["evaluated_df"] is not None
    assert len(at.session_state["evaluated_df"]) == 25
    eval_grades = set(at.session_state["evaluated_df"]["grade"])
    assert any(g in ["O", "E", "A"] for g in eval_grades)


def test_direct_upload_navigation_from_homepage():
    """Verify clicking 'Go to Dataset Upload & Config' routes to Upload & Configure page."""
    at = AppTest.from_file("app.py")
    at.run()
    get_button(at, "Go to Dataset Upload & Config").click().run()
    assert not at.exception
    assert at.session_state["current_page"] == PAGE_CONFIG


def test_first_time_dataset_upload():
    """Verify first-time upload sets raw_df on Upload & Configure without unprompted analysis."""
    content = b"student_id,student_name,attendance,Math\nS01,Alice,95.0,90.0\nS02,Bob,85.0,75.0\n"
    mock_file = _make_mock_file("first_upload.csv", content)

    with patch("streamlit.file_uploader", return_value=mock_file):
        at = AppTest.from_file("app.py")
        at.session_state["current_page"] = PAGE_CONFIG
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
        at.session_state["current_page"] = PAGE_CONFIG
        at.run()
        run_btn = get_button(at, "Run Academic Analysis")
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
        at.session_state["current_page"] = PAGE_CONFIG
        at.run()
        run_btn = get_button(at, "Run Academic Analysis")
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
        at.session_state["current_page"] = PAGE_CONFIG
        at.run()
        run_btn = get_button(at, "Run Academic Analysis")
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
        if kwargs.get("key") == "csv_uploader_0":
            return custom_file
        return None

    with patch("streamlit.file_uploader", side_effect=mock_uploader):
        at = AppTest.from_file("app.py")
        at.session_state["current_page"] = PAGE_CONFIG
        at.run()
        run_btn = get_button(at, "Run Academic Analysis")
        run_btn.click().run()
        assert at.session_state["dataset_name"] == "custom.csv"
        assert at.session_state["evaluated_df"] is not None

        # Click the button to load the built-in School sample dataset
        school_btn = get_button(at, "Load Sample School Dataset")
        school_btn.click().run()

        assert not at.exception
        assert at.session_state["dataset_name"] == "sample_school.csv"
        assert at.session_state["evaluated_df"] is None
        assert at.session_state["class_summary"] is None
        assert len(at.session_state["raw_df"]) == 20


def test_invalid_upload_after_successful_analysis():
    """Verify submitting an invalid upload after analysis clears stale results and raw data safely."""
    valid_content = b"student_id,student_name,attendance,Math\nS01,Alice,95.0,90.0\n"
    valid_file = _make_mock_file("valid.csv", valid_content)

    with patch("streamlit.file_uploader", return_value=valid_file):
        at = AppTest.from_file("app.py")
        at.session_state["current_page"] = PAGE_CONFIG
        at.run()
        run_btn = get_button(at, "Run Academic Analysis")
        run_btn.click().run()
        assert at.session_state["evaluated_df"] is not None

    # Now upload an invalid CSV with duplicate header names
    invalid_content = b"student_id,student_name,student_name\n1,Alice,Alice\n"
    invalid_file = _make_mock_file("invalid.csv", invalid_content)

    with patch("streamlit.file_uploader", return_value=invalid_file):
        at.run()
        assert not at.exception
        assert at.session_state["evaluated_df"] is None
        assert at.session_state["raw_df"] is None
        assert at.session_state["dataset_name"] is None
        assert at.session_state["upload_error"] is not None
        assert "duplicate column headers" in at.session_state["upload_error"].lower()


def test_changing_grading_thresholds_invalidates_analysis():
    """Verify editing passing thresholds after analysis invalidates results and prompts re-analysis."""
    at = AppTest.from_file("app.py")
    at.session_state["current_page"] = PAGE_CONFIG
    at.run()
    get_button(at, "Load Sample School Dataset").click().run()
    get_button(at, "Run Academic Analysis").click().run()
    assert at.session_state["evaluated_df"] is not None

    thresh_input = [ni for ni in at.number_input if "Subject Passing Threshold" in ni.label][0]
    thresh_input.set_value(50.0).run()

    assert not at.exception
    assert at.session_state["evaluated_df"] is None
    assert at.session_state["config_stale"] is True
    assert len(at.warning) > 0


def test_changing_subject_maximum_marks_invalidates_analysis():
    """Verify modifying a subject's maximum marks invalidates previously evaluated results."""
    at = AppTest.from_file("app.py")
    at.session_state["current_page"] = PAGE_CONFIG
    at.run()
    get_button(at, "Load Sample School Dataset").click().run()
    get_button(at, "Run Academic Analysis").click().run()
    assert at.session_state["evaluated_df"] is not None

    math_max_input = [ni for ni in at.number_input if "Mathematics Max" in ni.label][0]
    math_max_input.set_value(75.0).run()

    assert not at.exception
    assert at.session_state["evaluated_df"] is None
    assert at.session_state["config_stale"] is True


def test_changing_selected_subject_columns_invalidates_analysis():
    """Verify deselecting a subject column invalidates prior analysis results."""
    at = AppTest.from_file("app.py")
    at.session_state["current_page"] = PAGE_CONFIG
    at.run()
    get_button(at, "Load Sample School Dataset").click().run()
    get_button(at, "Run Academic Analysis").click().run()
    assert at.session_state["evaluated_df"] is not None

    subj_multiselect = at.multiselect[0]
    current_subjs = subj_multiselect.value
    subj_multiselect.set_value(current_subjs[:-1]).run()

    assert not at.exception
    assert at.session_state["evaluated_df"] is None
    assert at.session_state["config_stale"] is True


def test_normal_rerun_preserves_analysis():
    """Verify regular Streamlit reruns without configuration changes do NOT reset analysis."""
    at = AppTest.from_file("app.py")
    at.session_state["current_page"] = PAGE_CONFIG
    at.run()
    get_button(at, "Load Sample School Dataset").click().run()
    get_button(at, "Run Academic Analysis").click().run()
    assert at.session_state["evaluated_df"] is not None
    pass_pct = at.session_state["class_summary"].overall_pass_percentage

    at.run()
    assert at.session_state["evaluated_df"] is not None
    assert at.session_state["class_summary"].overall_pass_percentage == pass_pct

    at.run()
    assert at.session_state["evaluated_df"] is not None
    assert at.session_state["class_summary"].overall_pass_percentage == pass_pct


def test_complete_session_reset():
    """Verify 'Start New Analysis / Reset' button clears all analysis and bumps uploader key."""
    at = AppTest.from_file("app.py")
    at.session_state["current_page"] = PAGE_CONFIG
    at.run()
    get_button(at, "Load Sample School Dataset").click().run()
    get_button(at, "Run Academic Analysis").click().run()
    assert at.session_state["evaluated_df"] is not None

    prev_key = at.session_state["uploader_key"]
    reset_btn = get_sidebar_button(at, "Reset")
    reset_btn.click().run()

    assert not at.exception
    assert at.session_state["evaluated_df"] is None
    assert at.session_state["raw_df"] is None
    assert at.session_state["dataset_name"] is None
    assert at.session_state["uploader_key"] == prev_key + 1
    assert at.session_state["current_page"] == PAGE_OVERVIEW


def test_independent_sessions_with_different_datasets():
    """Verify distinct AppTest sessions operate with total isolation and zero data crossover."""
    at_school = AppTest.from_file("app.py")
    at_college = AppTest.from_file("app.py")
    at_school.session_state["current_page"] = PAGE_CONFIG
    at_college.session_state["current_page"] = PAGE_CONFIG

    at_school.run()
    at_college.run()

    get_button(at_school, "Load Sample School Dataset").click().run()
    get_button(at_school, "Run Academic Analysis").click().run()

    get_button(at_college, "Load Sample College Dataset").click().run()
    get_button(at_college, "Run Academic Analysis").click().run()

    assert at_school.session_state["dataset_name"] == "sample_school.csv"
    assert len(at_school.session_state["evaluated_df"]) == 20
    assert at_school.session_state["evaluated_df"].iloc[0]["student_id"].startswith("SCH-")

    assert at_college.session_state["dataset_name"] == "sample_college.csv"
    assert len(at_college.session_state["evaluated_df"]) == 25
    assert at_college.session_state["evaluated_df"].iloc[0]["student_id"] == "001"


# =============================================================================
# 3. MULTI-THREAD CONCURRENCY ISOLATION
# =============================================================================

def simulate_user_session(dataset_id: int) -> dict:
    """Simulate an independent user session performing an academic evaluation."""
    if dataset_id == 1:
        df = pd.DataFrame({
            "student_id": [f"U1_S0{i}" for i in range(1, 6)],
            "student_name": [f"User1_Student_{i}" for i in range(1, 6)],
            "attendance": [95.0] * 5,
            "Math": [90.0, 92.0, 94.0, 96.0, 98.0],
        })
        policy = GradingPolicy(subject_pass_percentage=50.0, aggregate_pass_percentage=50.0)
    else:
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


# =============================================================================
# 4. ADDITIONAL HARDENING AND EDGE-CASE TESTS
# =============================================================================

def test_same_file_uploaded_repeatedly_preserves_analysis():
    """Verify that uploading the exact same file content repeatedly preserves valid analysis."""
    content = b"student_id,student_name,attendance,Math\nS01,Alice,95.0,90.0\n"
    file_obj = _make_mock_file("same_data.csv", content)

    with patch("streamlit.file_uploader", return_value=file_obj):
        at = AppTest.from_file("app.py")
        at.session_state["current_page"] = PAGE_CONFIG
        at.run()
        run_btn = get_button(at, "Run Academic Analysis")
        run_btn.click().run()
        assert at.session_state["evaluated_df"] is not None

        at.run()
        assert not at.exception
        assert at.session_state["evaluated_df"] is not None
        assert at.session_state["dataset_name"] == "same_data.csv"


def test_invalid_upload_followed_by_valid_upload():
    """Verify recovering from a rejected upload by submitting a valid CSV cleanly resets state."""
    invalid_content = b"header1,header1\nval1,val2\n"
    invalid_file = _make_mock_file("invalid.csv", invalid_content)

    valid_content = b"student_id,student_name,attendance,Math\nS01,Alice,95.0,90.0\n"
    valid_file = _make_mock_file("valid.csv", valid_content)

    current_file = invalid_file

    def mock_uploader(*args, **kwargs):
        return current_file

    with patch("streamlit.file_uploader", side_effect=mock_uploader):
        at = AppTest.from_file("app.py")
        at.session_state["current_page"] = PAGE_CONFIG
        at.run()
        assert at.session_state["upload_error"] is not None
        assert at.session_state["raw_df"] is None
        assert at.session_state["evaluated_df"] is None

        current_file = valid_file
        at.run()
        assert not at.exception
        assert at.session_state["upload_error"] is None
        assert at.session_state["raw_df"] is not None
        assert len(at.session_state["raw_df"]) == 1

        get_button(at, "Run Academic Analysis").click().run()
        assert at.session_state["evaluated_df"] is not None


def test_reset_button_after_failed_upload():
    """Verify reset button clears error state and resets workflow after a failed upload."""
    invalid_content = b"bad,csv,format\n"
    invalid_file = _make_mock_file("bad.csv", invalid_content)

    def mock_uploader(*args, **kwargs):
        if kwargs.get("key") == "csv_uploader_0":
            return invalid_file
        return None

    with patch("streamlit.file_uploader", side_effect=mock_uploader):
        at = AppTest.from_file("app.py")
        at.session_state["current_page"] = PAGE_CONFIG
        at.run()
        assert at.session_state["upload_error"] is not None

        reset_btn = get_sidebar_button(at, "Reset")
        reset_btn.click().run()

        assert not at.exception
        assert at.session_state["upload_error"] is None
        assert at.session_state["raw_df"] is None
        assert at.session_state["evaluated_df"] is None
        assert at.session_state["current_page"] == PAGE_OVERVIEW


def test_consecutive_grading_threshold_changes_and_reanalysis():
    """Verify modifying multiple institutional policy settings consecutively and re-evaluating."""
    at = AppTest.from_file("app.py")
    at.session_state["current_page"] = PAGE_CONFIG
    at.run()
    get_button(at, "Load Sample School Dataset").click().run()
    get_button(at, "Run Academic Analysis").click().run()
    assert at.session_state["evaluated_df"] is not None

    # Change 1: Subject passing threshold to 50
    ni_subj = [ni for ni in at.number_input if "Subject Passing Threshold" in ni.label][0]
    ni_subj.set_value(50.0).run()
    assert at.session_state["evaluated_df"] is None
    assert at.session_state["config_stale"] is True

    # Change 2: Aggregate passing threshold to 60
    ni_agg = [ni for ni in at.number_input if "Aggregate Passing Threshold" in ni.label][0]
    ni_agg.set_value(60.0).run()
    assert at.session_state["evaluated_df"] is None
    assert at.session_state["config_stale"] is True

    # Change 3: Attendance warning cutoff to 80
    ni_att = [ni for ni in at.number_input if "Attendance Warning Cutoff" in ni.label][0]
    ni_att.set_value(80.0).run()
    assert at.session_state["evaluated_df"] is None
    assert at.session_state["config_stale"] is True

    # Re-run analysis
    get_button(at, "Run Academic Analysis").click().run()

    assert not at.exception
    assert at.session_state["evaluated_df"] is not None
    assert at.session_state["config_stale"] is False
    assert at.session_state["policy"].subject_pass_percentage == 50.0
    assert at.session_state["policy"].aggregate_pass_percentage == 60.0
    assert at.session_state["policy"].attendance_warning_threshold == 80.0


def test_widget_state_isolation_across_dataset_swaps():
    """Verify switching between datasets isolates column mappings and subject settings cleanly."""
    at = AppTest.from_file("app.py")
    at.session_state["current_page"] = PAGE_CONFIG
    at.run()

    # Load School (uniform 100-mark format)
    get_button(at, "Load Sample School Dataset").click().run()
    school_subjs = at.multiselect[0].value
    assert "English" in school_subjs
    assert "Mathematics" in school_subjs

    # Load College (heterogeneous marks with labs)
    get_button(at, "Load Sample College Dataset").click().run()
    college_subjs = at.multiselect[0].value
    assert "Data_Structures" in college_subjs
    assert "Database_Lab" in college_subjs
    assert "English" not in college_subjs

    # Switch back to School
    get_button(at, "Load Sample School Dataset").click().run()
    reloaded_school_subjs = at.multiselect[0].value
    assert "English" in reloaded_school_subjs
    assert "Database_Lab" not in reloaded_school_subjs


def test_streamlit_validation_error_display_on_non_finite_marks():
    """Verify that uploading a dataset with non-finite marks shows validation errors in UI without crashing."""
    content = b"student_id,student_name,attendance,Math\nS01,Alice,90.0,inf\n"
    file_obj = _make_mock_file("infinite_marks.csv", content)

    with patch("streamlit.file_uploader", return_value=file_obj):
        at = AppTest.from_file("app.py")
        at.session_state["current_page"] = PAGE_CONFIG
        at.run()

        get_button(at, "Run Academic Analysis").click().run()

        assert not at.exception
        assert at.session_state["evaluated_df"] is None
        assert any("Validation Failed" in err.value for err in at.error)


def test_fix03_config_staleness_on_policy_and_metadata_modifications():
    """Verify that changing grade boundaries, overrides, attendance toggle, or metadata invalidates analysis results."""
    from core.grading import InstitutionMetadata, GradeBoundary

    base_cfg = create_analysis_config(
        dataset_fingerprint="fp_abc123",
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        department_col=None,
        selected_subjects=["Math", "Science"],
        subject_configs={"Math": 100.0, "Science": 100.0},
        subject_pass_percentage=40.0,
        aggregate_pass_percentage=40.0,
        attendance_warning_threshold=75.0,
        grade_boundaries=[GradeBoundary("A", 80.0), GradeBoundary("F", 0.0)],
        subject_pass_overrides={"Science": 50.0},
        enable_attendance_warning=True,
        institution_metadata=InstitutionMetadata(institution_name="St. Mary's"),
    )

    # 1. Changing grade boundaries
    cfg_gb = dict(base_cfg)
    cfg_gb["grade_boundaries"] = (("A+", 90.0), ("A", 80.0), ("F", 0.0))
    assert is_analysis_stale(cfg_gb, base_cfg) is True

    # 2. Changing subject pass overrides
    cfg_overrides = dict(base_cfg)
    cfg_overrides["subject_pass_overrides"] = {"Science": 45.0}
    assert is_analysis_stale(cfg_overrides, base_cfg) is True

    # 3. Changing attendance warning enable toggle
    cfg_att_toggle = dict(base_cfg)
    cfg_att_toggle["enable_attendance_warning"] = False
    assert is_analysis_stale(cfg_att_toggle, base_cfg) is True

    # 4. Changing institution metadata
    cfg_meta = dict(base_cfg)
    cfg_meta["institution_metadata"] = ("St. Jude's", "School", "", "")
    assert is_analysis_stale(cfg_meta, base_cfg) is True


def test_apptest_institution_metadata_and_custom_preset_flow():
    """Verify end-to-end Streamlit UI flow: applying College preset and configuring institution details."""
    at = AppTest.from_file("app.py")
    at.session_state["current_page"] = PAGE_CONFIG
    at.run()

    # 1. Load built-in School sample dataset
    get_button(at, "Load Sample School Dataset").click().run()
    assert at.session_state["raw_df"] is not None

    # 2. Configure institution metadata in text inputs
    inst_input = [ti for ti in at.text_input if "Institution Name" in ti.label][0]
    inst_input.set_value("Oxford International Academy").run()

    prog_input = [ti for ti in at.text_input if "Class / Course" in ti.label][0]
    prog_input.set_value("Class 10").run()

    # 3. Apply College grading preset
    preset_sel = [sb for sb in at.selectbox if "Select Sample Preset" in sb.label][0]
    preset_sel.select("Example College").run()

    apply_btn = get_button(at, "Apply Preset")
    apply_btn.click().run()

    # Verify custom_boundaries updated to College preset
    labels = [b.label for b in at.session_state["custom_boundaries"]]
    assert "O" in labels
    assert "E" in labels
    assert "A" in labels

    # 4. Run Academic Analysis
    run_btn = get_button(at, "Run Academic Analysis")
    run_btn.click().run()

    assert not at.exception
    assert at.session_state["evaluated_df"] is not None
    assert at.session_state["institution_metadata"].institution_name == "Oxford International Academy"
    assert at.session_state["institution_metadata"].program_name == "Class 10"

    eval_grades = set(at.session_state["evaluated_df"]["grade"])
    assert any(g in ["O", "E", "A"] for g in eval_grades)


def test_grade_boundary_editor_preserves_user_edits_on_add_tier():
    """Verify that editing a grade boundary label/percentage and then adding a tier preserves edits."""
    at = AppTest.from_file("app.py")
    at.session_state["current_page"] = PAGE_CONFIG
    at.run()

    get_button(at, "Load Sample School Dataset").click().run()
    assert at.session_state["raw_df"] is not None

    label_input = [ti for ti in at.text_input if "Grade 1 Label" in ti.label][0]
    label_input.set_value("Distinction").run()

    add_btn = get_button(at, "Add Grade Level")
    add_btn.click().run()

    assert not at.exception
    bounds = at.session_state["custom_boundaries"]
    assert bounds[0].label == "Distinction"
    assert len(bounds) == 8


def test_grade_boundary_editor_preserves_user_edits_on_remove_tier():
    """Verify that editing a grade boundary label and then removing a tier preserves edits."""
    at = AppTest.from_file("app.py")
    at.session_state["current_page"] = PAGE_CONFIG
    at.run()

    get_button(at, "Load Sample School Dataset").click().run()
    assert at.session_state["raw_df"] is not None

    label_input = [ti for ti in at.text_input if "Grade 1 Label" in ti.label][0]
    label_input.set_value("Distinction").run()

    rem_btn = get_button(at, "Remove Grade Level")
    rem_btn.click().run()

    assert not at.exception
    bounds = at.session_state["custom_boundaries"]
    assert bounds[0].label == "Distinction"
    assert len(bounds) == 6


def test_grade_boundary_editor_add_tier_at_low_percentage_avoids_duplicate():
    """Verify that adding tiers when preceding tier is <= 20% strictly decreases and avoids duplicates."""
    at = AppTest.from_file("app.py")
    at.session_state["current_page"] = PAGE_CONFIG
    at.run()

    get_button(at, "Load Sample School Dataset").click().run()
    assert at.session_state["raw_df"] is not None

    at.session_state["custom_boundaries"] = [
        GradeBoundary("Top", 90.0),
        GradeBoundary("Mid", 50.0),
        GradeBoundary("Low", 10.0),
        GradeBoundary("Fail", 0.0),
    ]
    at.session_state["gb_version"] = 10
    at.run()

    add_btn = get_button(at, "Add Grade Level")
    add_btn.click().run()

    assert not at.exception
    bounds = at.session_state["custom_boundaries"]
    pcts = [b.min_percentage for b in bounds]
    for i in range(len(pcts) - 1):
        assert pcts[i] > pcts[i + 1]


def test_student_search_special_characters_regex_safety():
    """Verify that searching with regex metacharacters does not raise unhandled exceptions."""
    at = AppTest.from_file("app.py")
    at.session_state["current_page"] = PAGE_CONFIG
    at.run()

    get_button(at, "Load Sample School Dataset").click().run()
    get_button(at, "Run Academic Analysis").click().run()
    assert at.session_state["evaluated_df"] is not None

    # Navigate to Student Explorer page
    select_page(at, PAGE_STUDENTS)
    search_inputs = [ti for ti in at.text_input if "Search by Student Name" in ti.label]
    assert len(search_inputs) > 0
    search_box = search_inputs[0]

    for special_query in ["[", "(", "*", "+", "?", "\\", "^", "$", "(.*)"]:
        search_box.set_value(special_query).run()
        assert not at.exception, f"Crash encountered with search query: {special_query}"


def test_reports_and_export_download_generation():
    """Verify that Reports & Export view renders sanitized CSV and text summary reports."""
    at = AppTest.from_file("app.py")
    at.session_state["current_page"] = PAGE_CONFIG
    at.run()

    get_button(at, "Load Sample School Dataset").click().run()
    get_button(at, "Run Academic Analysis").click().run()
    assert at.session_state["evaluated_df"] is not None

    select_page(at, PAGE_REPORTS)
    assert not at.exception
    # Verify subheaders and report preview text are rendered on the Reports page
    subheaders = [sh.value for sh in at.subheader]
    assert any("Sanitized Analyzed CSV" in s for s in subheaders)
    assert any("Summary Text Audit Report" in s for s in subheaders)
    assert any("Report Preview" in s for s in subheaders)
    assert len(at.text) > 0
    assert "EDUMETRICS ACADEMIC PERFORMANCE REPORT" in at.text[0].value


def test_workflow_a_school_quick_demo_config_synchronization():
    """Workflow A: School Quick Demo -> Dashboard -> Upload & Configure preserves settings and analysis validity."""
    at = AppTest.from_file("app.py")
    at.run()

    # 1. Click School Demo
    school_btn = get_button(at, "Load & Analyze School Model")
    school_btn.click().run()
    assert at.session_state["current_page"] == PAGE_DASHBOARD
    assert at.session_state["evaluated_df"] is not None

    # 2. Navigate to Upload & Configure
    select_page(at, PAGE_CONFIG)
    assert not at.exception
    assert at.session_state["evaluated_df"] is not None, "Evaluated DF must remain valid when opening configuration"
    assert at.session_state["config_stale"] is False, "Config must not be marked stale on clean navigation"

    # Verify displayed configuration matches computed results
    preset_sb = [sb for sb in at.selectbox if "Select Sample Preset" in sb.label][0]
    assert preset_sb.value == "Default EduMetrics"

    inst_name_ti = [ti for ti in at.text_input if "Institution Name" in ti.label][0]
    assert inst_name_ti.value == "Greenwood High School"

    prog_ti = [ti for ti in at.text_input if "Class / Course" in ti.label][0]
    assert prog_ti.value == "Class 10-A"


def test_workflow_b_college_quick_demo_config_synchronization():
    """Workflow B: College Quick Demo -> Dashboard -> Upload & Configure preserves 50-mark labs and Example College preset."""
    at = AppTest.from_file("app.py")
    at.run()

    # 1. Click College Demo
    college_btn = get_button(at, "Load & Analyze College Model")
    college_btn.click().run()
    assert at.session_state["current_page"] == PAGE_DASHBOARD
    assert at.session_state["evaluated_df"] is not None

    # 2. Navigate to Upload & Configure
    select_page(at, PAGE_CONFIG)
    assert not at.exception
    assert at.session_state["evaluated_df"] is not None, "College Evaluated DF must remain valid when opening configuration"
    assert at.session_state["config_stale"] is False, "College Config must not be marked stale on clean navigation"

    # Verify Example College preset and metadata
    preset_sb = [sb for sb in at.selectbox if "Select Sample Preset" in sb.label][0]
    assert preset_sb.value == "Example College"

    inst_name_ti = [ti for ti in at.text_input if "Institution Name" in ti.label][0]
    assert inst_name_ti.value == "Apex Institute of Technology"

    prog_ti = [ti for ti in at.text_input if "Class / Course" in ti.label][0]
    assert prog_ti.value == "B.Tech Computer Science"

    # Verify heterogeneous 50-mark labs and 100-mark theory subjects
    lab_ni = [ni for ni in at.number_input if "Database_Lab Max" in ni.label][0]
    assert lab_ni.value == 50.0

    web_ni = [ni for ni in at.number_input if "Web_Tech_Lab Max" in ni.label][0]
    assert web_ni.value == 50.0

    proj_ni = [ni for ni in at.number_input if "Project_Phase_1 Max" in ni.label][0]
    assert proj_ni.value == 50.0

    theory_ni = [ni for ni in at.number_input if "Data_Structures Max" in ni.label][0]
    assert theory_ni.value == 100.0


def test_workflow_c_open_config_without_change_preserves_analysis():
    """Workflow C: Open configuration without changing anything preserves analysis validity."""
    at = AppTest.from_file("app.py")
    at.run()
    get_button(at, "Load & Analyze School Model").click().run()
    assert at.session_state["evaluated_df"] is not None

    select_page(at, PAGE_CONFIG)
    assert at.session_state["evaluated_df"] is not None
    assert at.session_state["config_stale"] is False


def test_workflow_d_change_subject_max_marks_invalidates_analysis():
    """Workflow D: Change one subject maximum mark invalidates previous analysis until recomputed."""
    at = AppTest.from_file("app.py")
    at.run()
    get_button(at, "Load & Analyze College Model").click().run()
    assert at.session_state["evaluated_df"] is not None

    select_page(at, PAGE_CONFIG)
    theory_ni = [ni for ni in at.number_input if "Data_Structures Max" in ni.label][0]
    theory_ni.set_value(120.0).run()

    # Analysis must now be invalidated
    assert at.session_state["evaluated_df"] is None
    assert at.session_state["config_stale"] is True

    # Re-running analysis must produce updated results
    get_button(at, "Run Academic Analysis").click().run()
    assert at.session_state["evaluated_df"] is not None
    assert at.session_state["config_stale"] is False
    assert at.session_state["subject_configs"]["Data_Structures"] == 120.0


def test_workflow_e_switch_school_to_college_isolation():
    """Workflow E: Switching from School Demo to College Demo isolates all dataset-specific configuration and results."""
    at = AppTest.from_file("app.py")
    at.run()

    # School demo
    get_button(at, "Load & Analyze School Model").click().run()
    assert at.session_state["dataset_name"] == "sample_school.csv"
    assert at.session_state["institution_metadata"].institution_name == "Greenwood High School"

    # Switch to College demo
    select_page(at, PAGE_OVERVIEW)
    get_button(at, "Load & Analyze College Model").click().run()
    assert at.session_state["dataset_name"] == "sample_college.csv"
    assert at.session_state["institution_metadata"].institution_name == "Apex Institute of Technology"
    assert "Mathematics" not in at.session_state["subject_configs"]
    assert "Data_Structures" in at.session_state["subject_configs"]


def test_workflow_f_custom_upload_to_sample_and_back():
    """Workflow F: Switching from custom uploaded CSV to sample dataset and back to a new custom CSV leaves no leakage."""
    at = AppTest.from_file("app.py")
    at.run()
    select_page(at, PAGE_CONFIG)

    # 1. Custom upload A
    csv1 = b"student_id,student_name,attendance,CustomCourse\nC01,Alice,90,85\n"
    with patch("streamlit.file_uploader", return_value=_make_mock_file("custom1.csv", csv1)):
        at.run()
    assert at.session_state["dataset_name"] == "custom1.csv"
    assert "CustomCourse" in at.session_state["raw_df"].columns

    # 2. Switch to Sample School
    with patch("streamlit.file_uploader", return_value=None):
        get_button(at, "Sample School Dataset").click().run()
    assert at.session_state["dataset_name"] == "sample_school.csv"
    assert "CustomCourse" not in at.session_state["raw_df"].columns

    # 3. New custom upload B
    csv2 = b"reg_no,full_name,attendance,Physics\nP01,Bob,92,78\n"
    with patch("streamlit.file_uploader", return_value=_make_mock_file("custom2.csv", csv2)):
        at.run()
    assert at.session_state["dataset_name"] == "custom2.csv"
    assert "English" not in at.session_state["raw_df"].columns
    assert "Physics" in at.session_state["raw_df"].columns

