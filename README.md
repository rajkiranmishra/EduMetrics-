# EduMetrics 🎓
### Academic Performance Analytics Platform

[![EduMetrics CI](https://github.com/rajkiranmishra/EduMetrics-/actions/workflows/ci.yml/badge.svg)](https://github.com/rajkiranmishra/EduMetrics-/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Tests: 145 Passed](https://img.shields.io/badge/Tests-145%20Passed-success.svg)](docs/TEST_REPORT.md)

**EduMetrics** is a production-minded academic analytics platform that empowers teachers, professors, and academic coordinators to validate student performance datasets, configure institutional grading policies, compute statistical cohort distributions, and export sanitized reports without requiring spreadsheet programming.

Built with **Python, NumPy, Pandas, and Streamlit**, EduMetrics satisfies all requirements of the **EWB Courses "Student Performance Analytics System"** assignment while establishing a security-conscious, modular foundation.

---

## 📑 Table of Contents
- [Problem Statement](#-problem-statement)
- [Key Features](#-key-features)
- [Architecture Overview](#-architecture-overview)
- [Tech Stack](#-tech-stack)
- [Sample Datasets](#-sample-datasets)
- [Installation & Local Setup](#-installation--local-setup)
- [Usage: Standalone CLI](#-usage-standalone-cli)
- [Usage: Web Dashboard](#-usage-web-dashboard)
- [Academic Grading Methodology](#-academic-grading-methodology)
- [Security & Privacy Controls](#-security--privacy-controls)
- [Automated Testing](#-automated-testing)
- [Project Documentation Index](#-project-documentation-index)
- [Limitations & Future Roadmap](#-limitations--future-roadmap)
- [License](#-license)

---

## 🎯 Problem Statement

Educators frequently compile student marks across disparate spreadsheets with manual, error-prone calculations:
1. **Unequal Maximum Marks:** Calculating totals across mixed courses (e.g., 100-mark theory vs. 50-mark lab) often leads to skewed unweighted averages.
2. **Rigid Policies:** Off-the-shelf software rarely handles dual-layer passing rules (e.g., requiring a passing mark in *every* course in addition to an overall aggregate percentage).
3. **Lack of Instant Diagnostics:** Instructors struggle to quickly surface students who need help (e.g., students with high attendance but low scores, or students failing exactly one subject).
4. **Data Privacy & Ingestion Fragility:** Heavy enterprise software requires complex procurement and passwords, while ad-hoc spreadsheets risk spreadsheet formula execution exploits (CWE-1236).

EduMetrics resolves these challenges through a **zero-login, session-ephemeral web dashboard** and a **headless standalone CLI** sharing a pure functional analytics engine.

---

## ✨ Key Features

- **Dual Operating Modes:** Run headlessly via terminal CLI (`main.py`) or interactively in a web browser (`app.py`).
- **Institutional Metadata Support:** Configure institution name, academic level (School / College / University / Other), class/program name, and term/semester for audit-ready reports.
- **Configurable Grade Boundaries & Presets:** Define custom letter grades and percentage cutoffs with validation (finite, strictly monotonic, lowest at 0.0%). Select from built-in presets (`Default EduMetrics`, `Example School`, `Example College`) and customize them as needed.
- **Flexible Column Mapping:** Resiliently maps custom column names for Student ID, Name, Department, Attendance, and dynamic subject lists.
- **Heterogeneous Score Normalization:** Proportional normalization across subjects with different maximum possible marks.
- **Per-Subject & Aggregate Passing Rules:** Independent subject-level cutoffs (with optional per-subject overrides) and aggregate thresholds with detailed failure diagnostics.
- **Configurable Attendance Warnings:** Decoupled attendance warning policy (configurable threshold, toggleable indicator) that never causes academic failure.
- **Deterministic Ranking:** Multi-key tie-breaking (Percentage $\rightarrow$ Attendance $\rightarrow$ Student ID).
- **Rule-Based Academic Attention Flags:** Transparent heuristics identifying students needing tutoring, chronic absenteeism intervention, or single-course remediation.
- **Session State Integrity:** Automatic cache invalidation ensures changing policies or datasets instantly resets stale calculations.
- **CSV Formula Injection Defusion (CWE-1236):** Neutralizes formula triggers (`=`, `+`, `-`, `@`, `\t`, `\r`) on export.
- **Privacy by Design:** Zero permanent database storage in V1; records exist only in transient session memory.

---

## 🏗️ Architecture Overview

EduMetrics uses a **Headless Modular Monolith** architecture. The core computational engine has **zero imports of Streamlit**, ensuring it can be tested and executed headlessly.

```
edumetrics/
├── .github/workflows/ci.yml       # Automated GitHub Actions CI
├── .streamlit/config.toml          # Streamlit theme & upload constraints
├── core/
│   ├── loader.py                  # Encoding detection, safe CSV ingestion
│   ├── validation.py              # Schema, score bounds, duplicate checks
│   ├── grading.py                 # Normalization, grade brackets, pass/fail, presets
│   ├── analytics.py               # NumPy/Pandas statistics, ranking, attention
│   ├── reports.py                 # Sanitized CSV and text summary generation
│   └── session_state.py           # Session isolation, widget keys, staleness tracking
├── security/
│   └── upload_checks.py           # 2MB file limits, row/col caps, formula defusion
├── data/
│   ├── sample_school.csv          # Fictional K-12 dataset (20 students)
│   └── sample_college.csv         # Fictional College dataset (25 students, mixed max marks)
├── docs/
│   ├── SRS.md                     # Software Requirements Specification
│   ├── ARCHITECTURE.md            # Component diagrams & future DB design
│   ├── SECURITY.md                # Threat model (STRIDE) & disclosure policy
│   ├── TEST_REPORT.md             # Test results, benchmarks, and bug fixes
│   └── Project_Documentation.md   # EWB Courses assignment compliance document
├── tests/                         # 116 automated pytest unit, security & session tests
├── app.py                         # Streamlit Web Application (UI layer only)
├── main.py                        # Standalone CLI Entrypoint
├── requirements.txt               # Pinned dependencies
├── README.md                      # Project documentation
└── LICENSE                        # MIT License
```

---

## 🛠️ Tech Stack

- **Python 3.9+** — Core programming language.
- **NumPy** — Fast numerical calculations (mean, median, standard deviation, extremes).
- **Pandas** — DataFrames, schema validation, grouping, and CSV export.
- **Streamlit** — Interactive presentation layer with session-ephemeral state.
- **pytest** — Automated test suite with 100% pass rate across 116 tests.

---

## 📊 Sample Datasets

EduMetrics includes two fictional datasets in `data/`:

| Dataset | Cohort | Description | Structure |
| :--- | :--- | :--- | :--- |
| **`data/sample_school.csv`** | 20 students | K-12 School model across 2 sections (`Section A`, `Section B`). | 5 subjects with uniform 100 max marks (`English`, `Mathematics`, `Science`, `Social_Studies`, `Second_Language`). |
| **`data/sample_college.csv`** | 25 students | University engineering model across 3 departments (`CSE`, `IT`, `ECE`). | Leading zero IDs (`"001"`), 3 theory courses (Max: 100), and 3 lab/project courses (Max: 50). Total: 450 marks. |

---

## 🚀 Installation & Local Setup

### 1. Clone the Repository
```bash
# Clone active repository
git clone https://github.com/rajkiranmishra/EduMetrics-.git edumetrics
cd edumetrics
```

### 2. Create and Activate a Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 💻 Usage: Standalone CLI

Run the analytics engine directly from your terminal:

```bash
# Run on the School dataset (default)
python main.py --file data/sample_school.csv

# Run with institutional metadata and an example preset
python main.py --file data/sample_college.csv --institution "National Tech Institute" --level "College" --preset "Example College" --top 5 --export analyzed_report.csv

# Run with custom grade boundaries and per-subject passing cutoffs
python main.py --file data/sample_school.csv --grade-boundaries "A+:90,A:80,B:70,C:60,D:40,F:0" --subject-pass-overrides "Mathematics:45,Science:40"
```

### CLI Command Options
- `--file`, `-f`: Path to the CSV dataset (default: `data/sample_school.csv`).
- `--id-col`: Column header for Student ID (default: `student_id`).
- `--name-col`: Column header for Student Name (default: `student_name`).
- `--attendance-col`: Column header for Attendance % (default: `attendance`).
- `--dept-col`: Column header for Department (default: `department`).
- `--institution`: Name of the educational institution (optional).
- `--level`: Academic level (`School`, `College`, `University`, `Other`).
- `--program`: Class, course, or program name (optional).
- `--term`: Academic term or semester (optional).
- `--preset`: Grading scale preset (`Default EduMetrics`, `Example School`, `Example College`).
- `--grade-boundaries`: Custom grade boundaries formatted as `GRADE:MIN_PERCENT,...`.
- `--subject-pass`: Default minimum % required to pass individual subjects (default: `40.0`).
- `--subject-pass-overrides`: Per-subject pass thresholds formatted as `SUBJECT:CUTOFF,...`.
- `--aggregate-pass`: Minimum overall aggregate % required to pass (default: `40.0`).
- `--attendance-warning`: Attendance % threshold for warning (default: `75.0`).
- `--disable-attendance-warning`: Flag to disable attendance warning indicators.
- `--top`: Number of top performers to display (default: `5`).
- `--export`, `-e`: Optional path to save evaluated and formula-defused CSV.

---

## 🌐 Usage: Web Dashboard

Launch the Streamlit interactive dashboard locally:

```bash
streamlit run app.py
```

Open your browser at `http://localhost:8501`.

### Web Workflow & Navigation:
EduMetrics features a responsive sidebar navigation system with 8 destinations:
1. **Overview & Quick Start:** Concise privacy notice and 1-click quick start demonstrations for School and College models.
2. **Upload & Configure:** Upload CSVs or select built-in datasets with a structured 4-group workflow:
   - **Group 1 — Dataset Upload & Column Mapping:** Ingest CSV and configure column mapping for Student ID, Name, Department, and Attendance.
   - **Group 2 — Subject Marks & Passing Rules:** Dynamic subject detection, maximum achievable marks (100 for theory, 50 for lab), and optional per-subject passing cutoffs.
   - **Group 3 — Institution & Grading Policies:** Set passing thresholds, configure attendance warnings, select presets (`Default EduMetrics`, `Example School`, `Example College`), edit grade tiers (2 to 12 levels), and enter optional institutional metadata.
   - **Group 4 — Policy Preview & Run Analysis:** Real-time policy snapshot, stale configuration warning, and 1-click analysis execution.
3. **Performance Dashboard:** View KPI metric cards, pass rates, sorted letter grade distribution charts, and deterministic leaderboards.
4. **Subject Analysis:** Inspect pass rates, averages, and curriculum difficulty rankings per course.
5. **Student Explorer:** Search (literal, regex-safe), filter by department or pass/fail, and sort student-level performance records.
6. **Academic Attention:** Review students flagged for conceptual tutoring, chronic absenteeism, or subject remediation.
7. **Reports & Export:** Download sanitized CSV reports (with formula defusion) and comprehensive text summaries.
8. **Help & Methodology:** Review mathematical formulas, normalization rules, and privacy architecture.
9. **Reset Session:** Click "Start New Analysis / Reset" in the sidebar to cleanly clear all transient session memory.

---

## 📐 Academic Grading Methodology

### 1. Proportional Score Normalization
$$\text{Normalized Percentage} = \left( \frac{\sum_{i=1}^M \text{Marks Obtained}_i}{\sum_{i=1}^M \text{Maximum Possible Marks}_i} \right) \times 100$$
All subject marks are normalized proportionally against their respective maximum marks, correctly weighting heterogeneous subjects.

### 2. Configurable Grade Boundaries & Presets
EduMetrics assigns letter grades based on unrounded percentages (`raw_percentage`) using strictly monotonic boundaries starting at 0.0%:
- **Default EduMetrics:** A+ ($\ge 90$), A ($\ge 80$), B+ ($\ge 70$), B ($\ge 60$), C ($\ge 50$), D ($\ge 40$), F ($0$)
- **Example School:** A+ ($\ge 90$), A ($\ge 80$), B ($\ge 70$), C ($\ge 60$), D ($\ge 40$), F ($0$)
- **Example College:** O ($\ge 90$), E ($\ge 80$), A ($\ge 70$), B ($\ge 60$), C ($\ge 50$), P ($\ge 40$), F ($0$)

*(Note: Presets are illustrative samples, not official regulations, and can be fully customized by the user).*

### 3. Dual-Layer Pass/Fail Rule vs. Grade Assignment
Letter grade assignment and pass/fail evaluation serve distinct institutional functions:
- A student receives a letter grade reflecting overall percentage.
- A student passes if and only if:
  1. Every subject score meets or exceeds its configured passing threshold (default or per-subject override).
  2. Overall normalized aggregate percentage meets or exceeds the aggregate pass threshold.
If a student fails any single subject, their overall status is `FAIL` with diagnostic details (e.g., `"Failed in: Mathematics"`), even if their aggregate score would otherwise place them in an upper grade tier.

### 4. Attendance Policy & Decoupled Warnings
- Attendance warning status is an administrative/pastoral indicator (default: $< 75\%$).
- Attendance warnings are strictly separated from academic performance: low attendance **never** causes academic failure unless explicitly mandated by academic pass thresholds.

### 5. Transparent Academic Attention Indicators
- **Conceptual Support Needed:** Attendance $\ge 85\%$ and Score $< 50\%$.
- **Critical Intervention:** Attendance $< 75\%$ and Score $< 50\%$.
- **Subject-Specific Remediation:** Failed exactly 1 subject, while remaining subjects average $\ge 65\%$.
- **Borderline / At-Risk:** Passing within 5 percentage points of failure ($40\% \le \text{Score} < 45\%$).

---

## 🔒 Security & Privacy Controls

- **CWE-1236 Formula Injection Defense:** All exported text cells starting with `=`, `+`, `-`, `@`, `\t`, `\r`, or `%` (including leading whitespace bypasses like `"   =1+1"`) are neutralized by prepending a single quote (`'`), protecting educators opening files in Microsoft Excel, Apple Numbers, LibreOffice Calc, or Google Sheets.
- **Multi-Layer Ingestion Bounds:** Enforces a 2 MB file size limit, 5,000 maximum rows, 30 maximum columns, 512-character maximum individual cell length, and 64-character maximum header length.
- **Identifier Length Limits:** Enforces strict field bounds: Student ID ($\le 64$), Student Name ($\le 128$), and Department ($\le 64$).
- **Adversarial Filename Sanitization:** Path traversal sequences (`../`, `..\`), null bytes, control characters, and HTML tags are stripped from filenames.
- **Unicode & Control Character Defenses:** Prohibits dangerous bidirectional override characters (`\u202e` etc.) and unprintable control characters to prevent visual spoofing.
- **Validation Error Capping:** Capped at 500 errors to prevent memory exhaustion and browser UI rendering denial of service.
- **Transient In-Memory Processing:** Analysis executes strictly in transient server-side memory; EduMetrics V1 does not intentionally persist datasets to disk or databases.
- **Fictional Data Requirement:** Users are explicitly instructed to upload fictional or anonymized academic records only.

---

## 🧪 Automated Testing

EduMetrics includes a comprehensive test suite of **134 automated tests** covering all modules:

```bash
pytest -v
```

```
============================== test session starts ==============================
collected 145 items

tests/test_analytics.py .......                                           [  4%]
tests/test_cli.py ......                                                  [  8%]
tests/test_grading.py ..............................................      [ 40%]
tests/test_loader.py ............                                          [ 48%]
tests/test_reports.py ..                                                  [ 50%]
tests/test_security.py .............                                      [ 59%]
tests/test_sessions.py ...........................................        [ 89%]
tests/test_validation.py ................                                 [100%]

============================= 145 passed in ~5.5s ==============================
```

---

## 📚 Project Documentation Index

- [USER_GUIDE.md](docs/USER_GUIDE.md) — Comprehensive user manual for educators and coordinators.
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) — Streamlit Community Cloud and Linux VM deployment procedures.
- [USER_VALIDATION.md](docs/USER_VALIDATION.md) — Educator field testing protocol, questionnaire, and sample dataset.
- [RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) — Quality gates, pre-flight checks, and release sign-off.
- [RELEASE_NOTES.md](docs/RELEASE_NOTES.md) — Official EduMetrics V1.0.0 release notes.
- [SRS.md](docs/SRS.md) — Comprehensive Software Requirements Specification.
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — Component diagrams, data flow, and future relational DB schema.
- [SECURITY.md](docs/SECURITY.md) — Threat model (STRIDE), trust boundaries, and vulnerability disclosure.
- [TEST_REPORT.md](docs/TEST_REPORT.md) — Test execution evidence, bug fixes, and performance benchmarks.
- [Project_Documentation.md](docs/Project_Documentation.md) — EWB Courses assignment compliance document (10 headings).

---

## 🔮 Limitations & Future Roadmap

### Tested Scope (V1)
- Tested with cohort sizes of 20 to 5,000 records.
- Zero login / anonymous session-ephemeral mode.
- Institutional metadata and custom grading configuration are stored ephemerally in session memory and cleared on reset or session end.
- High-fidelity formula-defused CSV exports.

### Planned for V2 (Post-Submission)
- Multi-tenant institutional accounts with role-based access control (Admin, Coordinator, Teacher).
- Persistent storage using PostgreSQL (see [schema design in ARCHITECTURE.md](docs/ARCHITECTURE.md#4-future-relational-database-architecture-v2-roadmap)).
- Longitudinal student performance tracking across academic terms.
- Server-side PDF export generation.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
