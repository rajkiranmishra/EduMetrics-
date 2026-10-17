# EduMetrics V1.0.0 — Official Release Notes 🚀
### Academic Performance Analytics Platform

**Release Version:** V1.0.0  
**Target Date:** 26 October 2026  
**Status:** Pre-Release Candidate (Awaiting User Merge & Tagging Approval)  
**Target Git Tag:** `v1.0.0`  
**License:** MIT License  

---

## 🌟 Executive Summary

EduMetrics V1.0.0 is the inaugural production-ready release of the **EduMetrics Academic Performance Analytics Platform**. Built to fulfill and exceed all requirements of the **EWB Courses "Student Performance Analytics System"** assignment, EduMetrics provides a modular, privacy-first solution for educators, professors, and academic coordinators.

EduMetrics eliminates manual, error-prone spreadsheet calculations by providing a **headless Python CLI** and an **interactive Streamlit web dashboard** backed by pure NumPy and Pandas analytics.

---

## ✨ What's New in V1.0.0

### 1. Dual-Mode Analytics Architecture
- **Interactive Web Dashboard (`app.py`):** An intuitive Streamlit-native sidebar dashboard with 8 dedicated destinations, 1-click Quick Demos with full bidirectional configuration sync (UI-02.1), accessibility-compliant typography, responsive layouts, and zero-login ephemeral session memory.
- **Standalone Headless CLI (`main.py`):** A full-featured command-line utility for automated batch processing, scripting, and grading report generation without requiring a browser or web server.

### 2. Heterogeneous Course Scoring & Normalization
- Proportional percentage normalization across courses with unequal maximum marks (e.g. 100-mark theory vs. 50-mark lab/project courses):
  $$\text{Percentage} = \left( \frac{\sum \text{Marks Obtained}}{\sum \text{Maximum Marks}} \right) \times 100$$
- Unrounded floating-point calculations preserve numerical precision and eliminate rounding artifacts.

### 3. Configurable Institutional Grading Policies & Metadata
- **Institution Details:** Configure institution name, academic level (School, College, University, Other), class/program name, and term/semester for official audit reports.
- **Grading Scale Presets:** One-click application of sample presets (`Default EduMetrics`, `Example School`, `Example College`).
- **Dynamic Grade Boundary Editor:** Add, remove, or customize 2 to 12 grade tiers with real-time monotonicity and finite-number validation.
- **Independent Passing Rules:** Enforces a Dual-Layer Pass/Fail Rule requiring a passing mark in *every* subject (with optional per-subject overrides) as well as an aggregate passing threshold.
- **Decoupled Attendance Policy:** Configurable attendance warning cutoff (default: `< 75%`) with toggleable alert indicators that never cause academic failure.

### 4. Rule-Based Academic Attention Heuristics
- Transparent, explainable diagnostic flags identifying students needing targeted intervention:
  - **Conceptual Support Needed:** High attendance ($\ge 85\%$) but low score ($< 50\%$).
  - **Critical Intervention:** Chronic absenteeism ($< 75\%$) compounded by academic failure ($< 50\%$).
  - **Subject-Specific Remediation:** Failed in exactly 1 subject while averaging $\ge 65\%$ across all other courses.
  - **Borderline / At-Risk:** Passed, but within 5 percentage points of failing threshold.

### 5. Multi-Layer Security & CWE-1236 Defense
- **CSV Formula Injection Defusion:** Automatically prepends an apostrophe (`'`) to all exported spreadsheet cells starting with `=`, `+`, `-`, `@`, `\t`, `\r`, or `%` (including leading whitespace bypasses), neutralizing spreadsheet execution attacks in Microsoft Excel, Apple Numbers, and LibreOffice Calc.
- **Computational & Memory Bounds:** Enforces strict limits: 2 MB file size limit, 5,000 maximum rows, 30 maximum columns, 512-character cell lengths, and 64-character student identifiers.
- **Input Sanitization:** Rejects unprintable control characters, directory traversal sequences, and dangerous Unicode bidirectional override sequences (`\u202e` etc.).
- **Zero-Storage Privacy Architecture:** Processes datasets exclusively in ephemeral server-side RAM scoped to the active session; zero persistent database writes.

### 6. Session Integrity & Multi-Threaded Concurrency
- Centralized session state management automatically detects configuration staleness. Any change to datasets, column mappings, maximum marks, or grading thresholds invalidates active results to prevent data contamination.
- Concurrent session isolation verified across parallel worker threads.

---

## 🛠️ Verification & Test Metrics

- **Total Automated Tests:** **145 passed** (0 failed, 0 skipped) across 8 test suites.
- **Test Execution Time:** ~5.5 seconds.
- **Supported Python Runtimes:** Python 3.9, 3.10, 3.11.
- **Benchmark Datasets:**
  - `data/sample_school.csv`: 20 students, 5 subjects, uniform 100-mark scale.
  - `data/sample_college.csv`: 25 students, 6 subjects (3 theory, 3 lab/project), leading-zero IDs (`"001"`).

---

## 📦 Delivered Documentation

- `README.md`: High-level architecture, quick start, CLI options, and security index.
- `docs/DEPLOYMENT.md`: Step-by-step Streamlit Community Cloud and Linux VM deployment guide.
- `docs/USER_GUIDE.md`: Comprehensive educator manual covering web tabs, CLI, and FAQs.
- `docs/USER_VALIDATION.md`: Field testing package with synthetic dataset and educator questionnaire.
- `docs/RELEASE_CHECKLIST.md`: Formal verification gates and release evidence.
- `docs/SECURITY.md`: Comprehensive threat model (STRIDE), trust boundaries, and vulnerability disclosure.
- `docs/TEST_REPORT.md`: Granular test suite breakdown, benchmarks, and bugfix history.
- `docs/Project_Documentation.md`: EWB Courses assignment compliance document (10 required headings).
- `docs/SRS.md`: Complete Software Requirements Specification (functional and non-functional requirements).
- `docs/ARCHITECTURE.md`: Component diagrams, data flow specifications, and future relational database design.

---

## 🔮 Limitations & Future Roadmap (V2)

- **Identifiable Student Records:** EduMetrics V1 runs on public shared infrastructure and is approved only for fictional or de-identified academic data.
- **Persistent Multi-Tenancy:** Multi-user accounts with role-based access control (Admin, Teacher, Coordinator) and PostgreSQL persistence are scheduled for V2.0.
- **Report Card PDFs:** Formatted printable PDF exports with institutional crests are scheduled for V2.0.
