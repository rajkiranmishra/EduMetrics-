# EduMetrics — Educator User Validation Package 📝
### Practical Field Evaluation Protocol & Questionnaire for Academic Evaluators

**Status:** ⏳ **PENDING FIELD EVALUATION**  
*(Awaiting feedback from an external educator/professor. Zero synthetic testimonials or fabricated participant data have been recorded).*  
**Evaluation Target:** EduMetrics V1.0.0 Web Dashboard  
**Intended Participant:** Teacher, Teaching Assistant, Course Coordinator, or Professor  
**Estimated Time Commitment:** 10–15 minutes  

---

## 📑 Table of Contents
1. [Invitation Message (Ready to Send)](#1-invitation-message-ready-to-send)
2. [Included Fictional Validation Dataset](#2-included-fictional-validation-dataset)
3. [Step-by-Step Evaluation Protocol (Educator Tasks)](#3-step-by-step-evaluation-protocol-educator-tasks)
4. [Structured Educator Feedback Questionnaire](#4-structured-educator-feedback-questionnaire)
5. [Actual Feedback Log (To Be Completed by Participant)](#5-actual-feedback-log-to-be-completed-by-participant)
6. [Defect and Improvement Log](#6-defect-and-improvement-log)

---

## 1. Invitation Message (Ready to Send)

*Copy and send this message to a willing educator, teaching assistant, or professor:*

```text
Subject: Request for Feedback: EduMetrics Academic Analytics Demonstration (10-15 mins)

Dear [Professor / Teacher / Colleague Name],

As part of my final project for the EWB Courses "Student Performance Analytics System", I have developed EduMetrics—a lightweight, privacy-first web platform and CLI that helps educators validate marks spreadsheets, customize institutional grading policies, identify struggling students, and export audit-ready reports without requiring complex spreadsheet programming.

I would deeply appreciate your practical perspective as an educator. I have prepared an interactive demonstration that takes approximately 10 to 15 minutes to evaluate using fictional student marks (no real student data is involved).

App Link: [Insert Streamlit App URL or run locally via `streamlit run app.py`]
Validation Guide & Sample CSV: https://github.com/rajkiranmishra/EduMetrics-/blob/main/docs/USER_VALIDATION.md

The testing protocol involves 5 simple tasks:
1. Loading an academic dataset.
2. Customizing grading boundaries and pass marks.
3. Reviewing class statistics and difficulty rankings.
4. Reviewing rule-based academic attention flags.
5. Exporting a sanitized CSV and text summary report.

After testing, could you briefly answer the 6 short questions at the bottom of the guide? Your frank feedback on usability, grading flexibility, and report utility will directly shape the project submission and future roadmap.

Thank you very much for your time and guidance!

Warm regards,
Rajkiran Mishra
```

---

## 2. Included Fictional Validation Dataset

To ensure absolute privacy compliance (FERPA/GDPR), evaluators must test EduMetrics using **synthetic data only**.

Below is a dedicated 15-student validation dataset (`educator_validation_sample.csv`) designed to test edge cases:
- Mixed performance distribution (high performers, borderline passes, chronic absences, and single-subject failures).
- Explicit absence marker (`ABS`) in practical courses.
- Section cohorts (`Grade 11-A` and `Grade 11-B`).

```csv
student_id,student_name,department,attendance,Physics,Chemistry,Mathematics,Computer_Science
VAL-201,Aditi Sharma,Grade 11-A,96.0,92.0,88.0,95.0,98.0
VAL-202,Bikram Roy,Grade 11-A,84.0,76.0,81.0,72.0,79.0
VAL-203,Chetan Deshmukh,Grade 11-A,62.0,38.0,42.0,35.0,40.0
VAL-204,Deepa Nambiar,Grade 11-A,91.0,85.0,80.0,32.0,88.0
VAL-205,Eshan Guha,Grade 11-A,93.5,45.0,46.0,42.0,44.0
VAL-206,Fatima Sheikh,Grade 11-A,98.0,94.0,96.0,98.0,97.0
VAL-207,Girish Nair,Grade 11-A,70.0,41.0,38.0,40.0,42.0
VAL-208,Harini Swaminathan,Grade 11-B,95.0,89.0,91.0,94.0,92.0
VAL-209,Irfan Pathan,Grade 11-B,64.0,36.0,34.0,32.0,38.0
VAL-210,Jaspreet Kaur,Grade 11-B,88.0,72.0,75.0,70.0,74.0
VAL-211,Karan Mehra,Grade 11-B,89.0,78.0,34.0,80.0,82.0
VAL-212,Lata Subramanian,Grade 11-B,92.0,43.0,44.0,41.0,42.0
VAL-213,Mohammad Zafar,Grade 11-B,86.0,80.0,82.0,84.0,ABS
VAL-214,Nandita Sen,Grade 11-B,94.0,90.0,88.0,92.0,95.0
VAL-215,Ojasvi Varma,Grade 11-B,72.0,41.0,42.0,40.0,41.0
```

*Note: You can copy the block above into a plain text file named `validation_sample.csv`, or use the built-in **"Load Sample School Dataset"** button directly inside the app.*

---

## 3. Step-by-Step Evaluation Protocol (Educator Tasks)

Please follow these 5 tasks in the EduMetrics web application:

### Task 1: Dataset Loading & Column Mapping
1. Open the EduMetrics web dashboard.
2. In the **"Upload & Configure"** tab, upload `validation_sample.csv` (or click **"Load Sample School Dataset"**).
3. Verify that the system automatically detects:
   - Student ID: `student_id`
   - Student Name: `student_name`
   - Attendance: `attendance`
   - Department: `department`
   - Selected Subjects: `Physics`, `Chemistry`, `Mathematics`, `Computer_Science`.

### Task 2: Institution Metadata & Policy Customization
1. Expand **"🏫 Institution Metadata (Optional)"** and enter your school/college name and program (e.g. `Greenwood High`, `Grade 11`).
2. In **Section 3**, set `Computer_Science Max` to `100.0` and check **"Configure subject-specific passing thresholds"**. Set `Mathematics Pass Cut (%)` to `40.0%`.
3. In **Section 4**, review the letter grade boundaries. Try changing Grade 1 to `Distinction` or clicking **"➕ Add Grade Level"**.
4. In **Section 5**, confirm the attendance shortage warning is set to `< 75%`.

### Task 3: Running Analysis & Interpreting Dashboard
1. Click **"🚀 Run Academic Analysis"**.
2. Switch to the **"📊 Performance Dashboard"** tab:
   - Are the top summary cards (Total Students, Pass Rate, Class Average, Mean Attendance) intuitive?
   - Does the Letter Grade Distribution chart accurately represent the class?
   - Is the Top Performers Leaderboard clear?
3. Switch to the **"📚 Subject Analysis"** tab:
   - Does the difficulty ranking clearly convey which subject was the most challenging for the cohort?

### Task 4: Student Explorer & Attention Flags
1. Switch to the **"🔍 Student Explorer"** tab:
   - Search for a specific student (e.g. `Aditi` or `VAL-201`).
   - Try searching with special punctuation (e.g. `VAL-`). Verify the filter responds immediately without errors.
2. Switch to the **"⚠️ Academic Attention"** tab:
   - Review the rule-based categories:
     - *Conceptual Support Needed* (high attendance, low score).
     - *Critical Intervention* (low attendance and low score).
     - *Subject-Specific Remediation* (failed in exactly 1 course).
   - Are the diagnostic rationales and recommended action items practical for a real instructor?

### Task 5: Audit Reports & Session Reset
1. Switch to the **"📥 Reports & Export"** tab:
   - Click **"⬇️ Download Sanitized CSV"**. Open the downloaded CSV in Excel, Numbers, or Calc.
   - Click **"⬇️ Download Summary Text Report"**. Verify the text summary includes your institution metadata and applied policies.
2. In the left sidebar, click **"🔄 Start New Analysis / Reset"**.
   - Verify the session clears and returns to the initial state.

---

## 4. Structured Educator Feedback Questionnaire

Please rate each dimension on a scale of **1 to 5** and provide qualitative feedback:

| Dimension | Rating (1 = Poor, 5 = Excellent) | Evaluator Comments & Observations |
| :--- | :---: | :--- |
| **1. Ease of Use & Workflow** | *[Pending]* | *Is the 7-step layout intuitive for a non-technical teacher?* |
| **2. Grading Policy Flexibility** | *[Pending]* | *Are custom grade boundaries, presets, and per-subject cuts adequate for real-world grading?* |
| **3. Dashboard Clarity & Visuals** | *[Pending]* | *Are metric cards, charts, and tables easy to interpret at a glance?* |
| **4. Calculation Correctness** | *[Pending]* | *Did the percentage normalizations and pass/fail statuses align with your academic expectations?* |
| **5. Actionable Attention Flags** | *[Pending]* | *Are the academic attention heuristics helpful for identifying struggling students early?* |
| **6. Report & Export Utility** | *[Pending]* | *Is the sanitized CSV and ASCII audit report useful for institutional records?* |

---

## 5. Actual Feedback Log (To Be Completed by Participant)

*This section will be populated once the nominated educator completes the testing session.*

- **Evaluator Name / Role:** *[Pending Evaluation]*
- **Institution / Department:** *[Pending Evaluation]*
- **Evaluation Date:** *[Pending Evaluation]*
- **Evaluation Environment:** Localhost / Streamlit Community Cloud (Chrome / Safari / Firefox)
- **Overall Impression Score:** *[Pending / 5]*

### Evaluator's Qualitative Remarks:
> *[Pending educator's direct feedback submission]*

---

## 6. Defect and Improvement Log

| Issue ID | Category | Severity | Description | Action Item / Resolution | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DEF-01** | Student Search | Medium | Special regex characters (`[`, `(`, `*`) previously raised unhandled `re.error` in Pandas. | Resolved: Implemented `regex=False, na=False` in `app.py`. | **VERIFIED FIXED** |
| **DEF-02** | Grade Editor | Low | Adding a tier when preceding boundary was $\le 20\%$ previously risked duplicate percentage. | Resolved: Added dynamic half-step calculation strictly between 0 and preceding tier. | **VERIFIED FIXED** |
| **DEF-03** | Startup Paths | Low | Starting Streamlit from non-root working directory caused `sample_*.csv` file not found. | Resolved: Anchored sample data paths to `BASE_DIR = os.path.dirname(__file__)`. | **VERIFIED FIXED** |
| **REQ-01** | Feature Request | Low | Allow uploading official institution logo to appear on exported reports. | Scheduled for V2.0 roadmap. | **BACKLOG (V2)** |
| **REQ-02** | Feature Request | Low | PDF report generation with formatted printable report cards. | Scheduled for V2.0 roadmap. | **BACKLOG (V2)** |
