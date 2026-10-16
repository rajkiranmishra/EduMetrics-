# Security Architecture, Threat Model & Privacy Controls
## EduMetrics — Academic Performance Analytics Platform

**Document Version:** 1.5.0  
**Target Release:** EduMetrics V1 (Fix 04 Security Hardened)  
**Security Status:** Audited & Hardened for Public Demonstration  

---

## 1. Executive Security Summary

EduMetrics V1 is a lightweight, session-ephemeral educational analytics platform designed to analyze student academic performance. As part of **Fix 04: Security Hardening, Privacy & Concurrency**, the codebase was audited under a lightweight STRIDE threat model, resulting in:
- Hardened CSV upload ingestion with multi-layer bounding (file size, row count, column count, raw cell length, and header length).
- Defense-in-depth against CSV Formula Injection (CWE-1236), including detection of leading whitespace bypasses and dangerous control triggers.
- Robust filename sanitization preventing directory traversal and script tag injection.
- Detection and rejection of dangerous Unicode bidirectional override sequences (`\u202e` etc.) and unprintable control characters.
- Strict error-collection capping preventing memory and UI rendering denial of service.
- Verification of session isolation and multi-user concurrency without global shared-state contamination.
- Transparent and honest documentation of data handling realities and hosting operational boundaries.

---

## 2. Threat Model (STRIDE Analysis)

### 2.1 Assets, Entry Points, and Trust Boundaries

- **Assets:**
  - Student performance data (Student IDs, Names, Attendance, Course Marks).
  - Calculated academic results (Percentages, Grades, Pass/Fail classifications, Leaderboards).
  - Institutional grading configurations (Grade boundaries, passing thresholds, subject overrides, attendance policies).
  - Exported artifacts (Sanitized CSVs and audit-ready text summary reports).

- **Entry Points:**
  - CSV file upload component (`app.py` via `st.file_uploader`).
  - Preloaded sample dataset selection buttons.
  - Interactive Streamlit widgets (Grade boundary inputs, sliders, numbers, and text fields).
  - CLI arguments and dataset file path (`main.py`).
  - Export download requests (CSV and Text report generation).

- **Trust Boundaries:**
  - **Client Browser $\leftrightarrow$ Streamlit Server:** Untrusted browser traffic connects over HTTP/WebSockets.
  - **Streamlit UI Layer $\leftrightarrow$ Core Analytical Engine:** Analytical functions in `core/` accept data from `app.py` or `main.py`.
  - **Application Memory $\leftrightarrow$ Exported Files:** Data exported to disk or browser downloads crosses to external software (e.g., Microsoft Excel, Google Sheets, LibreOffice Calc).
  - **Application Server $\leftrightarrow$ Cloud Hosting Platform:** Container runtime managed by third-party hosting providers (e.g., Streamlit Community Cloud).

- **Potential Threat Actors:**
  - Anonymous web visitors submitting malformed, oversized, or malicious files.
  - Users attempting to execute arbitrary formulas in educators' spreadsheet applications.
  - Users attempting to exhaust server CPU or RAM to cause Denial of Service.

---

### 2.2 STRIDE Threat Classification & Mitigations

