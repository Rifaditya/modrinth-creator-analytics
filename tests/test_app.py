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
