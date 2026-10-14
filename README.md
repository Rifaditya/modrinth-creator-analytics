# 📈 Modrinth Creator Analytics Studio

[![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://streamlit.io/)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Plotly](https://img.shields.io/badge/Plotly-5.20%2B-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com/)
[![License](https://img.shields.io/badge/License-GPL--3.0-blue?style=for-the-badge)](LICENSE)
[![Zero-Keys](https://img.shields.io/badge/API%20Keys-Zero%20Required-success?style=for-the-badge)](#-1-click-streamlit-community-cloud-deployment)

> **Autonomous Executive Intelligence Suite for Minecraft Mod Creators**  
> High-performance, offline-first dashboard designed to ingest raw Modrinth analytics exports, resolve telemetry ambiguities, model creator revenue economics, analyze launcher ecosystems, and visualize global geospatial distributions.

---

## 🌟 Executive Overview & Studio Telemetry

Over the **178-day historical observation window** (April 16, 2026 – October 13, 2026), the studio recorded milestone telemetry across 21 published Fabric mods and libraries:

| Studio Metric | Value | Architectural Significance |
| :--- | :--- | :--- |
| **Total Downloads** | **100,226** | 100K milestone achieved across 21 production projects |
| **Creator Revenue** | **$29.40** | Total Modrinth Creator Program net monetization yield |
| **Cumulative Playtime** | **1,048.96 hours (~43.7 days)** | Logged in-game engagement tracked across Modrinth App telemetry |
| **Blended RPM** | **$0.29** | Blended revenue per 1,000 total downloads |
| **Monetized RPM** | **$2.95** | Effective revenue per 1,000 eligible monetized downloads |
| **Monetized View RPM** | **$1.17** | Revenue per 1,000 monetized project page views |
| **Lead Engine Anchor** | **MC 26.2** | Sovereign target anchor leading adoption with 32,556 DLs |
| **Modern Adoption (26.x)** | **92.3%** | Modern Minecraft versions dominate user installations |
| **Direct vs Modpack** | **72.0% / 28.0%** | 72,195 standalone user installs vs 28,031 ecosystem modpack pulls |
| **Version Mapping Rate** | **99.80%** | Enriched Engine disambiguates 38.7k raw telemetry unknowns |

---

## 🧭 The 5 Dedicated Intelligence Tabs

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          MODRINTH CREATOR ANALYTICS STUDIO                             │
├───────────────┬───────────────────┬──────────────────┬─────────────────┬───────────────┤
│ 💰 Tab 1      │ 🚀 Tab 2          │ 🎮 Tab 3         │ 📦 Tab 4        │ 🌍 Tab 5      │
│ Revenue       │ Launchers &       │ Minecraft        │ Projects &      │ Global        │
│ Economics     │ Sources           │ Demographics     │ Modpacks        │ Geography     │
└───────────────┴───────────────────┴──────────────────┴─────────────────┴───────────────┘
```

### 💰 Tab 1: Revenue Economics, Rolling RPM & Milestone Forecaster
- **Dual-RPM & View-Based Monetization**: Breaks down the revenue funnel into **Blended RPM** ($0.29 / 1,000 downloads) and **Monetized RPM** ($2.95 / 1,000 eligible downloads), complemented by **View-Based Monetization** ($1.17 per 1,000 monetized views) reflecting verified ad impressions on creator project pages. Non-monetized downloads (90.1%) represent launcher updates, background syncs, and direct API pulls where impressions are not served.
- **Rolling Trailing-30D RPM Dynamics**: Computes 30-day moving window blended and monetized RPMs over time to capture longitudinal monetization momentum beyond static lifetime averages.
- **Daily Financial Trendlines**: Dual-axis Plotly visualization correlating daily net earnings ($) against daily download velocity.
- **Interactive Milestone Forecasting Calculator**: Dynamic slider projecting estimated days, daily run-rates, and download targets required to achieve creator milestones ($50, $100, $250, $500, etc.).
- **Streamer Privacy Mode & Pre-Tracking Baseline**: Sidebar toggles to instantly mask revenue figures (`$••••`) for public streaming, and exclude the April 16–30 pre-tracking baseline where dimension telemetry was unrecorded by Modrinth to focus on active logging from May 1 onward.

### 🚀 Tab 2: Launchers & Distribution Sources
- **Launcher Market Share**: Deep-dive audit comparing the **Modrinth App** (44,055 DLs, 44.0%), **Web Direct** (17,845 DLs, 17.8%), **Prism Launcher** (16,332 DLs, 16.3%), and third-party clients (**Lunar Client**, **Badlion**, **CurseForge**, **ATLauncher**).
- **Standalone vs Ecosystem Distribution**: Quantifies direct player intent (72,195 direct downloads) vs secondary modpack bundle syndication (28,031 downloads).
- **Cumulative Ingestion Trajectory**: Visualizes client adoption waves and growth dynamics over time.

### 🎮 Tab 3: Minecraft Demographics & Disambiguation Engine
- **Sovereign Lead Anchor (MC 26.2)**: Tracks 32,556 downloads on MC 26.2, establishing it as the sovereign target version, followed closely by MC 26.1 and 26.3+.
- **Multi-Era Anchor Parity**: Tracks legacy Long-Term Support (LTS) anchors (1.21.1 with 5,820 DLs and 1.20.1 with 1,672 DLs), validating studio backporting investments.
- **The Enriched Disambiguation Engine**: Modrinth's raw telemetry leaves **38,775 downloads** categorized as "Other" or "Unknown" due to headless launcher API queries and the April 16–30 pre-tracking baseline. Our custom enrichment engine cross-references file hash fingerprints and version metadata against `data/modrinth_version_catalog.json` to resolve **99.80%** of all version downloads into their true Minecraft targets.
- **Side-by-Side Verification**: Toggle between **Enriched Engine** and **Raw Telemetry** to audit the exact disambiguation uplift.

### 📦 Tab 4: Projects & Modpack Ecosystem Matrix
- **Full Catalog Matrix**: Interactive, sortable leaderboard ranking all 21 studio projects by total downloads, views, revenue, conversion rates, playtime, and **Downloads per View (x)**.
- **Flagship Dominance**: Identifies core library utility **Dasik Library** (41,167 DLs) and top standalone player mod **VO: Better Dogs** (31,034 DLs).
- **Third-Party Modpack Virality**: Tracks dependent project adoption, revealing massive organic syndication through curated modpacks such as **Sensible MC** (11,624 DLs) and **Legacies** (3,522 DLs).
- **Single Mod Deep-Dive Inspector**: Dedicated sub-view allowing creators to isolate a single project and inspect its version distribution, download reasons, and monetization performance.

### 🌍 Tab 5: Global Geography & Telemetry Analytics
- **World Choropleth Map**: Interactive choropleth visualizer rendering geographic distribution across **8 sovereign nations** (US, Germany, Brazil, UK, China, Russia, Indonesia, Singapore) + Other.
- **Dual Display Metrics**: Toggle between **Total Downloads** and **Cumulative Playtime (Hours)** to analyze player engagement depth.
- **High-Contrast Logarithmic Scaling**: Optional logarithmic color normalization to prevent dominant nations (United States with 20,381 DLs, Germany with 1,765 DLs) from flattening international gradients.
- **Telemetry Ingestion Callout**: Highlights Modrinth's logging pipeline telemetry, where **76,315 downloads (76.1%)** under 'Other' represent unrecorded IP telemetry in the logging pipeline (settling to ~75% in later months).

---

## 🏗️ Architecture & Directory Tree

```
modrinth-creator-analytics/
├── .streamlit/
│   └── config.toml               # Studio dark theme & typography configuration
├── data/
│   ├── modrinth_version_catalog.json # Version hash metadata catalog (99.80% disambiguation)
│   └── raw/                      # 10 Modrinth raw CSV exports (Apr 16 - Oct 13, 2026)
│       ├── Modrinth Analytics Country Breakdown ... .csv
│       ├── Modrinth Analytics Dependent project Breakdown ... .csv
│       ├── Modrinth Analytics Download reason Breakdown ... .csv
│       ├── Modrinth Analytics Download source Breakdown ... .csv
│       ├── Modrinth Analytics Game version Breakdown ... .csv
│       ├── Modrinth Analytics Loader Breakdown ... .csv
│       ├── Modrinth Analytics Member Breakdown ... .csv
│       ├── Modrinth Analytics Monetization Breakdown ... .csv
│       ├── Modrinth Analytics Project Breakdown ... .csv
│       └── Modrinth Analytics Project version Breakdown ... .csv
├── src/
│   ├── __init__.py               # Package root
│   ├── charts.py                 # Plotly visualization components & dark theme styling
│   ├── loader.py                 # Data loader, normalization, enrichment & caching
│   └── metrics.py                # Financial, launcher, demographic & summary KPI calculations
├── tests/
│   ├── __init__.py               # Test package root
│   ├── test_app.py               # Headless Streamlit AppTest suite (widgets, tabs, toggles)
│   ├── test_loader.py            # Unit tests for loading, enrichment & parity bounds
│   └── test_metrics.py           # Unit tests for KPIs, milestones, charts & empty resilience
├── app.py                        # Main Streamlit executive dashboard entrypoint
├── requirements.txt              # Production dependency specifications
├── run.bat                       # 1-Click Windows execution launcher
├── verify_app.py                 # Standalone 5-Gate automated verification engine
└── README.md                     # High-density technical documentation & cloud deploy guide
```

---

## ☁️ 1-Click Streamlit Community Cloud Deployment

Deploying this studio to **Streamlit Community Cloud** (`share.streamlit.io`) is completely free, requires **zero environment variables**, and operates with **zero API keys**:

### Step 1: Push Repository to GitHub
Ensure this repository is pushed to your GitHub account:
```bash
git remote add origin https://github.com/<your-username>/modrinth-creator-analytics.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Streamlit Cloud
1. Navigate to [share.streamlit.io](https://share.streamlit.io/) and sign in with your GitHub account.
2. Click **"Create app"** (or **"New app"**).
3. Fill in the deployment parameters:
   - **Repository**: `<your-username>/modrinth-creator-analytics`
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL**: *(Optional)* Select a custom subdomain (e.g. `modrinth-creator-analytics.streamlit.app`)
4. Click **"Deploy!"**.

### Why Zero Configuration is Required:
- **Zero API Keys**: Uses static, offline CSV exports and a bundled metadata catalog.
- **Zero Environment Variables**: No credentials, database connections, or tokens needed.
- **Self-Contained Data**: Bundled in `data/raw/` and cached via `@st.cache_data`.
- **Custom Upload Ready**: Any viewer or creator can use the built-in sidebar file uploader to analyze their own Modrinth export archives on the fly.

---

## 💻 Local Quickstart

### Prerequisites
- Python 3.10, 3.11, 3.12, 3.13, or 3.14
- Standard `pip` package manager

### 1. Clone & Install
```bash
git clone https://github.com/<your-username>/modrinth-creator-analytics.git
cd modrinth-creator-analytics
pip install -r requirements.txt
```

### 2. Launch the Application
- **Windows 1-Click**: Double-click `run.bat`
- **Command Line**:
  ```bash
  python -m streamlit run app.py
  ```
The dashboard will open automatically in your browser at `http://localhost:8501`.

---

## 🛡️ 5-Gate Automated Verification Suite

The repository includes a standalone, production-grade verification runner that validates all 5 architectural gates before deployment:

```bash
python verify_app.py
```

### The 5 Verification Gates:

| Gate | Description | Pass Criteria |
| :--- | :--- | :--- |
| **Gate 1: Bytecode Compilation** | Compiles all `.py` files across root, `src/`, and `tests/` using `py_compile`. | 0 syntax errors across 10 source files. |
| **Gate 2: Dataset Integrity** | Validates `ModrinthDataBundle` schema, dataframes, revenue, and mapping rate. | 10/10 non-empty tables, $29.40 revenue, 100,226 downloads, $\ge 99.5\%$ mapping rate. |
| **Gate 3: Pytest Execution** | Runs the full unit and integration test suite via `pytest tests/ -v`. | 23/23 tests pass 100% green. |
| **Gate 4: Headless AppTest** | Executes `streamlit.testing.v1.AppTest` through all widget permutations. | 0 runtime exceptions across load, streamer toggle, radios, and selects. |
| **Gate 5: Subprocess Smoke Test** | Spawns local Streamlit background server on port 8599 and polls health check. | HTTP 200 OK from `/_stcore/health` within 15 seconds. |

### Verification Output:
```text
======================================================================
 MODRINTH CREATOR ANALYTICS -- 5-GATE VERIFICATION SUITE
======================================================================
Working Directory : E:\Minecraft Project\modrinth-creator-analytics
Python Executable : python.exe
Python Version    : 3.14.6

[RUNNING] Gate 1: Bytecode Compilation...
[PASS] Gate 1: Bytecode Compilation (0.05s): Successfully compiled 10 Python source files with 0 syntax errors.

[RUNNING] Gate 2: Dataset Integrity & Enrichment Check...
[PASS] Gate 2: Dataset Integrity & Enrichment Check (1.67s): 10/10 tables verified. Revenue: $29.3994 (~$29.40), Downloads: 100,226, Mapping Rate: 99.80% (>=99.5%).

[RUNNING] Gate 3: Pytest Execution (23+ Unit & App Tests)...
[PASS] Gate 3: Pytest Execution (23+ Unit & App Tests) (14.91s): Pytest suite passed: 23 passed in 13.79s.

[RUNNING] Gate 4: Headless Streamlit AppTest Verification...
[PASS] Gate 4: Headless Streamlit AppTest Verification (7.56s): Headless AppTest passed initial run and all interactive widget permutations cleanly (0 exceptions).

[RUNNING] Gate 5: Local Streamlit Subprocess Smoke Test...
[PASS] Gate 5: Local Streamlit Subprocess Smoke Test (1.74s): Streamlit server healthy at http://localhost:8599/_stcore/health (HTTP 200 OK).

======================================================================
 VERIFICATION SUMMARY BANNER
======================================================================
Gate Name                                     | Status | Duration
----------------------------------------------------------------------
Gate 1: Bytecode Compilation                  | PASS   |   0.05s
Gate 2: Dataset Integrity & Enrichment Check  | PASS   |   1.67s
Gate 3: Pytest Execution (23+ Unit & App Tests) | PASS   |  14.91s
Gate 4: Headless Streamlit AppTest Verification | PASS   |   7.56s
Gate 5: Local Streamlit Subprocess Smoke Test | PASS   |   1.74s
----------------------------------------------------------------------
Total Verification Duration                   |        |  25.93s

>>> ALL 5 GATES PASSED (100% GREEN) -- STUDIO PRODUCTION READY <<<
```

---

## 📄 License & Attribution

Distributed under the **GNU General Public License v3.0** (`GPL-3.0`). See `LICENSE` for details.  
Built with pride for the Minecraft creator ecosystem by **Dasik (Rifaditya)**.