| STRIDE Category | Threat Scenario | Baseline Risk | Countermeasures Implemented | Verified Residual Risk |
| :--- | :--- | :---: | :--- | :---: |
| **Spoofing** | Attacker injects Unicode bidirectional overrides (`\u202e`) into student names to spoof administrator or teacher identities. | Medium | `has_prohibited_characters()` rejects all Bidi override sequences (`\u202a`–`\u202e`, `\u200e`, `\u200f`, `\u2066`–`\u2069`) in student IDs, names, and departments. | Low |
| **Tampering** | Upload of malicious CSV with binary data, ZIP bombs, unprintable characters, or oversized individual cells ($>512$ bytes). | High | 1. Null-byte & binary header rejection (`MZ`, `ELF`, `PK\x03\x04`).<br>2. Cell length bounded to $\le 512$ characters in raw reader.<br>3. Column headers bounded to $\le 64$ characters.<br>4. Header & cell control characters rejected. | Low |
| **Repudiation** | Disputes regarding which grading policy was used to evaluate student standings. | Low | Exported text reports embed an immutable audit snapshot with timestamp, total student records, exact grade boundaries, passing thresholds, and attendance rules. | Low |
| **Information Disclosure** | Data from User A leaking to User B; server paths, environment variables, or stack traces displayed in the UI. | High | 1. Zero global mutable state; all user data is strictly scoped in `st.session_state` or pure functional scope.<br>2. Centralized session cleanup resets stale state.<br>3. Sanitized error messages prevent stack trace and file path exposure to users. | Low |
| **Denial of Service (DoS)** | Exhaustion of server memory via massive files ($>2$ MB), row bombs ($>5,000$), column bombs ($>30$), or thousands of validation errors. | High | 1. Strict pre-allocation limits: 2 MB max, 5,000 rows max, 30 columns max.<br>2. Validation error collection capped at 500 errors to prevent browser DOM exhaustion.<br>3. Benchmark confirmed: 5,000 rows evaluated in ~0.51s using 12.6 MB peak RAM. | Low |
| **Elevation of Privilege** | **CSV Formula Injection (CWE-1236):** Malicious CSV cells executing commands (e.g., `=CMD|' /C calc'!A0`) when opened by an educator in Excel or Calc. | High | In `security/upload_checks.py`, all exported text fields beginning with `=`, `+`, `-`, `@`, `\t`, `\r`, or `%` (including leading whitespace bypasses like `   =1+1`) are escaped by prepending a single quote (`'`). | Low |

---

## 3. CSV Upload Security & Ingestion Defenses

EduMetrics enforces defense-in-depth ingestion controls across `security/upload_checks.py`, `core/loader.py`, and `core/validation.py`:

1. **Pre-Allocation Size Check:**
   - Maximum upload size is strictly limited to **2 MB (2,097,152 bytes)**.
   - Files exceeding 2 MB are rejected immediately before decoding or parsing.

2. **Binary and Executable Rejection:**
   - Raw bytes are inspected for null bytes (`\x00`).
   - Magic bytes for known executable and archive formats are actively checked and rejected:
     - `MZ` (Windows PE / executable)
     - `\x7fELF` (Linux ELF executable)
     - `\xca\xfe\xba\xbe` (Java bytecode / Mach-O universal binary)
     - `PK\x03\x04` (ZIP archives / Office Open XML containers)

3. **Dimensional Limits:**
   - Maximum rows: **5,000 data rows**.
   - Maximum columns: **30 columns**.
   - Files exceeding these boundaries are rejected during header/row counting prior to DataFrame instantiation.

4. **Field and Cell Length Limits:**
   - **Raw Cell Length:** Maximum **512 characters** per individual CSV cell. Prevents memory exhaustion attacks utilizing small file sizes with massive single-cell payloads.
   - **Column Header Length:** Maximum **64 characters**.
   - **Student ID Length:** Maximum **64 characters**.
   - **Student Name Length:** Maximum **128 characters**.
   - **Department Name Length:** Maximum **64 characters**.

