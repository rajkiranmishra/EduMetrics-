# EduMetrics 🎓
### Academic Performance Analytics Platform

[![EduMetrics CI](https://github.com/rajkiranmishra/edumetrics/actions/workflows/ci.yml/badge.svg)](https://github.com/rajkiranmishra/edumetrics/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Tests: 116 Passed](https://img.shields.io/badge/Tests-116%20Passed-success.svg)](docs/TEST_REPORT.md)

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
git clone https://github.com/rajkiranmishra/edumetrics.git
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

### Web Workflow & Configuration Layout:
1. **Overview & Samples:** Read the privacy notice and download sample CSV templates.
2. **Upload & Configure:** Upload your CSV (or load a sample with 1 click). Configuration is structured into 7 clean sections:
   - **Section 1 — Institution Details:** (Optional) Institution name, academic level (School/College/University/Other), program name, and academic term.
   - **Section 2 — Column Mapping:** Map Student ID, Name, Department, and Attendance columns.
   - **Section 3 — Subject Configuration:** Detects subjects dynamically, allows setting custom maximum marks (e.g. 100 for theory, 50 for lab) and optional per-subject passing thresholds.
   - **Section 4 — Grading Policy:** Choose an institutional preset (`Default EduMetrics`, `Example School`, `Example College`) or customize boundaries. Add or remove grade tiers (2 to 12) with real-time validation.
   - **Section 5 — Attendance Policy:** Configure the warning threshold percentage and toggle attendance warning indicators on/off.
   - **Section 6 — Policy Preview:** Live summary card displaying active grade tiers, pass thresholds, and warning rules before running analysis.
   - **Section 7 — Run Analysis:** Validates and executes calculations. Any change to settings automatically marks results stale to ensure integrity.
3. **Performance Dashboard:** View class averages, pass rates, grade distribution charts, and leaderboards.
4. **Subject Analysis:** Inspect pass rates, averages, and difficulty rankings per subject.
5. **Student Explorer:** Search, filter, and sort student-level performance records.
6. **Academic Attention:** Review students flagged for conceptual tutoring, chronic absenteeism, or subject remediation.
7. **Reports & Export:** Download sanitized CSV reports (with formula defusion) and comprehensive text summaries containing institutional metadata.
8. **Reset Session:** Click "Start New Analysis / Reset" to clear all session memory.

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

- **CWE-1236 Formula Injection Defense:** All exported text cells starting with `=`, `+`, `-`, `@`, `\t`, or `\r` are neutralized by prepending a single quote (`'`), protecting educators opening files in Microsoft Excel or Apple Numbers.
- **Resource Limits:** Hard caps of 2 MB file size, 5,000 rows, and 30 columns prevent memory exhaustion DoS attacks.
- **Binary Rejection:** Null bytes and binary executable magic headers are rejected before parsing.
- **Zero Disk Retention:** Uploaded student data lives strictly within volatile session memory.

---

## 🧪 Automated Testing

EduMetrics includes a comprehensive test suite of **116 automated tests** covering all modules:

```bash
pytest -v
```

```
============================== test session starts ==============================
collected 116 items

tests/test_analytics.py .......                                           [  6%]
tests/test_grading.py ..............................................      [ 45%]
tests/test_loader.py .............                                        [ 56%]
tests/test_reports.py ..                                                  [ 58%]
tests/test_security.py .....                                              [ 62%]
tests/test_sessions.py ............................                       [ 87%]
tests/test_validation.py ...............                                  [100%]

============================== 116 passed in 1.85s ==============================
```

---

## 📚 Project Documentation Index

- [SRS.md](docs/SRS.md) — Comprehensive Software Requirements Specification.
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — Component diagrams, data flow, and future relational DB schema.
- [SECURITY.md](docs/SECURITY.md) — Threat model (STRIDE), trust boundaries, and vulnerability reporting.
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
