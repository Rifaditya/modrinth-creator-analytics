"""Standalone 5-Gate Automated Verification Script for Modrinth Creator Analytics.

Gates:
  Gate 1: Bytecode Compilation (py_compile across root, src/, tests/)
  Gate 2: Dataset Integrity & Enrichment Check (10 tables, revenue, downloads, mapping rate)
  Gate 3: Pytest Execution (full test suite execution via subprocess)
  Gate 4: Headless Streamlit AppTest Verification (AppTest interaction suite)
  Gate 5: Local Streamlit Subprocess Smoke Test (server startup & _stcore/health poll)
"""

import os
import py_compile
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Tuple


def print_banner(title: str) -> None:
    """Print section divider banner."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def gate_1_bytecode_compilation(root_dir: Path) -> Tuple[bool, str]:
    """Gate 1: Compiles all .py files in root, src/, and tests/."""
    py_files: List[Path] = []
    for folder in [root_dir, root_dir / "src", root_dir / "tests"]:
        if folder.exists():
            py_files.extend(folder.glob("*.py"))

    compiled_count = 0
    for file_path in py_files:
        try:
            py_compile.compile(str(file_path), doraise=True)
            compiled_count += 1
        except py_compile.PyCompileError as e:
            return False, f"Compilation failed for {file_path.name}: {e}"

    return True, f"Successfully compiled {compiled_count} Python source files with 0 syntax errors."


def gate_2_dataset_integrity(root_dir: Path) -> Tuple[bool, str]:
    """Gate 2: Verifies dataset integrity, total revenue, downloads, mapping rate, and dynamic metrics."""
    try:
        from src.loader import load_all_data
        from src.metrics import (
            calculate_country_summary,
            calculate_kpis,
            calculate_view_monetization,
        )

        bundle = load_all_data()

        # Check all 10 DataFrames are non-empty
        table_dict = bundle.as_dict()
        if len(table_dict) != 10:
            return False, f"Expected 10 tables in bundle, found {len(table_dict)}"

        for name, df in table_dict.items():
            if df is None or df.empty:
                return False, f"Table '{name}' is empty or None"

        kpis = calculate_kpis(bundle)
        total_rev = kpis["total_revenue"]
        total_dls = kpis["total_downloads"]

        # Check total revenue (~$29.40 / $29.3994)
        if abs(total_rev - 29.40) > 0.05:
            return False, f"Total project revenue ${total_rev:.4f} deviates from expected $29.40"

        # Check total downloads (100,226)
        if total_dls != 100226:
            return False, f"Total downloads {total_dls} != expected 100,226"

        # Check version-to-project mapping rate >= 99.5%
        pv = bundle.project_version
        pv_tot_dls = pv["Downloads"].sum()
        mapped_dls = pv[pv["Project"] != "Unknown"]["Downloads"].sum()
        mapping_rate = mapped_dls / pv_tot_dls if pv_tot_dls > 0 else 0.0

        if mapping_rate < 0.995:
            return False, f"Mapping rate {mapping_rate:.4%} is below 99.5% requirement"

        # Dynamic country and view monetization checks
        _, country_kpis = calculate_country_summary(
            bundle.country, total_bundle_downloads=total_dls
        )
        if country_kpis["identified_countries_count"] <= 0:
            return False, "Dynamic identified_countries_count is non-positive"

        view_mon = calculate_view_monetization(bundle.monetization, bundle.member)
        if view_mon["monetized_view_rpm"] <= 0.0:
            return False, "Dynamic monetized_view_rpm is non-positive"

        return True, (
            f"10/10 tables verified. Revenue: ${total_rev:.4f} (~$29.40), "
            f"Downloads: {total_dls:,}, Mapping Rate: {mapping_rate:.2%} (>=99.5%), "
            f"Identified Nations: {country_kpis['identified_countries_count']}, "
            f"Monetized View RPM: ${view_mon['monetized_view_rpm']:.2f}."
        )
    except Exception as e:
        return False, f"Dataset integrity check raised exception: {e}"


def gate_3_pytest_execution(root_dir: Path) -> Tuple[bool, str]:
    """Gate 3: Runs pytest tests/ -v programmatically via subprocess."""
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]
    try:
        res = subprocess.run(
            cmd,
            cwd=str(root_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            return False, f"Pytest failed with exit code {res.returncode}:\n{res.stdout}\n{res.stderr}"

        # Count passed tests from stdout
        passed_summary = [
            line for line in res.stdout.splitlines() if "passed" in line and "=" in line
        ]
        summary_str = passed_summary[-1].strip("=") if passed_summary else "all tests passed"
        return True, f"Pytest suite passed: {summary_str.strip()}."
    except Exception as e:
        return False, f"Failed to execute pytest: {e}"


def gate_4_headless_apptest(root_dir: Path) -> Tuple[bool, str]:
    """Gate 4: Headless Streamlit AppTest across load, tab switches, and widget interactions."""
    try:
        from streamlit.testing.v1 import AppTest

        app_file = str(root_dir / "app.py")
        at = AppTest.from_file(app_file, default_timeout=30)
        at.run()

        if at.exception:
            return False, f"AppTest initial load failed with exceptions: {at.exception}"

        # 1. Streamer Mode Toggle interaction
        streamer_boxes = [cb for cb in at.checkbox if "Streamer" in cb.label]
        if streamer_boxes:
            streamer_boxes[0].check().run()
            if at.exception:
                return False, f"AppTest exception on streamer mode enable: {at.exception}"
            streamer_boxes[0].uncheck().run()
            if at.exception:
                return False, f"AppTest exception on streamer mode disable: {at.exception}"

        # 2. Exclude Pre-Tracking Baseline toggle interaction
        pretrack_boxes = [cb for cb in at.checkbox if "Pre-Tracking" in cb.label]
        if pretrack_boxes:
            pretrack_boxes[0].check().run()
            if at.exception:
                return False, f"AppTest exception on pre-tracking exclude: {at.exception}"
            pretrack_boxes[0].uncheck().run()
            if at.exception:
                return False, f"AppTest exception on pre-tracking uncheck: {at.exception}"

        # 3. Dynamic metric checks (verify no hardcoded 38+ string and dynamic Sovereign Nations)
        country_metrics = [m for m in at.metric if m.label == "Identified Nations"]
        if country_metrics:
            val = str(country_metrics[0].value)
            if "38+" in val:
                return False, f"Gate 4 failed: Identified Nations still displays hardcoded '38+' string: {val}"
            if "Sovereign Nations" not in val:
                return False, f"Gate 4 failed: Expected dynamic 'Sovereign Nations' in Identified Nations, got {val}"

        # 4. Version Analytics Source radio interaction
        source_radios = [r for r in at.radio if "Analytics Source" in r.label]
        if source_radios:
            radio = source_radios[0]
            raw_opt = [o for o in radio.options if "Raw" in o]
            enriched_opt = [o for o in radio.options if "Enriched" in o]
            if raw_opt:
                radio.set_value(raw_opt[0]).run()
                if at.exception:
                    return False, f"AppTest exception on switching to Raw version mode: {at.exception}"
            if enriched_opt:
                radio.set_value(enriched_opt[0]).run()
                if at.exception:
                    return False, f"AppTest exception on switching to Enriched version mode: {at.exception}"

        # 5. Catalog View Mode radio interaction (Deep-Dive & Matrix)
        view_radios = [r for r in at.radio if "Catalog View Mode" in r.label]
        if view_radios:
            vr = view_radios[0]
            deep_opts = [o for o in vr.options if "Deep-Dive" in o]
            matrix_opts = [o for o in vr.options if "Matrix" in o]
            if deep_opts:
                vr.set_value(deep_opts[0]).run()
                if at.exception:
                    return False, f"AppTest exception on switching to Deep-Dive view: {at.exception}"
                # Test project selectbox
                inspect_sbs = [sb for sb in at.selectbox if "Select Project to Inspect" in sb.label]
                if inspect_sbs and len(inspect_sbs[0].options) > 1:
                    inspect_sbs[0].set_value(inspect_sbs[0].options[1]).run()
                    if at.exception:
                        return False, f"AppTest exception on selectbox selection: {at.exception}"
            if matrix_opts:
                vr.set_value(matrix_opts[0]).run()
                if at.exception:
                    return False, f"AppTest exception on returning to Matrix view: {at.exception}"

        # 6. Geography controls interaction
        geo_radios = [r for r in at.radio if "Display Metric" in r.label]
        if geo_radios:
            geo_radios[0].set_value("Playtime (Hours)").run()
            if at.exception:
                return False, f"AppTest exception on switching geography metric: {at.exception}"
            geo_radios[0].set_value("Downloads").run()
            if at.exception:
                return False, f"AppTest exception on switching back geography metric: {at.exception}"

        log_cbs = [cb for cb in at.checkbox if "Logarithmic" in cb.label]
        if log_cbs:
            log_cbs[0].check().run()
            if at.exception:
                return False, f"AppTest exception on checking logarithmic scale: {at.exception}"
            log_cbs[0].uncheck().run()
            if at.exception:
                return False, f"AppTest exception on unchecking logarithmic scale: {at.exception}"

        return True, "Headless AppTest passed initial run, pre-tracking toggle, dynamic metrics, and all widget permutations cleanly (0 exceptions)."
    except Exception as e:
        return False, f"AppTest execution error: {e}"


def gate_5_local_subprocess_smoke_test(root_dir: Path) -> Tuple[bool, str]:
    """Gate 5: Spawns local Streamlit subprocess and polls /_stcore/health endpoint."""
    port = 8599
    health_url = f"http://localhost:{port}/_stcore/health"
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.headless=true",
        f"--server.port={port}",
        "--browser.gatherUsageStats=false",
    ]

    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(root_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        start_time = time.time()
        timeout_seconds = 15.0
        connected = False
        status_code = None

        while time.time() - start_time < timeout_seconds:
            # Check if process crashed prematurely
            ret = proc.poll()
            if ret is not None:
                stdout, stderr = proc.communicate()
                return False, f"Streamlit server exited prematurely with code {ret}.\nStderr: {stderr.decode()}"

            try:
                with urllib.request.urlopen(health_url, timeout=2.0) as resp:
                    status_code = resp.status
                    if resp.status == 200:
                        connected = True
                        break
            except (urllib.error.URLError, ConnectionRefusedError, TimeoutError, OSError):
                time.sleep(0.5)

        if not connected:
            return False, f"Failed to receive HTTP 200 OK from {health_url} within {timeout_seconds}s"

        return True, f"Streamlit server healthy at {health_url} (HTTP {status_code} OK)."
    except Exception as e:
        return False, f"Subprocess smoke test exception: {e}"
    finally:
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass


def main() -> int:
    """Execute all 5 verification gates and present results."""
    root_dir = Path(__file__).resolve().parent

    print_banner("MODRINTH CREATOR ANALYTICS -- 5-GATE VERIFICATION SUITE")
    print(f"Working Directory : {root_dir}")
    print(f"Python Executable : {sys.executable}")
    print(f"Python Version    : {sys.version.split()[0]}")

    gates = [
        ("Gate 1: Bytecode Compilation", gate_1_bytecode_compilation),
        ("Gate 2: Dataset Integrity & Enrichment Check", gate_2_dataset_integrity),
        ("Gate 3: Pytest Execution (23+ Unit & App Tests)", gate_3_pytest_execution),
        ("Gate 4: Headless Streamlit AppTest Verification", gate_4_headless_apptest),
        ("Gate 5: Local Streamlit Subprocess Smoke Test", gate_5_local_subprocess_smoke_test),
    ]

    results: List[Tuple[str, bool, str, float]] = []
    overall_success = True

    for title, gate_fn in gates:
        print(f"\n[RUNNING] {title}...")
        t0 = time.perf_counter()
        passed, details = gate_fn(root_dir)
        elapsed = time.perf_counter() - t0
        results.append((title, passed, details, elapsed))

        status_tag = "PASS" if passed else "FAIL"
        print(f"[{status_tag}] {title} ({elapsed:.2f}s): {details}")

        if not passed:
            overall_success = False

    # Summary Table
    print_banner("VERIFICATION SUMMARY BANNER")
    print(f"{'Gate Name':<45} | {'Status':<6} | {'Duration':<8}")
    print("-" * 70)
    total_time = 0.0
    for title, passed, _, elapsed in results:
        status_str = "PASS" if passed else "FAIL"
        print(f"{title:<45} | {status_str:<6} | {elapsed:>6.2f}s")
        total_time += elapsed
    print("-" * 70)
    print(f"{'Total Verification Duration':<45} | {'':<6} | {total_time:>6.2f}s")

    if overall_success:
        print("\n>>> ALL 5 GATES PASSED (100% GREEN) -- STUDIO PRODUCTION READY <<<")
        return 0
    else:
        print("\n>>> VERIFICATION FAILED -- INSPECT FAILED GATES ABOVE <<<")
        return 1


if __name__ == "__main__":
    sys.exit(main())
