"""Centralized session state management and integrity enforcement for EduMetrics.

Provides lightweight, reusable helper functions to:
1. Initialize session state schema.
2. Invalidate and clear calculated analytics results.
3. Replace the active dataset while guaranteeing previous results are discarded.
4. Track the exact effective configuration used for an analysis.
5. Detect configuration and dataset changes that make active results stale.
6. Reset complete workflow and widget state cleanly.
7. Safeguard against cross-dataset data leakage and stale metric displays.
"""

import hashlib
from typing import Dict, List, Optional, Tuple, Any, MutableMapping
import pandas as pd

from core.grading import GradingPolicy, GradeBoundary


def _get_state(state: Optional[MutableMapping] = None) -> MutableMapping:
    """Return the provided session state mapping or default to st.session_state."""
    if state is not None:
        return state
    import streamlit as st
    return st.session_state


def compute_dataset_fingerprint(file_bytes: bytes) -> str:
    """Compute a deterministic SHA-256 fingerprint for dataset content."""
    if not file_bytes:
        return ""
    return hashlib.sha256(file_bytes).hexdigest()


def init_session_state(state: Optional[MutableMapping] = None) -> MutableMapping:
    """Ensure all core session state keys are safely initialized."""
    s = _get_state(state)
    defaults = {
        "raw_df": None,
        "dataset_name": None,
        "dataset_fingerprint": None,
        "dataset_source": None,  # "upload" | "sample" | None
        "evaluated_df": None,
        "class_summary": None,
        "subject_metrics": None,
        "attention_students": None,
        "policy": GradingPolicy(),
        "subject_configs": {},
        "analysis_config": None,
        "upload_error": None,
        "uploader_key": 0,
        "config_stale": False,
    }
    for key, val in defaults.items():
        if key not in s:
            s[key] = val
    return s


def clear_analysis_results(state: Optional[MutableMapping] = None) -> None:
    """Clear all calculated analysis results and invalidate the active analysis."""
    s = _get_state(state)
    s["evaluated_df"] = None
    s["class_summary"] = None
    s["subject_metrics"] = None
    s["attention_students"] = None
    s["analysis_config"] = None


def replace_active_dataset(
    df: pd.DataFrame,
    dataset_name: str,
    fingerprint: str,
    source: str = "upload",
    state: Optional[MutableMapping] = None,
) -> None:
    """Replace the active dataset and cleanly invalidate previous results and configurations."""
    s = _get_state(state)
    clear_analysis_results(s)
    s["raw_df"] = df
    s["dataset_name"] = dataset_name
    s["dataset_fingerprint"] = fingerprint
    s["dataset_source"] = source
    s["upload_error"] = None
    s["config_stale"] = False
    s["subject_configs"] = {}
    # Clean up any lingering widget keys from previous datasets
    for k in list(s.keys()):
        if any(k.startswith(prefix) for prefix in ("col_", "sel_subjs_", "max_m_", "pol_")):
            del s[k]


def handle_failed_upload(
    error_message: str,
    state: Optional[MutableMapping] = None,
) -> None:
    """Handle an invalid upload by resetting active data to prevent inconsistent state."""
    s = _get_state(state)
    clear_analysis_results(s)
    s["raw_df"] = None
    s["dataset_name"] = None
    s["dataset_fingerprint"] = None
    s["dataset_source"] = None
    s["subject_configs"] = {}
    s["upload_error"] = error_message
    s["config_stale"] = False
    # Clean up lingering widget keys
    for k in list(s.keys()):
        if any(k.startswith(prefix) for prefix in ("col_", "sel_subjs_", "max_m_", "pol_")):
            del s[k]


def clear_removed_upload(state: Optional[MutableMapping] = None) -> None:
    """Clear state when user removes the uploaded file from the uploader."""
    s = _get_state(state)
    clear_analysis_results(s)
    s["raw_df"] = None
    s["dataset_name"] = None
    s["dataset_fingerprint"] = None
    s["dataset_source"] = None
    s["subject_configs"] = {}
    s["upload_error"] = None
    s["config_stale"] = False


def reset_complete_workflow(state: Optional[MutableMapping] = None) -> None:
    """Reset the entire workflow, clearing all session state and bumping uploader key."""
    s = _get_state(state)
    current_uploader_key = s.get("uploader_key", 0)
    next_key = current_uploader_key + 1
    # Clear all keys
    for k in list(s.keys()):
        del s[k]
    # Re-initialize with incremented uploader key
    init_session_state(s)
    s["uploader_key"] = next_key


def create_analysis_config(
    dataset_fingerprint: str,
    student_id_col: str,
    name_col: str,
    attendance_col: str,
    department_col: Optional[str],
    selected_subjects: List[str],
    subject_configs: Dict[str, float],
    subject_pass_percentage: float,
    aggregate_pass_percentage: float,
    attendance_warning_threshold: float,
    grade_boundaries: Optional[List[GradeBoundary]] = None,
) -> dict:
    """Construct a normalized dictionary tracking effective settings used for analysis."""
    if grade_boundaries is None:
        grade_boundaries = GradingPolicy().grade_boundaries
    return {
        "dataset_fingerprint": str(dataset_fingerprint),
        "student_id_col": str(student_id_col),
        "name_col": str(name_col),
        "attendance_col": str(attendance_col),
        "department_col": str(department_col) if department_col else None,
        "selected_subjects": sorted(list(selected_subjects)),
        "subject_configs": {k: float(v) for k, v in sorted(subject_configs.items())},
        "subject_pass_percentage": float(subject_pass_percentage),
        "aggregate_pass_percentage": float(aggregate_pass_percentage),
        "attendance_warning_threshold": float(attendance_warning_threshold),
        "grade_boundaries": tuple((b.label, float(b.min_percentage)) for b in grade_boundaries),
    }


def is_analysis_stale(
    current_config: dict,
    analysis_config: Optional[dict],
) -> bool:
    """Determine whether active analysis results are stale compared to current configuration."""
    if analysis_config is None:
        return False
    return current_config != analysis_config
