"""Headless test suite verifying app.py runs cleanly via Streamlit AppTest."""

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest


@pytest.fixture
def app_path() -> str:
    """Return absolute path to app.py."""
    return str(Path(__file__).resolve().parent.parent / "app.py")


def test_app_runs_cleanly(app_path: str):
    """Verify app.py loads, renders all default widgets, and completes with 0 exceptions."""
    at = AppTest.from_file(app_path, default_timeout=30)
    at.run()

    assert not at.exception, f"AppTest encountered exceptions: {at.exception}"

    # Verify metric cards are present
    assert len(at.metric) >= 4, f"Expected at least 4 metrics, got {len(at.metric)}"

    # Verify slider exists
    assert len(at.slider) >= 1, "Milestone slider was not rendered"


def test_app_streamer_mode_toggle(app_path: str):
    """Verify toggling streamer mode masks revenue without causing runtime errors."""
    at = AppTest.from_file(app_path, default_timeout=30)
    at.run()

    # Find the streamer mode checkbox in sidebar
    checkboxes = [cb for cb in at.checkbox if "Streamer" in cb.label]
    assert len(checkboxes) == 1, "Streamer mode checkbox not found"

    # Toggle streamer mode on
    checkboxes[0].check().run()
    assert not at.exception, f"Exceptions after toggling streamer mode: {at.exception}"

    # Verify masked text appears in metric values
    metric_values = [m.value for m in at.metric]
    has_masked = any("••••" in str(v) for v in metric_values)
    assert has_masked, f"Expected masked values in metrics, got {metric_values}"


def test_app_tab2_and_tab3_metrics(app_path: str):
    """Verify Tab 2 (Launchers & Sources) and Tab 3 (Demographics) metrics render cleanly."""
    at = AppTest.from_file(app_path, default_timeout=30)
    at.run()

    assert not at.exception, f"AppTest encountered exceptions: {at.exception}"
    assert len(at.metric) >= 15, f"Expected at least 15 metrics across tabs, got {len(at.metric)}"

    metric_dict = {m.label: m.value for m in at.metric}

    # Tab 2 metrics verification
    assert "Primary Launcher" in metric_dict
    assert "44,055" in metric_dict["Primary Launcher"]

    assert "Web Direct" in metric_dict
    assert "17,845" in metric_dict["Web Direct"]

    assert "Community Launchers" in metric_dict
    assert "16,332" in metric_dict["Community Launchers"]

    assert "Ecosystem Distribution" in metric_dict
    assert "28,031" in metric_dict["Ecosystem Distribution"]

    # Tab 3 metrics verification (Enriched Engine default)
    assert "Sovereign Lead Anchor" in metric_dict
    assert "32,556 DLs" in metric_dict["Sovereign Lead Anchor"]

    assert "Modern Anchors (26.x)" in metric_dict
    assert "92,541 DLs" in metric_dict["Modern Anchors (26.x)"]

    assert "Legacy LTS Anchors" in metric_dict
    assert "7,492 DLs" in metric_dict["Legacy LTS Anchors"]

    assert "Primary Mod Loader" in metric_dict
    assert "Fabric Dominant" in metric_dict["Primary Mod Loader"]


def test_app_version_mode_toggle(app_path: str):
    """Verify switching between Enriched Engine and Raw Telemetry updates metrics dynamically."""
    at = AppTest.from_file(app_path, default_timeout=30)
    at.run()

    # Find the version source radio toggle
    radios = [r for r in at.radio if "Analytics Source" in r.label]
    assert len(radios) == 1, "Analytics Source radio toggle not found"
    radio = radios[0]

    raw_option = [opt for opt in radio.options if "Raw" in opt][0]
    enriched_option = [opt for opt in radio.options if "Enriched" in opt][0]

    # Switch to Raw Modrinth Telemetry
    radio.set_value(raw_option).run()
    assert not at.exception, f"Exceptions after switching to Raw mode: {at.exception}"

    raw_metrics = {m.label: m.value for m in at.metric}
    assert "33,832 DLs" in raw_metrics["Sovereign Lead Anchor"]
    assert "57,487 DLs" in raw_metrics["Modern Anchors (26.x)"]
    assert "3,956 DLs" in raw_metrics["Legacy LTS Anchors"]

    # Switch back to Enriched Engine
    radio.set_value(enriched_option).run()
    assert not at.exception, f"Exceptions after returning to Enriched mode: {at.exception}"

    enriched_metrics = {m.label: m.value for m in at.metric}
    assert "32,556 DLs" in enriched_metrics["Sovereign Lead Anchor"]
    assert "92,541 DLs" in enriched_metrics["Modern Anchors (26.x)"]
    assert "7,492 DLs" in enriched_metrics["Legacy LTS Anchors"]
