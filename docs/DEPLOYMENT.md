# EduMetrics — Deployment Guide 🚀
### Production Preparation, Streamlit Community Cloud & Self-Hosting

**Target Version:** V1.0.0  
**Entry Point:** `app.py`  
**Primary Platform:** Streamlit Community Cloud  
**Supported Runtimes:** Linux (Ubuntu 22.04 LTS+), macOS, Docker (Debian/Alpine base)  
**Supported Python Versions:** Python 3.9, 3.10, 3.11  

---

## 📑 Table of Contents
1. [Deployment Architecture & Operational Model](#1-deployment-architecture--operational-model)
2. [Pre-Flight Verification Checklist](#2-pre-flight-verification-checklist)
3. [Streamlit Community Cloud Deployment (Step-by-Step)](#3-streamlit-community-cloud-deployment-step-by-step)
4. [Post-Deployment Verification & Smoke Testing](#4-post-deployment-verification--smoke-testing)
5. [Resource Bounds & Shared Hosting Limitations](#5-resource-bounds--shared-hosting-limitations)
6. [Rollback Procedure](#6-rollback-procedure)
7. [Alternative Self-Hosted Deployment (Linux VM / Docker)](#7-alternative-self-hosted-deployment-linux-vm--docker)
8. [Troubleshooting & Common Failure Modes](#8-troubleshooting--common-failure-modes)

---

## 1. Deployment Architecture & Operational Model

EduMetrics is architected as an **ephemeral, zero-login academic analytics dashboard**:
- **Transient Memory Scoping:** Uploaded datasets, mapped schemas, customized grading policies, and computed metrics exist strictly within the server-side process memory assigned to the user's active session.
- **Zero Persistent Storage:** The application intentionally does not write uploaded files to disk, databases, or object storage (AWS S3, Google Cloud Storage).
- **Stateless Cloud Portability:** Because no external databases or API credentials are required, the repository deploys cleanly to any standard Streamlit host without environment configuration secrets.

```
+-------------------------------------------------------------------------+
|                       Streamlit Community Cloud                         |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                     Container (Debian Linux)                      |  |
|  |                                                                   |  |
|  |   Python 3.9/3.10/3.11 Runtime                                    |  |
|  |   Dependencies: streamlit 1.50.0, pandas 2.3.3, numpy 2.0.2       |  |
|  |                                                                   |  |
|  |   +-----------------------------------------------------------+   |  |
|  |   |                app.py (Streamlit Web UI)                  |   |  |
|  |   +-----------------------------+-----------------------------+   |  |
|  |                                 |                                 |  |
|  |   +-----------------------------v-----------------------------+   |  |
|  |   |      core/ (loader, validation, grading, analytics)       |   |  |
|  |   |      security/ (upload checks, formula injection defusion)|   |  |
|  |   +-----------------------------------------------------------+   |  |
|  |                                                                   |  |
|  |   +-----------------------------------------------------------+   |  |
|  |   |  data/sample_school.csv  |  data/sample_college.csv       |   |  |
|  |   |  (Read-only built-in benchmarks resolved via BASE_DIR)    |   |  |
|  |   +-----------------------------------------------------------+   |  |
|  +-------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
```

---

## 2. Pre-Flight Verification Checklist

Before triggering a public deployment, verify the following prerequisites:

| Item | Requirement | Status | Verification Command |
| :--- | :--- | :--- | :--- |
| **Entry Point** | Root `app.py` exists and is executable | Verified | `test -f app.py && echo "OK"` |
| **Dependencies** | `requirements.txt` has pinned versions | Verified | `pip install -r requirements.txt` |
| **Test Suite** | All automated tests pass cleanly | Verified | `pytest -v` (134 passed) |
| **CLI Engine** | Standalone CLI executes on sample datasets | Verified | `python main.py --file data/sample_school.csv` |
| **Sample Data** | `data/sample_school.csv` and `college` present | Verified | `ls -l data/*.csv` |
| **Relative Paths** | Path resolution uses `os.path.abspath(__file__)` | Verified | Tested across arbitrary working dirs |
| **Zero Secrets** | No API keys, credentials, or `.env` files in git | Verified | `git grep -i 'secret'` |
| **Streamlit Config** | `.streamlit/config.toml` restricts upload to 2MB | Verified | `cat .streamlit/config.toml` |

---

## 3. Streamlit Community Cloud Deployment (Step-by-Step)

Follow these exact steps to deploy EduMetrics to Streamlit Community Cloud:

### Step 1: Sign In to Streamlit Community Cloud
1. Navigate to **[https://share.streamlit.io](https://share.streamlit.io)**.
2. Sign in using your authorized GitHub account (`rajkiranmishra`).

### Step 2: Create a New Application
1. In the top-right corner of the Streamlit Cloud workspace, click **"New app"**.
2. If prompted, grant Streamlit authorization to access your GitHub repositories.

### Step 3: Configure Repository Settings
In the **"Deploy an app"** dialog, configure the deployment parameters:

- **Repository:** `rajkiranmishra/private` *(or `rajkiranmishra/edumetrics` once renamed)*
- **Branch:** `fix/v1-hardening` *(or `main` following release merge)*
- **Main file path:** `app.py`
- **App URL (optional):** Choose a custom subdomain if available (e.g., `edumetrics-demo.streamlit.app`).

### Step 4: Advanced Configuration (Python Runtime)
1. Click **"Advanced settings"** before deploying.
2. **Python Version:** Select **Python 3.10** or **Python 3.11** (both fully tested and supported).
3. **Secrets:** Leave blank. EduMetrics requires zero API keys, database credentials, or environment secrets.
4. Click **"Save"**.

### Step 5: Launch Deployment
1. Click **"Deploy!"**.
2. Streamlit Cloud will allocate a container, clone the repository, install dependencies from `requirements.txt`, and start the Tornado web server.
3. Monitor the build log drawer on the right side of the screen.

---

## 4. Post-Deployment Verification & Smoke Testing

Once Streamlit Cloud reports `"Your app is live!"`, execute this verification protocol on the public URL:

### Test Case 1: Interface & Layout
- Verify the browser title displays: `EduMetrics — Academic Analytics`.
- Confirm the blue **Privacy Notice** banner is visible at the top.
- Confirm the sidebar navigation and session status widgets render without error.

### Test Case 2: Built-in Sample Datasets
- Navigate to **"Upload & Configure"** tab.
- Click **"Load Sample School Dataset"**.
  - Expected: Loads 20 records, 5 subjects (`English`, `Mathematics`, `Science`, `Social_Studies`, `Second_Language`).
- Click **"Load Sample College Dataset"**.
  - Expected: Loads 25 records, 6 subjects (`Data_Structures`, `Algorithms`, `Operating_Systems`, `Database_Lab`, `Web_Tech_Lab`, `Project_Phase_1`), preserving leading-zero IDs (`001`, `002`).

### Test Case 3: Academic Policy Configuration
- Expand **"🏫 Institution Metadata (Optional)"** and provide test values:
  - Institution: `St. Jude Academy`
  - Program: `Grade 10-A`
- Click **"➕ Add Grade Level"** and verify a new tier is added without duplicate percentage errors.
- Click **"➖ Remove Grade Level"** and verify the tier is removed while preserving preceding edits.

### Test Case 4: Run Academic Analysis
- Click **"🚀 Run Academic Analysis"**.
- Confirm the success message appears: `✅ Analysis successfully computed! View the results across the tabs above.`
- Inspect **"📊 Performance Dashboard"**:
  - Class summary metrics (Total, Pass Rate, Class Average, Attendance).
  - Letter grade distribution chart.
  - Top 5 leaderboard.
- Inspect **"📚 Subject Analysis"**:
  - Subject difficulty rankings and pass rates.
- Inspect **"🔍 Student Explorer"**:
  - Test search with ordinary queries (e.g. `Ishita`).
  - Test search with special characters (e.g. `[`, `(`, `*`) — verify no regex crash occurs.
- Inspect **"⚠️ Academic Attention"**:
  - Verify rule-based flags (6 students flagged on school dataset).

### Test Case 5: Report Export & Sanitization
- Navigate to **"📥 Reports & Export"** tab.
- Click **"⬇️ Download Sanitized CSV"** and open the file:
  - Confirm calculated fields (`percentage`, `grade`, `status`, `failure_reasons`) are present.
  - Confirm formula control characters (`=`, `+`, `-`, `@`) have been defused with prepended single quotes (`'`).
- Click **"⬇️ Download Summary Text Report"** and confirm text layout.

### Test Case 6: Session Reset
- In the sidebar, click **"🔄 Start New Analysis / Reset"**.
- Confirm active dataset and results are completely cleared and UI returns to initial state.

---

## 5. Resource Bounds & Shared Hosting Limitations

Streamlit Community Cloud operates on shared infrastructure with container-level resource constraints. EduMetrics incorporates application-level guardrails aligned with these limits:

| Resource | Shared Hosting Limit | EduMetrics Enforcement | Failure Behavior |
| :--- | :--- | :--- | :--- |
| **Max File Size** | ~200 MB default | **2 MB** enforced (`MAX_FILE_SIZE_BYTES`) | Immediate rejection with human-readable error |
| **Max Rows** | Container OOM risk | **5,000 rows** enforced (`MAX_ROW_COUNT`) | Structural validation failure |
| **Max Columns** | Layout degradation | **30 columns** enforced (`MAX_COLUMN_COUNT`) | Structural validation failure |
| **Max Cell Length** | Unbounded string DoS | **512 characters** (`MAX_RAW_CELL_LENGTH`) | Loader-level rejection |
| **Memory (RAM)** | ~1 GB container cap | Ephemeral in-memory DataFrames (< 15 MB) | Graceful garbage collection on session reset |
| **Session Inactivity** | ~15 minutes idle | Session state discarded on timeout | User simply reloads or re-uploads CSV |

> [!CAUTION]
> **FERPA / GDPR Demonstration Notice:**  
> EduMetrics V1 runs on public, shared infrastructure. It is strictly approved for **fictional, synthetic, or de-identified academic datasets**. Educators must never upload personally identifiable student records (PII), national identification numbers, or confidential medical/disciplinary files.

---

## 6. Rollback Procedure

If an unexpected runtime regression occurs post-deployment:

### Method A: Streamlit Cloud Dashboard (Instant Branch Switch)
1. Log in to [https://share.streamlit.io](https://share.streamlit.io).
2. Click the three dots (`...`) next to your application and select **"Settings"**.
3. Under **"Branch"**, switch from `fix/v1-hardening` to the last known stable commit or `main`.
4. Click **"Save"**. The container automatically restarts with the chosen commit.

### Method B: Git Rollback (Repository Level)
1. Identify the previous working commit SHA:
   ```bash
   git log --oneline -n 5
   ```
2. Revert the problematic commit:
   ```bash
   git revert <COMMIT_SHA> -m 1
   git push origin fix/v1-hardening
   ```
3. Streamlit Cloud detects the new push and triggers an automatic build.

---

## 7. Alternative Self-Hosted Deployment (Linux VM / Docker)

For institutional deployments requiring local network isolation or intranet hosting:

### Option A: Standard Linux Systemd Service (Ubuntu 22.04 LTS)

1. **Clone repository:**
   ```bash
   cd /opt
   git clone https://github.com/rajkiranmishra/private.git edumetrics
   cd edumetrics
   ```

2. **Setup virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Create Systemd service definition (`/etc/systemd/system/edumetrics.service`):**
   ```ini
   [Unit]
   Description=EduMetrics Academic Analytics Platform
   After=network.target

   [Service]
   Type=simple
   User=www-data
   WorkingDirectory=/opt/edumetrics
   ExecStart=/opt/edumetrics/.venv/bin/streamlit run app.py --server.port 8501 --server.address 127.0.0.1 --server.headless true
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```

4. **Enable and start service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable edumetrics
   sudo systemctl start edumetrics
   ```

---

## 8. Troubleshooting & Common Failure Modes

### 1. `ModuleNotFoundError: No module named 'core'`
- **Cause:** Running `streamlit run` from an unexpected subfolder or PYTHONPATH omission.
- **Solution:** Ensure `app.py` is invoked from the repository root directory. EduMetrics uses root-relative module imports (`from core.grading import ...`).

### 2. `FileNotFoundError: data/sample_school.csv`
- **Cause:** Arbitrary current working directory when invoking Streamlit.
- **Solution:** Already defended! EduMetrics uses `BASE_DIR = os.path.dirname(os.path.abspath(__file__))` to resolve sample data paths absolutely.

### 3. `CORS / XSRF Configuration Conflict`
- **Cause:** Incompatible flags in `.streamlit/config.toml` (`enableCORS = false` with `enableXsrfProtection = true`).
- **Solution:** Verified! EduMetrics configures `enableCORS = true` and `enableXsrfProtection = true`, ensuring CSRF defenses remain active without browser origin rejections.

### 4. `Streamlit Session Reconnects / Clears Unexpectedly`
- **Cause:** Streamlit Cloud container sleeping after 15 minutes of inactivity.
- **Solution:** This is normal behavior for ephemeral shared hosting. Reopening the tab wakes the container in ~10 seconds.
