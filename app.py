"""EduMetrics — Academic Performance Analytics Web Dashboard.

Production-minded, privacy-first academic performance analytics platform.
Presentation layer for EduMetrics core engine.
"""

import os
from typing import Dict, List, Optional
import streamlit as st
import pandas as pd

from security.upload_checks import (
    MAX_FILE_SIZE_BYTES,
    MAX_ROW_COUNT,
    MAX_COLUMN_COUNT,
)
from core.loader import load_csv_from_bytes, IngestionError
from core.validation import validate_dataset, ValidationResult
from core.grading import (
    GradingPolicy,
    GradeBoundary,
    InstitutionMetadata,
    GRADING_PRESETS,
    parse_grade_boundaries_string,
    PolicyConfigurationError,
    evaluate_students,
)
from core.analytics import (
    compute_class_summary,
    compute_subject_analytics,
    compute_department_summary,
    identify_academic_attention_cases,
    get_top_performers,
)
from core.reports import generate_text_summary, generate_sanitized_csv
from core.session_state import (
    init_session_state,
    clear_analysis_results,
    replace_active_dataset,
    handle_failed_upload,
    clear_removed_upload,
    reset_complete_workflow,
    create_analysis_config,
    is_analysis_stale,
    compute_dataset_fingerprint,
)

