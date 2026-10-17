# EduMetrics — Complete User Guide 📖
### Comprehensive Manual for Educators, Administrators, and Academic Coordinators

**Platform Version:** V1.0.0  
**Target Audiences:** School Teachers, College Professors, Academic Coordinators, Teaching Assistants, Exam Officers  

---

## 📑 Table of Contents
1. [Overview & Core Philosophy](#1-overview--core-philosophy)
2. [Data Preparation & CSV Specifications](#2-data-preparation--csv-specifications)
3. [Interactive Web Dashboard Guide](#3-interactive-web-dashboard-guide)
   - [Tab 1: Overview & Samples](#tab-1-overview--samples)
   - [Tab 2: Ingestion & Configuration (7-Section Workflow)](#tab-2-ingestion--configuration-7-section-workflow)
   - [Tab 3: Academic Performance Dashboard](#tab-3-academic-performance-dashboard)
   - [Tab 4: Subject Analytics & Difficulty Rankings](#tab-4-subject-analytics--difficulty-rankings)
   - [Tab 5: Student Explorer & Filter](#tab-5-student-explorer--filter)
   - [Tab 6: Academic Attention Indicators](#tab-6-academic-attention-indicators)
   - [Tab 7: Reports & Export](#tab-7-reports--export)
   - [Tab 8: Help & Methodology](#tab-8-help--methodology)
4. [Standalone CLI Execution Guide](#4-standalone-cli-execution-guide)
5. [Understanding Academic Attention Heuristics](#5-understanding-academic-attention-heuristics)
6. [Data Privacy, Security & Formula Injection Defense](#6-data-privacy-security--formula-injection-defense)
7. [Frequently Asked Questions (FAQ)](#7-frequently-asked-questions-faq)

---

## 1. Overview & Core Philosophy

EduMetrics was built to bridge the gap between error-prone manual spreadsheets and complex, heavyweight Enterprise Resource Planning (ERP) systems. 

Key design principles:
- **Zero Installation Barrier:** Runs cleanly in modern web browsers or headlessly in terminal environments.
- **Academic Precision:** Evaluates scores without premature rounding artifacts, correctly handles courses with different maximum marks, and enforces independent subject pass thresholds.
- **Privacy by Design:** Requires no user accounts, passwords, or persistent cloud databases in V1. Your data is analyzed in ephemeral session memory and cleared on reset.
- **Defensive Export:** Defuses spreadsheet formula injections (CWE-1236) to safeguard educators opening CSV exports in Microsoft Excel, Apple Numbers, or LibreOffice.

---

## 2. Data Preparation & CSV Specifications

EduMetrics accepts standard comma-separated values (`.csv`) files.

### 2.1 Required Columns
Your CSV file must include columns representing:
1. **Student Identifier:** A unique student roll number, registration ID, or code (e.g. `SCH-101`, `001`). Leading zeros are strictly preserved.
2. **Student Name:** Official student full name. Supports international Unicode characters, accented letters, hyphens, and apostrophes.
3. **Attendance Percentage:** Attendance numeric value between `0.0` and `100.0`. Trailing `%` signs are automatically handled.
4. **Academic Course Columns:** One or more numeric columns representing scores achieved in subjects (e.g. `English`, `Mathematics`, `Data_Structures`, `Physics_Lab`).

### 2.2 Optional Columns
- **Department / Section:** Grouping cohort (e.g. `Section A`, `Section B`, `CSE`, `ECE`).

### 2.3 Special Values & Marks Rules
- **Explicit Absence:** If a student was absent from an examination, record their score as `ABS` or `ABSENT`. The system treats this as 0 marks for percentage calculations while clearly recording an official examination absence in failure diagnostics.
- **Non-Numeric / Empty Cells:** Blank cells are **not permitted** in subject columns. Enter a valid numerical score or `ABS`/`ABSENT`.
- **Score Limits:** Every mark must be between `0.0` and the configured Maximum Mark for that subject (default: 100 for theory, 50 for lab).
- **Prohibited Characters:** Unprintable control characters and dangerous Unicode bidirectional overrides (`\u202e` etc.) are automatically rejected for security.

---

## 3. Interactive Web Dashboard Guide

Launch the web app with:
```bash
streamlit run app.py
```
Then navigate through the 8 tabs described below:

### Tab 1: Overview & Samples
- Read the system summary and active privacy advisory.
- Download the built-in reference CSV templates:
  - **Sample 1 (K-12 School Model):** 20 students, uniform 100-mark scoring scale.
  - **Sample 2 (University Engineering Model):** 25 students, leading-zero IDs (`"001"`), mixed 100-mark theory and 50-mark lab courses.

### Tab 2: Ingestion & Configuration (7-Section Workflow)
This is your primary configuration workspace. It is structured into 7 logical sections:

1. **Section 1 — Institution Details:** (Optional) Enter your institution name, academic level (School, College, University, Other), program or class name, and semester/term.
2. **Section 2 — Column Mapping:** The system automatically inspects your CSV headers and recommends mappings for Student ID, Name, Attendance, and Department. Confirm or adjust these selections.
3. **Section 3 — Subject Configuration:** Select which course columns to include in the evaluation. Specify the maximum achievable marks for each course (e.g. 100 for theory, 50 for lab). If different courses have different pass cutoffs, check **"Configure subject-specific passing thresholds"**.
4. **Section 4 — Grading Policy:**
   - Set the default **Subject Passing Threshold (%)** (default: 40%).
   - Set the **Aggregate Passing Threshold (%)** (default: 40%).
   - Select an institutional preset (`Default EduMetrics`, `Example School`, `Example College`) or customize grade labels and minimum percentages directly.
   - Use **"➕ Add Grade Level"** or **"➖ Remove Grade Level"** to adjust the number of tiers (supports 2 to 12 levels).
5. **Section 5 — Attendance Policy:**
   - Configure the attendance shortage threshold (default: `< 75%`).
   - Toggle the warning indicator on or off. Note: Attendance warnings are pastoral advisories and do not cause course failure.
6. **Section 6 — Policy Preview:** Live summary table displaying all active grade brackets, score ranges, and passing criteria before running calculations.
7. **Section 7 — Run Analysis:**
   - Click **"🚀 Run Academic Analysis"** to validate records and execute the analytics engine.
   - Any modification to column mappings or grading settings marks active analysis stale to guarantee data integrity.

### Tab 3: Academic Performance Dashboard
- **Top Metric Cards:** Instant view of Total Enrolled, Overall Pass Rate, Class Average Score, Class Median Score, Mean Attendance, Attendance Shortages, and Class Topper.
- **Grade Distribution Chart:** Interactive bar chart displaying the frequency of each assigned letter grade.
- **Statistical Overview:** Detailed table with variance, standard deviation, and highest/lowest score records.
- **Top Performers Leaderboard:** Deterministic top 5 ranking with multi-key tie breaking (Percentage $\rightarrow$ Attendance $\rightarrow$ Student ID).

### Tab 4: Subject Analytics & Difficulty Rankings
- Ranked table showing every course's difficulty rank:
  - Rank #1 identifies the most challenging subject based on pass rate and class average.
  - Displays Max Marks, Average Score, Average Percentage, Pass Rate, Pass/Fail Counts, and Score Range.
- Comparative subject pass rate visualization.

### Tab 5: Student Explorer & Filter
- Search individual student records by Student Name or Student ID.
- Special punctuation characters (e.g. `[`, `(`, `-`) are handled safely without search crashes.
- Filter by Department/Section or Pass/Fail status.

### Tab 6: Academic Attention Indicators
Surfaces students requiring early intervention using transparent, rule-based heuristics:
- **Conceptual Support Needed:** High attendance ($\ge 85\%$) but low score ($< 50\%$).
- **Critical Intervention:** Chronic absenteeism ($< 75\%$) compounded by academic failure ($< 50\%$).
- **Subject-Specific Remediation:** Failed in exactly 1 course while maintaining an average $\ge 65\%$ across all other courses.
- **Borderline / At-Risk:** Passing, but within 5 percentage points of failure.

### Tab 7: Reports & Export
- **Sanitized CSV Download:** Complete evaluated dataset including calculated totals, normalized percentages, letter grades, pass/fail statuses, and failure diagnostic messages. Every text field is protected against formula execution (CWE-1236).
- **Summary Text Audit Report:** Formatted ASCII summary document containing institution metadata, applied policy snapshot, class statistics, and attention flags.

### Tab 8: Help & Methodology
- Complete mathematical definitions of proportional normalization, the dual-layer passing rule, formula injection defusion, and privacy boundaries.

---

## 4. Standalone CLI Execution Guide

For automated batch processing or headless servers:

```bash
# 1. Run basic analysis on sample dataset
python main.py --file data/sample_school.csv

# 2. Run with institutional metadata and export evaluated report
python main.py --file data/sample_college.csv \
  --institution "Kendriya Vidyalaya" \
  --level "School" \
  --program "Class 10-A" \
  --term "Annual 2026" \
  --top 5 \
  --export evaluated_report.csv

# 3. Apply custom grade boundaries and subject pass overrides
python main.py --file data/sample_school.csv \
  --grade-boundaries "Distinction:85,First:65,Second:50,Pass:40,Fail:0" \
  --subject-pass-overrides "Mathematics:50,Science:45"
```

### CLI Arguments Summary
| Flag | Description | Default |
| :--- | :--- | :--- |
| `--file`, `-f` | Path to CSV marks dataset | `data/sample_school.csv` |
| `--id-col` | Student ID column name | `student_id` |
| `--name-col` | Student Name column name | `student_name` |
| `--attendance-col` | Attendance percentage column name | `attendance` |
| `--dept-col` | Department/Section column name | `department` |
| `--subject-pass` | Default minimum % to pass individual course | `40.0` |
| `--aggregate-pass`| Minimum aggregate % required to pass cohort | `40.0` |
| `--attendance-warning` | Attendance % cutoff for warning alert | `75.0` |
| `--disable-attendance-warning` | Disable attendance warnings | `False` |
| `--preset` | Grading scale preset (`Default`, `School`, `College`) | `None` |
| `--grade-boundaries` | Custom grade thresholds (`G:MIN_PCT,...`) | `None` |
| `--subject-pass-overrides` | Per-subject cutoffs (`SUBJ:PCT,...`) | `None` |
| `--institution` | Institution name string | `""` |
| `--level` | Academic level (`School`, `College`, `University`, `Other`) | `""` |
| `--program` | Class or program name | `""` |
| `--term` | Term or semester name | `""` |
| `--top` | Number of top performers to display | `5` |
| `--export`, `-e` | File path to export sanitized CSV | `None` |

---

## 5. Understanding Academic Attention Heuristics

Traditional gradebooks merely display a failing grade at the end of the term. EduMetrics categorizes struggling students into actionable intervention archetypes:

```
+-----------------------------------------------------------------------------------+
|                        Academic Attention Framework                               |
+-----------------------------------------------------------------------------------+
| Category               | Criterion                      | Recommended Action      |
+------------------------+--------------------------------+-------------------------+
| Conceptual Support     | Attendance >= 85%, Score < 50% | 1-on-1 concept tutoring |
| Critical Intervention  | Attendance < 75%, Score < 50%  | Parent/pastoral meeting |
| Subject Remediation    | Failed 1 course, rest >= 65%   | Course-specific modules |
| Borderline / At-Risk   | Passed, but within 5% of cut   | Weekly progress review  |
+-----------------------------------------------------------------------------------+
```

---

## 6. Data Privacy, Security & Formula Injection Defense

### 6.1 Ephemeral Memory Model
EduMetrics V1 operates in transient server memory. Resetting your session removes all in-memory references, allowing the Python garbage collector to reclaim RAM. The application creates no background database records.

### 6.2 Formula Injection Defense (CWE-1236)
When exporting student records to CSV, untrusted inputs (e.g. student names or IDs) could contain spreadsheet formulas:
`=cmd|'/C calc'!A0` or `+SUM(A1:A10)` or `@HYPERLINK(...)`

If an educator opens an unescaped CSV in Microsoft Excel, Apple Numbers, or LibreOffice Calc, the spreadsheet software may execute the formula or execute remote commands.

**EduMetrics Defense:** All exported string cells beginning with `=`, `+`, `-`, `@`, `\t`, `\r`, or `%` (even with preceding whitespace like `"   =1+1"`) are safely defused by prepending an apostrophe (`'`). Spreadsheet engines display the content strictly as literal text.

---

## 7. Frequently Asked Questions (FAQ)

### Q: Why did my analysis disappear when I changed a grade boundary?
**A:** EduMetrics enforces **session state integrity**. If you modify grade boundaries, subject pass thresholds, or maximum marks after computing analysis, the previous results are mathematically invalid under your new rules. The system marks the analysis stale and requires you to click **"🚀 Run Academic Analysis"** to generate updated, consistent metrics.

### Q: Can a student pass if they have 90% overall but failed one subject?
**A:** Under standard institutional rules, **No**. EduMetrics uses a **Dual-Layer Pass/Fail Rule**: a student must pass *every* enrolled subject in addition to achieving the aggregate passing threshold. If a student fails one subject, their status is `FAIL` with a diagnostic reason (e.g. `"Failed in: Mathematics"`), even if their overall average is high.

### Q: Does low attendance automatically fail a student?
**A:** No. Attendance is treated as an administrative and pastoral indicator. An attendance shortage triggers an alert in the summary metrics and student record, but does not cause academic course failure unless an institution specifically sets an academic pass cutoff reflecting it.

### Q: How do I export an official report?
**A:** Navigate to the **"Reports & Export"** tab. Click **"⬇️ Download Sanitized CSV"** for complete tabular records, or **"⬇️ Download Summary Text Report"** for an audit-ready text report including your institution metadata.