5. **Adversarial Filename Sanitization:**
   - `sanitize_filename()` strips all path traversal sequences (`../`, `..\`), directory separators, null bytes, HTML/script tags (`<`, `>`, `"`, `'`, `;`, `|`), and control characters.
   - Filenames are bounded to a maximum of 128 characters.
   - Empty, dot-only, or whitespace-only filenames fall back safely to `uploaded_dataset.csv`.

6. **Validation Error Capping:**
   - Datasets generating massive numbers of validation errors (e.g., thousands of malformed cells) are capped at **500 errors** with an explicit termination notice. This protects server memory and client browser rendering performance.

---

## 4. CSV Formula-Injection Defense (CWE-1236)

### 4.1 Threat Context
When educators export analysis results to CSV and open them in spreadsheet software (Microsoft Excel, Apple Numbers, Google Sheets, LibreOffice Calc), cells starting with formula trigger characters can be automatically interpreted as active formulas or DDE (Dynamic Data Exchange) command executions.

### 4.2 Defusion Implementation
EduMetrics implements formula defusion in `security/upload_checks.py` via `defuse_formula_injection()`, invoked across all CSV export paths (`core/reports.py`):
- **Triggers Protected:** `=`, `+`, `-`, `@`, Tab (`\t`), Carriage Return (`\r`), `%`.
- **Leading Whitespace Detection:** Triggers preceded by whitespace (e.g., `"   =1+1"`, `"\t@SUM(...)"`, `"  +cmd|..."`) are detected by inspecting `value.lstrip(" \t\r\n")` and escaped.
- **Escaping Mechanism:** If a string begins with any trigger character (or leading whitespace followed by a trigger), a single quote (`'`) is prepended to the string.
- **Idempotence:** Strings already beginning with `'` are not double-escaped.
- **Preservation of Legitimate Values:** Numeric numbers (integers, floats) and valid student names/IDs that do not begin with formula triggers remain untouched.

### 4.3 Realistic Spreadsheet Behavior & Limitations
- **Microsoft Excel & LibreOffice Calc:** Prepending a single quote (`'`) instructs the spreadsheet calculation engine to treat the cell contents strictly as a literal text string rather than an executable formula or command.
- **Display Variations:** While Excel and Calc typically suppress the leading single quote in cell views, some lightweight or web-based spreadsheet viewers may display the literal single quote prefix. This is an intentional trade-off in favor of execution security.
- **General Caution:** Educators should never enable external data links, macros, or DDE execution when prompted by spreadsheet software on untrusted external CSV files.

---

## 5. Session State & Concurrency Isolation

### 5.1 Architecture & Scope
Streamlit applications execute in a shared Python runtime process where each connected user communicates over an isolated WebSocket connection tied to a distinct `st.session_state` instance:
- **Zero Global Mutable State:** EduMetrics maintains no module-level global DataFrames, shared result dictionaries, or inter-session caches.
- **Dataset Fingerprinting:** Uploaded datasets are fingerprinted via MD5 content hashing (`compute_dataset_fingerprint()`). If a user uploads a new dataset, re-uploads different data under the same filename, or selects a sample dataset, previous analytical results and DataFrames are immediately cleared.
- **Configuration Staleness:** Modifying grade boundaries, subject maximum marks, passing cutoffs, or attendance policies immediately flags `st.session_state.config_stale = True` and invalidates previous results.
- **Explicit Reset:** Clicking "Start New Analysis / Reset" purges all active DataFrame references, metadata objects, and increments the uploader key to clear file widgets.

### 5.2 Concurrency Verification
Session isolation has been verified across multiple levels:
1. **Automated Streamlit AppTest Regressions:** `tests/test_sessions.py` executes 29 distinct scenarios including multi-session isolation, consecutive dataset swaps, policy mutation invalidation, and state resets.
2. **Multi-Threaded Concurrency Testing:** 20 simulated concurrent user sessions running across 4 worker threads with differing datasets, grading policies, and malformed uploads verified:
   - 100% data isolation (zero cross-session contamination).
   - Safe rejection of malformed uploads without impacting concurrent valid sessions.
   - Deterministic and independent grade distributions.

---

## 6. Privacy & Data Handling Realities

EduMetrics is committed to transparent, accurate privacy disclosures without unsubstantiated claims:

1. **Server-Side Memory Processing:**
   - Uploaded student datasets are sent to the application server over HTTPS/WebSockets.
   - All dataset validation, normalization, grade evaluation, and statistical reporting occur entirely within transient server memory (RAM).

2. **No Persistent Application Storage in V1:**
   - EduMetrics V1 does not implement or connect to any database, file storage bucket, Redis cache, or disk persistence layer.
   - Uploaded datasets are not intentionally written to disk or recorded in application log files.

3. **Hosting Provider Operational Realities:**
   - On public cloud hosting platforms (such as Streamlit Community Cloud, AWS, GCP, or Azure), hosting providers operate the underlying container infrastructure.
   - Hosting platforms may collect operational infrastructure metrics, web server access logs, and ephemeral memory states.

4. **Session Reset Semantics:**
   - Clicking "Start New Analysis / Reset" removes active Python references to raw and evaluated DataFrames within the session state dictionary.
   - While Python's garbage collector frees dereferenced memory, physical memory overwriting (zeroing RAM) is neither guaranteed nor feasible within standard user-space runtimes.

5. **No Authentication Boundary:**
   - EduMetrics V1 does not implement user authentication (passwords, OAuth, MFA) or role-based access control.
   - Streamlit session state is an ephemeral UI session container, **not an authenticated cryptographic security perimeter**.

6. **Demonstration Policy:**
   - **Users must upload fictional or appropriately de-identified / anonymized academic datasets only.**
   - Do not upload real student records governed by FERPA, GDPR, or institutional privacy regulations to public demonstrator instances.

---

## 7. Error Handling & Information Exposure

- **Sanitized User Feedback:** Error messages generated during ingestion and validation provide specific row and column coordinates (e.g., `Row 5, Column 'Math': Mark exceeds maximum allowed score`) without disclosing private system data.
- **Stack Trace Suppression:** In the Streamlit web interface, common ingestion and configuration errors are caught and rendered as styled warning banners (`st.error()`, `st.warning()`), preventing internal Python tracebacks from displaying to end users.
- **Path Sanitization:** File error notices display only the sanitized base filename (`os.path.basename`) and do not disclose server directory structures or filesystem paths.

---

## 8. Dependency & Repository Security

- **Repository Hygiene:**
  - Zero hardcoded API keys, secrets, credentials, or tokens exist in source code or configuration files.
  - No real student records or personal identifying information are committed to git; only synthetic fictional datasets (`sample_school.csv`, `sample_college.csv`) are tracked.
  - `.gitignore` strictly excludes `.env`, `venv/`, `.venv/`, `.pytest_cache/`, `__pycache__/`, `.DS_Store`, and Streamlit credentials (`.streamlit/secrets.toml`).

- **GitHub Actions CI Least Privilege:**
  - `.github/workflows/ci.yml` explicitly enforces `permissions: contents: read`, restricting runner access to the minimum permissions necessary for checkout and automated testing.
  - CI workflow tests compatibility across Python 3.9, 3.10, and 3.11 on every push and pull request.

- **Dependency Management:**
  - Core dependencies (`pandas`, `numpy`, `streamlit`, `altair`, `pytest`) are pinned in `requirements.txt`.
  - Dependencies are compatible with standard Linux and macOS environments.

---

## 9. Performance & Resource Benchmarks

Real performance benchmarks were conducted on **macOS Darwin ARM64** using **Python 3.9.6** on the `fix/v1-hardening` branch.

### 9.1 Dataset Scaling Benchmarks (Pure Analytical Engine)

| Dataset Size | Records | Ingestion & Validation | Grading & Analytics | Total Processing Time | Peak Memory Delta |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **Small Cohort** | 20 students | 6.84 ms | 6.77 ms | **13.61 ms** | **0.56 MB** |
| **Standard Class** | 100 students | 6.80 ms | 7.04 ms | **13.84 ms** | **0.45 MB** |
| **Large Department** | 1,000 students | 55.43 ms | 49.89 ms | **105.32 ms** | **2.79 MB** |
| **Maximum Limit** | 5,000 students | 272.93 ms | 241.90 ms | **514.83 ms** | **12.66 MB** |

*Key Takeaway:* Processing a maximum allowed dataset (5,000 rows across 5 subjects) requires approximately **0.51 seconds** and consumes only **12.66 MB of RAM**, well within standard cloud container limits (typically 1 GB).

### 9.2 Concurrency Benchmark Results

| Concurrency Scenario | Total Wall Time | Avg Request Latency | Peak RAM Delta | Data Isolation |
| :---: | :---: | :---: | :---: | :---: |
| **1 Concurrent User** | 14.16 ms | 11.36 ms | 0.65 MB | 100% Isolated |
| **5 Concurrent Users** | 35.32 ms | 12.51 ms | 0.44 MB | 100% Isolated |
| **10 Concurrent Users** | 67.45 ms | 14.20 ms | 0.58 MB | 100% Isolated |
| **20 Concurrent Users** | 126.01 ms | 13.82 ms | 0.48 MB | 100% Isolated |

*Testing Methodology Note:* Concurrency was tested via multi-threaded Python sessions invoking full ingestion, validation, policy configuration, student evaluation, and report generation simultaneously. Web browser WebSocket concurrency under high connection counts remains subject to the hosting environment's bandwidth and proxy limits.

---

## 10. Responsible Vulnerability Disclosure

If you discover a security vulnerability or privacy flaw in EduMetrics, please report it responsibly:
- **Contact:** rajkiranmishra@example.com (or via private GitHub Security Advisory)
- **Response Commitment:** Initial acknowledgment and triage within 48 hours.
- **Coordination:** We request a 14-day coordination window before public disclosure to allow for verification and patching.