# Page configuration
st.set_page_config(
    page_title="EduMetrics — Academic Analytics",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for polished, accessible, restrained presentation
st.markdown("""
<style>
    .metric-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .badge-pass {
        background-color: #DCFCE7;
        color: #166534;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85em;
    }
    .badge-fail {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85em;
    }
    .privacy-notice {
        background-color: #EFF6FF;
        border-left: 4px solid #3B82F6;
        padding: 12px 16px;
        border-radius: 4px;
        margin-bottom: 20px;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)


# Initialize Centralized Session State
init_session_state()


def reset_session():
    """Reset the session workflow and clear active session references."""
    reset_complete_workflow()
    st.rerun()


# Sidebar Navigation & Session Controls
with st.sidebar:
    st.title("🎓 EduMetrics")
    st.caption("Academic Performance Analytics Platform (V1)")
    st.markdown("---")

    if st.session_state.evaluated_df is not None:
        st.success(f"Active Dataset: **{st.session_state.dataset_name}**")
        st.write(f"📊 Records: **{len(st.session_state.evaluated_df)}**")
        st.write(f"📈 Pass Rate: **{st.session_state.class_summary.overall_pass_percentage:.1f}%**")
    elif st.session_state.raw_df is not None:
        st.info(f"Loaded Dataset: **{st.session_state.dataset_name}**")
        st.write(f"📊 Records: **{len(st.session_state.raw_df)}**")
        st.caption("⚙️ Configure settings and click 'Run Academic Analysis' to view metrics.")
    elif st.session_state.upload_error is not None:
        st.error("Upload error detected.")
    else:
        st.info("No active dataset loaded. Please upload a CSV to begin.")

    st.markdown("---")
    if st.button("🔄 Start New Analysis / Reset", use_container_width=True):
        reset_session()

    st.markdown("---")
    st.markdown("### 🔒 Privacy & Operational Reality")
    st.caption(
        "EduMetrics V1 processes data strictly in transient server-side memory. "
        "The application does not intentionally persist datasets to disk or databases. "
        "Streamlit session state is an ephemeral UI container, not an authenticated security boundary. "
        "Resetting the session removes active references but cannot guarantee instant physical RAM erasure. "
        "Please use fictional or anonymized student records only."
    )


# Top Banner Privacy Notice
st.markdown("""
<div class="privacy-notice">
    <strong>EduMetrics Privacy Notice:</strong> Analysis occurs entirely in transient server-side memory scoped to your active session. 
    The application does not intentionally persist uploaded student datasets to disk or databases. 
    However, hosting providers may maintain operational memory/network logs, and browser sessions do not constitute an authenticated security boundary. 
    Resetting the session removes active application references but cannot guarantee immediate physical RAM sanitization. 
    <strong>Please upload fictional or properly de-identified / anonymized academic datasets only.</strong>
</div>
""", unsafe_allow_html=True)


# Main Tab Navigation
tabs = st.tabs([
    "📖 Overview & Samples",
    "📤 Upload & Configure",
    "📊 Performance Dashboard",
    "📚 Subject Analysis",
    "🔍 Student Explorer",
    "⚠️ Academic Attention",
    "📥 Reports & Export",
    "ℹ️ Help & Methodology",
])


# -----------------------------------------------------------------------------
# TAB 1: OVERVIEW & SAMPLES
# -----------------------------------------------------------------------------
with tabs[0]:
    st.header("Academic Performance Analytics Platform")
    st.markdown("""
    **EduMetrics** enables educators to validate marks datasets, configure institutional grading policies, 
    perform statistical analyses, and download sanitized reports without requiring spreadsheet programming.
    """)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏫 Sample 1: K-12 School Model")
        st.markdown("""
        - **Records:** 20 fictional students across 2 sections.
        - **Subjects:** English, Mathematics, Science, Social Studies, Second Language.
        - **Format:** Uniform 100-mark scoring scale.
        """)
        if os.path.exists("data/sample_school.csv"):
            with open("data/sample_school.csv", "rb") as f_s:
                st.download_button(
                    label="⬇️ Download School CSV Template",
                    data=f_s.read(),
                    file_name="sample_school.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

    with col2:
        st.subheader("🏛️ Sample 2: University Engineering Model")
        st.markdown("""
        - **Records:** 25 fictional students across CSE, IT, and ECE.
        - **Identifiers:** Leading zero preservation (`"001"`, `"002"`).
        - **Subjects:** 100-mark theory subjects + 50-mark lab/project courses.
        """)
        if os.path.exists("data/sample_college.csv"):
            with open("data/sample_college.csv", "rb") as f_c:
                st.download_button(
                    label="⬇️ Download College CSV Template",
                    data=f_c.read(),
                    file_name="sample_college.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

    st.markdown("---")
    st.markdown("### Quick Start Workflow")
    st.markdown("""
    1. Download one of the sample CSV templates above or prepare your own CSV.
    2. Switch to the **Upload & Configure** tab.
    3. Upload your CSV and verify column mappings.
    4. Adjust grading boundaries, pass thresholds, and maximum marks if needed.
    5. Click **Run Academic Analysis** to generate the interactive dashboard.
    """)


# -----------------------------------------------------------------------------
# TAB 2: UPLOAD & CONFIGURE
# -----------------------------------------------------------------------------
with tabs[1]:
    st.header("Dataset Ingestion & Configuration")

    uploaded_file = st.file_uploader(
        "Upload Academic Marks CSV",
        type=["csv"],
        key=f"csv_uploader_{st.session_state.uploader_key}",
        help=f"File must be plain text CSV, under {MAX_FILE_SIZE_BYTES // (1024*1024)} MB and <= {MAX_ROW_COUNT} rows.",
    )

    sample_loaded = False
    st.write("**Or load a built-in fictional dataset directly:**")
    c1, c2, _ = st.columns([1, 1, 2])
    with c1:
        if st.button("Load Sample School Dataset"):
            try:
                with open("data/sample_school.csv", "rb") as f:
                    file_bytes = f.read()
                df, cols = load_csv_from_bytes(file_bytes, "sample_school.csv")
                fingerprint = compute_dataset_fingerprint(file_bytes)
                replace_active_dataset(df, "sample_school.csv", fingerprint, source="sample")
                st.session_state.uploader_key += 1
                sample_loaded = True
            except Exception as err:
                handle_failed_upload(f"Failed to load sample dataset: {err}")
                sample_loaded = True
            st.rerun()
    with c2:
        if st.button("Load Sample College Dataset"):
            try:
                with open("data/sample_college.csv", "rb") as f:
                    file_bytes = f.read()
                df, cols = load_csv_from_bytes(file_bytes, "sample_college.csv")
                fingerprint = compute_dataset_fingerprint(file_bytes)
                replace_active_dataset(df, "sample_college.csv", fingerprint, source="sample")
                st.session_state.uploader_key += 1
                sample_loaded = True
            except Exception as err:
                handle_failed_upload(f"Failed to load sample dataset: {err}")
                sample_loaded = True
            st.rerun()

    # Process uploaded file if user provided one and a sample dataset was not just selected
    if not sample_loaded and uploaded_file is not None:
        try:
            file_bytes = uploaded_file.getvalue()
            fingerprint = compute_dataset_fingerprint(file_bytes)
            # Detect actual dataset change or initial upload
            if (
                fingerprint != st.session_state.dataset_fingerprint
                or st.session_state.dataset_source != "upload"
            ):
                df, cols = load_csv_from_bytes(file_bytes, uploaded_file.name)
                replace_active_dataset(df, uploaded_file.name, fingerprint, source="upload")
                st.success(f"Loaded '{uploaded_file.name}' with {len(df)} records.")
        except IngestionError as err:
            handle_failed_upload(f"Upload rejected: {err}")
        except Exception:
            handle_failed_upload(
                "Upload rejected: The file could not be parsed as a valid CSV. Please ensure it is well-formed."
            )
    elif not sample_loaded and uploaded_file is None:
        # If user removed the file in the uploader and the active dataset was from an upload
        if st.session_state.dataset_source == "upload":
            clear_removed_upload()

    # Display upload errors if any
    if st.session_state.upload_error:
        st.error(st.session_state.upload_error)
        st.info("ℹ️ Previous dataset and analysis results have been cleared to prevent data inconsistency. Please provide a valid CSV.")

    # Configuration Form
    if st.session_state.raw_df is not None:
        raw_df = st.session_state.raw_df
        available_cols = list(raw_df.columns)
        fp = st.session_state.dataset_fingerprint or "default"

        # ---------------------------------------------------------------------
        # 1. INSTITUTION DETAILS
        # ---------------------------------------------------------------------
        st.subheader("1. Institution Details")
        st.caption("Configure optional institutional metadata to contextualize academic performance reports.")
        with st.expander("🏫 Institution Metadata (Optional)", expanded=False):
            inst_col1, inst_col2 = st.columns(2)
            with inst_col1:
                inst_name = st.text_input(
                    "Institution Name",
                    value=st.session_state.institution_metadata.institution_name,
                    key=f"inst_name_{fp}",
                    help="Name of school, college, or university (e.g. Greenwood High School).",
                )
                level_options = ["School", "College", "University", "Other"]
                curr_level = st.session_state.institution_metadata.academic_level or "School"
                curr_lvl_idx = level_options.index(curr_level) if curr_level in level_options else 0
                inst_level = st.selectbox(
                    "Academic Level",
                    options=level_options,
                    index=curr_lvl_idx,
                    key=f"inst_level_{fp}",
                    help="Classification of the educational institution.",
                )
            with inst_col2:
                inst_program = st.text_input(
                    "Class / Course / Program Name",
                    value=st.session_state.institution_metadata.program_name,
                    key=f"inst_prog_{fp}",
                    help="e.g. Class 10-A, B.Tech Computer Science, Year 2.",
                )
                inst_term = st.text_input(
                    "Academic Term / Semester",
                    value=st.session_state.institution_metadata.academic_term,
                    key=f"inst_term_{fp}",
                    help="e.g. Term 1, Semester IV, Fall 2026.",
                )
            current_inst_meta = InstitutionMetadata(
                institution_name=inst_name,
                academic_level=inst_level,
                program_name=inst_program,
                academic_term=inst_term,
            )

        # ---------------------------------------------------------------------
        # 2. COLUMN MAPPING
        # ---------------------------------------------------------------------
        st.subheader("2. Column Mapping")
        st.caption("Map the columns in your CSV to standard academic fields.")

        # Heuristic auto-selection of columns
        def find_default(candidates: list, options: list) -> int:
            for c in candidates:
                for idx, opt in enumerate(options):
                    if c.lower() == opt.lower() or c.lower() in opt.lower():
                        return idx
            return 0

        cm1, cm2, cm3, cm4 = st.columns(4)
        with cm1:
            id_idx = find_default(["student_id", "id", "roll", "reg_no"], available_cols)
            selected_id = st.selectbox(
                "Student ID *",
                available_cols,
                index=id_idx,
                key=f"col_id_{fp}",
                help="Unique student identification number or registration roll.",
            )
        with cm2:
            name_idx = find_default(["student_name", "name", "full_name"], available_cols)
            selected_name = st.selectbox(
                "Student Name *",
                available_cols,
                index=name_idx,
                key=f"col_name_{fp}",
                help="Official student full name.",
            )
        with cm3:
            att_idx = find_default(["attendance", "attendance_pct", "att"], available_cols)
            selected_att = st.selectbox(
                "Attendance (%) *",
                available_cols,
                index=att_idx,
                key=f"col_att_{fp}",
                help="Attendance percentage value between 0.0% and 100.0%.",
            )
        with cm4:
            dept_opts = ["None"] + available_cols
            dept_idx = find_default(["department", "dept", "section", "class"], dept_opts)
            selected_dept_opt = st.selectbox(
                "Department / Section",
                dept_opts,
                index=dept_idx,
                key=f"col_dept_{fp}",
                help="Optional cohort grouping (e.g. Section A, CSE, Grade 10).",
            )
            selected_dept = None if selected_dept_opt == "None" else selected_dept_opt

        # ---------------------------------------------------------------------
        # 3. SUBJECT CONFIGURATION
        # ---------------------------------------------------------------------
        st.subheader("3. Subject Configuration")
        st.caption("Select academic courses, specify maximum possible marks, and configure subject pass thresholds.")

        excluded_from_subjects = [selected_id, selected_name, selected_att]
        if selected_dept:
            excluded_from_subjects.append(selected_dept)

        candidate_subjects = [c for c in available_cols if c not in excluded_from_subjects]
        selected_subjects = st.multiselect(
            "Select Subject Columns for Analysis *",
            options=candidate_subjects,
            default=candidate_subjects,
            key=f"sel_subjs_{fp}",
            help="Select all columns that represent academic course marks.",
        )

        subject_configs: Dict[str, float] = {}
        subject_pass_overrides: Dict[str, float] = {}
        if selected_subjects:
            st.write("**Subject Maximum Marks & Passing Cutoffs:**")
            enable_overrides = st.checkbox(
                "Configure subject-specific passing thresholds (optional)",
                key=f"enable_subj_overrides_{fp}",
                help="Check this if different courses have distinct passing percentage cutoffs (e.g. 50% for practical vs 40% for theory).",
            )
            sub_cols = st.columns(min(len(selected_subjects), 4))
            for i, subj in enumerate(selected_subjects):
                col_target = sub_cols[i % len(sub_cols)]
                default_max = 50.0 if any(k in subj.lower() for k in ["lab", "project", "practical"]) else 100.0
                max_val = col_target.number_input(
                    f"{subj} Max",
                    min_value=1.0,
                    max_value=500.0,
                    value=default_max,
                    step=5.0,
                    key=f"max_m_{subj}_{fp}",
                    help=f"Maximum possible score achievable in {subj}.",
                )
                subject_configs[subj] = float(max_val)
                if enable_overrides:
                    pass_val = col_target.number_input(
                        f"{subj} Pass Cut (%)",
                        min_value=0.0,
                        max_value=100.0,
                        value=40.0,
                        step=1.0,
                        key=f"pass_m_{subj}_{fp}",
                        help=f"Minimum percentage required to pass {subj}.",
                    )
                    subject_pass_overrides[subj] = float(pass_val)

        # ---------------------------------------------------------------------
        # 4. GRADING POLICY
        # ---------------------------------------------------------------------
        st.subheader("4. Grading Policy")
        st.caption("Configure passing criteria, grading scale presets, and customizable grade brackets.")
        pol1, pol2 = st.columns(2)
        with pol1:
            subj_pass_pct = st.number_input(
                "Subject Passing Threshold (%)",
                min_value=0.0,
                max_value=100.0,
                value=40.0,
                step=1.0,
                key=f"pol_subj_{fp}",
                help="Minimum percentage required in each individual subject unless overridden.",
            )
        with pol2:
            agg_pass_pct = st.number_input(
                "Aggregate Passing Threshold (%)",
                min_value=0.0,
                max_value=100.0,
                value=40.0,
                step=1.0,
                key=f"pol_agg_{fp}",
                help="Minimum overall normalized aggregate percentage required to pass.",
            )

        # Sample Presets Selector
        st.write("**Grading Scale Presets:**")
        st.caption("Select a sample preset (illustrative reference, not official institutional regulations):")
        pre_col1, pre_col2 = st.columns([3, 1])
        with pre_col1:
            preset_choice = st.selectbox(
                "Select Sample Preset",
                options=["Default EduMetrics", "Example School", "Example College"],
                key=f"preset_sel_{fp}",
                label_visibility="collapsed",
            )
        with pre_col2:
            if st.button("Apply Preset", key=f"btn_apply_preset_{fp}"):
                st.session_state.custom_boundaries = [
                    GradeBoundary(b.label, b.min_percentage) for b in GRADING_PRESETS[preset_choice]
                ]
                st.session_state.gb_version = st.session_state.get("gb_version", 0) + 1
                clear_analysis_results()
                st.session_state.config_stale = True
                st.rerun()

        # Custom Grade Boundaries Editor
        st.write("**Grade Boundaries:**")
        st.caption("Customize letter grade labels and minimum percentage thresholds (unrounded percentage evaluation).")
        gb_ver = st.session_state.get("gb_version", 0)
        active_bounds = st.session_state.get("custom_boundaries", GRADING_PRESETS["Default EduMetrics"])

        edited_boundaries: List[GradeBoundary] = []
        for i, b in enumerate(active_bounds):
            g1, g2, g3 = st.columns([2, 3, 3])
            with g1:
                lbl = st.text_input(
                    f"Grade {i+1} Label",
                    value=b.label,
                    key=f"gb_label_{i}_{fp}_{gb_ver}",
                )
            with g2:
                is_lowest = (i == len(active_bounds) - 1)
                min_val = st.number_input(
                    f"Min % for {lbl or f'Tier {i+1}'}",
                    min_value=0.0,
                    max_value=100.0,
                    value=0.0 if is_lowest else float(b.min_percentage),
                    step=1.0,
                    disabled=is_lowest,
                    key=f"gb_min_{i}_{fp}_{gb_ver}",
                    help="Lowest grade boundary must begin at 0%." if is_lowest else "Minimum score percentage required for this grade.",
                )
            with g3:
                if i == 0:
                    st.caption(f"Score Range: ≥ {min_val:.1f}% to 100.0%")
                elif is_lowest:
                    st.caption("Score Range: 0.0% to < preceding tier")
                else:
                    st.caption(f"Score Range: ≥ {min_val:.1f}% to < preceding tier")
            edited_boundaries.append(GradeBoundary(label=lbl, min_percentage=0.0 if is_lowest else min_val))

        st.session_state.custom_boundaries = edited_boundaries

        btn1, btn2, _ = st.columns([1, 1, 2])
        with btn1:
            if st.button("➕ Add Grade Level", key=f"btn_add_tier_{fp}"):
                if len(edited_boundaries) < 12:
                    last = edited_boundaries[-1]
                    prev_pct = edited_boundaries[-2].min_percentage if len(edited_boundaries) >= 2 else 50.0
                    new_pct = max(10.0, prev_pct - 10.0)
                    st.session_state.custom_boundaries = list(edited_boundaries[:-1]) + [GradeBoundary(f"G{len(edited_boundaries)}", new_pct), last]
                    st.session_state.gb_version = gb_ver + 1
                    clear_analysis_results()
                    st.session_state.config_stale = True
                    st.rerun()
                else:
                    st.warning("Maximum of 12 grade levels reached.")
        with btn2:
            if st.button("➖ Remove Grade Level", key=f"btn_rem_tier_{fp}"):
                if len(edited_boundaries) > 2:
                    st.session_state.custom_boundaries = list(edited_boundaries[:-2]) + [edited_boundaries[-1]]
                    st.session_state.gb_version = gb_ver + 1
                    clear_analysis_results()
                    st.session_state.config_stale = True
                    st.rerun()
                else:
                    st.warning("Minimum of 2 grade levels required.")

        # Real-time policy validation feedback
        policy_error = None
        try:
            test_policy = GradingPolicy(
                subject_pass_percentage=subj_pass_pct,
                aggregate_pass_percentage=agg_pass_pct,
                grade_boundaries=edited_boundaries,
                subject_pass_overrides=subject_pass_overrides,
            )
            test_policy.validate()
        except (PolicyConfigurationError, ValueError) as p_val_err:
            policy_error = str(p_val_err)
            st.error(f"⚠️ Policy Validation Warning: {policy_error}")

        # ---------------------------------------------------------------------
        # 5. ATTENDANCE POLICY
        # ---------------------------------------------------------------------
        st.subheader("5. Attendance Policy")
        st.caption("Configure attendance shortage alert threshold and academic evaluation isolation.")
        att1, att2 = st.columns(2)
        with att1:
            att_warn_thresh = st.number_input(
                "Attendance Warning Cutoff (%)",
                min_value=0.0,
                max_value=100.0,
                value=75.0,
                step=1.0,
                key=f"pol_att_{fp}",
                help="Attendance percentage below which students receive an attendance warning.",
            )
        with att2:
            st.write("")
            st.write("")
            enable_att_warn = st.checkbox(
                "Enable Attendance Shortage Warning Indicator",
                value=True,
                key=f"pol_att_enable_{fp}",
                help="When enabled, flags students below the attendance cutoff. Attendance warnings do not cause academic course failure.",
            )
        st.caption("ℹ️ **Academic Distinction:** Attendance is monitored as a pastoral and regulatory indicator. Low attendance triggers an advisory warning but does not automatically fail students.")

        # ---------------------------------------------------------------------
        # 6. POLICY PREVIEW
        # ---------------------------------------------------------------------
        st.subheader("6. Policy Preview")
        st.caption("Review active institutional settings, passing criteria, and grade scale before analysis.")
        with st.expander("👁️ View Active Policy Snapshot", expanded=True):
            if not current_inst_meta.is_empty():
                st.markdown(f"**Institution:** {current_inst_meta.institution_name or 'N/A'} | **Level:** {current_inst_meta.academic_level} | **Program:** {current_inst_meta.program_name or 'N/A'} | **Term:** {current_inst_meta.academic_term or 'N/A'}")
            p_prev1, p_prev2 = st.columns(2)
            with p_prev1:
                st.write("**Passing Criteria:**")
                st.write(f"- Subject Pass Threshold: **{subj_pass_pct:.1f}%**")
                if subject_pass_overrides:
                    for s, o_val in sorted(subject_pass_overrides.items()):
                        st.write(f"  - *{s} Override:* **{o_val:.1f}%**")
                st.write(f"- Aggregate Pass Threshold: **{agg_pass_pct:.1f}%**")
                st.write(f"- Attendance Alert: **{'< ' + str(att_warn_thresh) + '%' if enable_att_warn else 'Disabled'}**")
            with p_prev2:
                st.write("**Active Grade Scale:**")
                scale_items = []
                for idx, b in enumerate(edited_boundaries):
                    if idx == 0:
                        rng = f"≥ {b.min_percentage:.0f}% to 100%"
                    else:
                        prev_b = edited_boundaries[idx - 1]
                        rng = f"≥ {b.min_percentage:.0f}% to < {prev_b.min_percentage:.0f}%"
                    scale_items.append({"Grade": b.label, "Minimum %": f"{b.min_percentage:.1f}%", "Score Range": rng})
                st.dataframe(pd.DataFrame(scale_items), hide_index=True, use_container_width=True)

        # ---------------------------------------------------------------------
        # 7. RUN ANALYSIS
        # ---------------------------------------------------------------------
        st.subheader("7. Run Analysis")

        current_config = create_analysis_config(
            dataset_fingerprint=st.session_state.dataset_fingerprint or "",
            student_id_col=selected_id,
            name_col=selected_name,
            attendance_col=selected_att,
            department_col=selected_dept,
            selected_subjects=selected_subjects,
            subject_configs=subject_configs,
            subject_pass_percentage=subj_pass_pct,
            aggregate_pass_percentage=agg_pass_pct,
            attendance_warning_threshold=att_warn_thresh,
            grade_boundaries=edited_boundaries,
            subject_pass_overrides=subject_pass_overrides,
            enable_attendance_warning=enable_att_warn,
            institution_metadata=current_inst_meta,
        )

        if is_analysis_stale(current_config, st.session_state.analysis_config):
            clear_analysis_results()
            st.session_state.config_stale = True

        if st.session_state.config_stale and st.session_state.evaluated_df is None:
            st.warning(
                "⚠️ Academic configuration or column mapping has changed. "
                "Previous analysis results have been invalidated to maintain data integrity. "
                "Please click **'🚀 Run Academic Analysis'** below to generate updated results."
            )

        if st.button("🚀 Run Academic Analysis", type="primary", use_container_width=True):
            if not selected_subjects:
                st.error("Please select at least one subject column.")
            elif policy_error:
                st.error(f"Cannot run analysis with invalid grading policy: {policy_error}")
            else:
                # 1. Validate dataset
                val_result = validate_dataset(
                    df=raw_df,
                    student_id_col=selected_id,
                    name_col=selected_name,
                    attendance_col=selected_att,
                    subject_configs=subject_configs,
                    department_col=selected_dept,
                )

                if not val_result.is_valid:
                    st.error(f"Validation Failed with {val_result.error_count} error(s):")
                    for err in val_result.errors:
                        st.markdown(f"- **{err}**")
                else:
                    # 2. Build Policy & Evaluate
                    try:
                        policy = GradingPolicy(
                            subject_pass_percentage=subj_pass_pct,
                            aggregate_pass_percentage=agg_pass_pct,
                            attendance_warning_threshold=att_warn_thresh,
                            grade_boundaries=edited_boundaries,
                            subject_pass_overrides=subject_pass_overrides,
                            enable_attendance_warning=enable_att_warn,
                        )
                        policy.validate()
                        df_evaluated = evaluate_students(
                            df=raw_df,
                            student_id_col=selected_id,
                            name_col=selected_name,
                            attendance_col=selected_att,
                            subject_configs=subject_configs,
                            policy=policy,
                            department_col=selected_dept,
                        )

                        # 3. Analytics
                        pass_thresh_param = policy.subject_pass_overrides if policy.subject_pass_overrides else policy.subject_pass_percentage
                        summary = compute_class_summary(df_evaluated)
                        subj_metrics = compute_subject_analytics(df_evaluated, subject_configs, pass_thresh_param)
                        attention_cases = identify_academic_attention_cases(
                            df_evaluated,
                            subject_configs,
                            pass_thresh_param,
                            aggregate_pass_threshold=policy.aggregate_pass_percentage,
                            attendance_warning_threshold=policy.attendance_warning_threshold,
                        )

                        # Store in session state
                        st.session_state.evaluated_df = df_evaluated
                        st.session_state.class_summary = summary
                        st.session_state.subject_metrics = subj_metrics
                        st.session_state.attention_students = attention_cases
                        st.session_state.policy = policy
                        st.session_state.institution_metadata = current_inst_meta
                        st.session_state.subject_configs = subject_configs
                        st.session_state.analysis_config = current_config
                        st.session_state.config_stale = False

                        st.success("✅ Analysis successfully computed! View the results across the tabs above.")
                    except PolicyConfigurationError as p_err:
                        st.error(f"⚠️ Policy Configuration Error: {p_err}")
                    except ValueError as v_err:
                        st.error(f"⚠️ Academic Evaluation Error: {v_err}")


# -----------------------------------------------------------------------------
# TAB 3: PERFORMANCE DASHBOARD
# -----------------------------------------------------------------------------
with tabs[2]:
    if st.session_state.evaluated_df is None:
        st.info("Please upload a dataset and run the analysis in the 'Upload & Configure' tab.")
    else:
        summary = st.session_state.class_summary
        df_eval = st.session_state.evaluated_df

        inst_title = f"{st.session_state.institution_metadata.institution_name} — " if (st.session_state.institution_metadata and st.session_state.institution_metadata.institution_name) else ""
        st.header(f"Academic Performance Dashboard — {inst_title}{st.session_state.dataset_name}")

        # Top Metric Cards
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Students", summary.total_students)
        m2.metric("Overall Pass Rate", f"{summary.overall_pass_percentage:.1f}%", f"{summary.passed_students} Passed")
        m3.metric("Class Average", f"{summary.average_percentage:.1f}%", f"Median: {summary.median_percentage:.1f}%")
        m4.metric("Mean Attendance", f"{summary.average_attendance:.1f}%", f"{summary.attendance_shortage_count} Shortages", delta_color="inverse")
        m5.metric("Top Score", f"{summary.highest_percentage:.1f}%", summary.top_student_name)

        st.markdown("---")

        # Class Grade Distribution & Extremes
        c_left, c_right = st.columns([3, 2])

        with c_left:
            st.subheader("📊 Letter Grade Distribution")
            if summary.grade_distribution:
                # Order grades according to active grading policy
                grade_order = [b.label for b in st.session_state.policy.grade_boundaries]
                ordered_counts = {g: summary.grade_distribution.get(g, 0) for g in grade_order}
                st.bar_chart(ordered_counts)
            else:
                st.write("No grades assigned.")

        with c_right:
            st.subheader("📈 Statistical Overview")
            stat_df = pd.DataFrame({
                "Metric": [
                    "Total Records", "Passed Students", "Failed Students",
                    "Class Average (%)", "Class Median (%)", "Std Deviation",
                    "Highest Score (%)", "Lowest Score (%)", "Attendance Warnings"
                ],
                "Value": [
                    str(summary.total_students), str(summary.passed_students), str(summary.failed_students),
                    f"{summary.average_percentage:.2f}%", f"{summary.median_percentage:.2f}%", f"{summary.std_percentage:.2f}",
                    f"{summary.highest_percentage:.1f}% ({summary.top_student_name})",
                    f"{summary.lowest_percentage:.1f}% ({summary.lowest_student_name})",
                    str(summary.attendance_shortage_count)
                ]
            })
            st.dataframe(stat_df, hide_index=True, use_container_width=True)

        st.markdown("---")
        st.subheader("🏆 Top Performers Leaderboard (Deterministic Ranking)")
        top_df = get_top_performers(df_eval, n=5)
        display_top_cols = ["rank", "student_id", "student_name", "department", "percentage", "grade", "attendance", "status"]
        st.dataframe(top_df[[c for c in display_top_cols if c in top_df.columns]], hide_index=True, use_container_width=True)


# -----------------------------------------------------------------------------
# TAB 4: SUBJECT ANALYSIS
# -----------------------------------------------------------------------------
with tabs[3]:
    if st.session_state.evaluated_df is None:
        st.info("Please upload a dataset and run the analysis in the 'Upload & Configure' tab.")
    else:
        st.header("Subject-Wise Performance & Difficulty Rankings")
        metrics = st.session_state.subject_metrics

        subj_rows = []
        chart_data = {}
        for sm in metrics:
            subj_rows.append({
                "Difficulty Rank": f"#{sm.difficulty_rank}",
                "Subject": sm.subject_name,
                "Max Marks": sm.max_marks,
                "Average Score": sm.average_score,
                "Average (%)": f"{sm.average_percentage:.1f}%",
                "Pass Rate (%)": f"{sm.pass_percentage:.1f}%",
                "Passed": sm.pass_count,
                "Failed": sm.fail_count,
                "Min Score": sm.lowest_score,
                "Max Score": sm.highest_score,
            })
            chart_data[sm.subject_name] = sm.pass_percentage

        st.dataframe(pd.DataFrame(subj_rows), hide_index=True, use_container_width=True)
        st.caption("*(Difficulty Rank #1 indicates the most challenging subject based on pass rate and average score)*")

        st.subheader("Subject Pass Rate Comparison")
        st.bar_chart(chart_data)


# -----------------------------------------------------------------------------
# TAB 5: STUDENT EXPLORER
# -----------------------------------------------------------------------------
with tabs[4]:
    if st.session_state.evaluated_df is None:
        st.info("Please upload a dataset and run the analysis in the 'Upload & Configure' tab.")
    else:
        df_eval = st.session_state.evaluated_df
        st.header("Student Records Explorer")

        # Filters
        f1, f2, f3 = st.columns(3)
        with f1:
            search_query = st.text_input("🔍 Search by Student Name or ID", "")
        with f2:
            dept_filter = st.selectbox(
                "Filter by Department",
                options=["All"] + sorted(list(df_eval["department"].unique())),
            )
        with f3:
            status_filter = st.selectbox(
                "Filter by Pass/Fail Status",
                options=["All", "PASS", "FAIL"],
            )

        # Apply Filters
        filtered = df_eval.copy()
        if search_query:
            query = search_query.lower()
            filtered = filtered[
                filtered["student_name"].str.lower().str.contains(query) |
                filtered["student_id"].str.lower().str.contains(query)
            ]
        if dept_filter != "All":
            filtered = filtered[filtered["department"] == dept_filter]
        if status_filter != "All":
            filtered = filtered[filtered["status"] == status_filter]

        st.caption(f"Showing **{len(filtered)}** of **{len(df_eval)}** records")
        st.dataframe(filtered, hide_index=True, use_container_width=True)


# -----------------------------------------------------------------------------
# TAB 6: ACADEMIC ATTENTION
# -----------------------------------------------------------------------------
with tabs[5]:
    if st.session_state.evaluated_df is None:
        st.info("Please upload a dataset and run the analysis in the 'Upload & Configure' tab.")
    else:
        attention = st.session_state.attention_students
        st.header(f"Academic Attention Indicators ({len(attention)} Flagged)")
        st.markdown("""
        These indicators use **transparent, rule-based heuristics** to surface students who need academic 
        or attendance support. They are not black-box machine learning predictions.
        """)

        if not attention:
            st.success("🎉 No students currently flagged under academic attention heuristics.")
        else:
            for s in attention:
                with st.expander(f"⚠️ [{s.category.upper()}] {s.student_name} ({s.student_id}) — Score: {s.percentage:.1f}% | Attendance: {s.attendance:.1f}%"):
                    st.write(f"**Department / Section:** {s.department}")
                    st.write(f"**Diagnostic Rationale:** {s.rationale}")
                    st.info(f"**Recommended Action:** {s.action_item}")


# -----------------------------------------------------------------------------
# TAB 7: REPORTS & EXPORT
# -----------------------------------------------------------------------------
with tabs[6]:
    if st.session_state.evaluated_df is None:
        st.info("Please upload a dataset and run the analysis in the 'Upload & Configure' tab.")
    else:
        df_eval = st.session_state.evaluated_df
        summary = st.session_state.class_summary
        metrics = st.session_state.subject_metrics
        attention = st.session_state.attention_students
        policy = st.session_state.policy

        st.header("Download Academic Reports & Evaluated Data")

        exp1, exp2 = st.columns(2)

        with exp1:
            st.subheader("1. Sanitized Analyzed CSV")
            st.markdown("""
            - Contains full calculated fields: Totals, Normalization %, Letter Grades, Pass/Fail, Failure Diagnostics.
            - **Formula Injection Sanitized:** Prepends single quotes to formula triggers (`=`, `+`, `-`, `@`) to protect educators opening files in Microsoft Excel or Apple Numbers.
            """)
            csv_bytes = generate_sanitized_csv(df_eval)
            st.download_button(
                label="⬇️ Download Sanitized CSV",
                data=csv_bytes,
                file_name=f"edumetrics_evaluated_{st.session_state.dataset_name}",
                mime="text/csv",
                use_container_width=True,
            )

        with exp2:
            st.subheader("2. Summary Text Audit Report")
            st.markdown("""
            - Structured ASCII summary including class statistics, applied policy snapshot, subject difficulty ranking, and attention flags.
            - Suitable for archiving or appending to institutional records.
            """)
            text_rep = generate_text_summary(
                class_summary=summary,
                subject_metrics=metrics,
                attention_students=attention,
                policy=policy,
                dataset_name=st.session_state.dataset_name,
                institution_metadata=st.session_state.institution_metadata,
            )
            st.download_button(
                label="⬇️ Download Summary Text Report",
                data=text_rep.encode("utf-8"),
                file_name=f"edumetrics_summary_{st.session_state.dataset_name}.txt",
                mime="text/plain",
                use_container_width=True,
            )

        st.markdown("---")
        st.subheader("Report Preview")
        st.text(text_rep)


# -----------------------------------------------------------------------------
# TAB 8: HELP & METHODOLOGY
# -----------------------------------------------------------------------------
with tabs[7]:
    st.header("System Methodology & Academic Principles")

    st.markdown("""
    ### 1. Proportional Percentage Normalization
    When courses have heterogeneous maximum marks (e.g. 100-mark theory vs 50-mark lab), scores are normalized proportionally:
    $$\\text{Normalized Percentage} = \\left( \\frac{\\sum \\text{Marks Obtained}}{\\sum \\text{Maximum Possible Marks}} \\right) \\times 100$$
    
    ### 2. Dual-Layer Pass/Fail Rule
    A student earns an overall **PASS** if and only if:
    1. Their score in *each* individual subject meets or exceeds the subject passing threshold (default: 40%).
    2. Their normalized overall percentage meets or exceeds the aggregate passing threshold (default: 40%).
    
    If either condition fails, the diagnostic record specifies the exact failed courses.

    ### 3. CSV Formula Injection Defense (CWE-1236)
    Spreadsheet software (Microsoft Excel, LibreOffice Calc, Apple Numbers) can execute arbitrary code if untrusted cells begin with formula control characters:
    `=`, `+`, `-`, `@`, `\\t`, `\\r`.
    EduMetrics defuses all such strings upon export by prepending a single quote (`'`), ensuring spreadsheet applications display the text literally without execution.

    ### 4. Ephemeral Zero-Storage Privacy Architecture
    EduMetrics V1 does not persist records to a database, persistent disk, or remote storage. Uploaded data is processed in transient server memory scoped to the active user session. Active session references are cleared on reset or session termination, allowing memory to be reclaimed by runtime garbage collection.
    """)
