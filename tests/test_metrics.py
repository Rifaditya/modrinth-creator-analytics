"""Unit and integration tests for metrics calculations, filtering, and charts."""

import pytest
import pandas as pd

from src.loader import ModrinthDataBundle, load_all_data
from src.metrics import (
    calculate_kpis,
    filter_bundle_by_date,
    project_milestone_earnings,
)
from src.charts import (
    render_revenue_velocity_chart,
    render_monetization_donut_chart,
    render_daily_downloads_chart,
)


@pytest.fixture(scope="module")
def bundle() -> ModrinthDataBundle:
    """Fixture providing loaded Modrinth analytics bundle."""
    return load_all_data()


def test_calculate_kpis_parity(bundle: ModrinthDataBundle):
    """Verify calculated KPIs match baseline ground truth numbers."""
    kpis = calculate_kpis(bundle)

    # Total Revenue should be ~29.3994
    assert abs(kpis["total_revenue"] - 29.3994) < 0.005, (
        f"Expected revenue ~29.3994, got {kpis['total_revenue']}"
    )

    # Total Downloads should be exactly 100,226
    assert kpis["total_downloads"] == 100226, (
        f"Expected 100,226 downloads, got {kpis['total_downloads']}"
    )

    # Blended RPM should be ~0.2933 ($0.29 per 1k DLs)
    assert abs(kpis["blended_rpm"] - 0.2933) < 0.005, (
        f"Expected blended RPM ~0.2933, got {kpis['blended_rpm']}"
    )

    # Monetized RPM should be ~2.9518-2.9520 ($2.95 per 1k monetized DLs)
    assert abs(kpis["monetized_rpm"] - 2.9518) < 0.01, (
        f"Expected monetized RPM ~2.9518, got {kpis['monetized_rpm']}"
    )

    # Monetized and unmonetized download totals
    assert kpis["monetized_downloads"] == 9959
    assert kpis["unmonetized_downloads"] == 90267
    assert abs(kpis["monetization_rate"] - 9.9365) < 0.01

    # Playtime metrics
    assert kpis["total_playtime_seconds"] == 3776257
    assert kpis["total_playtime_hours"] > 1000
    assert kpis["avg_playtime_per_download_min"] > 0.5


def test_filter_bundle_by_date(bundle: ModrinthDataBundle):
    """Verify filter_bundle_by_date produces valid date-bounded subset slices."""
    start_date = "2026-05-01"
    end_date = "2026-05-31"

    filtered = filter_bundle_by_date(bundle, start_date=start_date, end_date=end_date)

    # Verify every table with Date column is bounded
    for name, df in filtered.as_dict().items():
        if "Date" in df.columns and not df.empty:
            assert df["Date"].min() >= pd.Timestamp(start_date)
            assert df["Date"].max() <= pd.Timestamp(end_date)
            # Row count should be strictly smaller than full bundle
            assert len(df) < len(bundle[name]), f"{name} was not filtered down"

    # Member table in May 2026 has exactly 31 daily rows
    assert len(filtered.member) == 31


def test_project_milestone_earnings():
    """Verify earnings forecaster output with 500,000 target downloads."""
    target_dls = 500_000
    blended_rpm = 0.2933315
    monetized_rpm = 2.9520476
    monetization_rate = 9.9365434

    proj = project_milestone_earnings(
        target_downloads=target_dls,
        blended_rpm=blended_rpm,
        monetized_rpm=monetized_rpm,
        monetization_rate=monetization_rate,
    )

    assert proj["target_downloads"] == 500_000.0
    # Projected earnings should be approx $146.66
    assert abs(proj["projected_blended_earnings"] - 146.66) < 0.1
    assert abs(proj["projected_monetized_earnings"] - 146.66) < 0.1
    # Projected monetized downloads should be approx 49,682
    assert abs(proj["projected_monetized_downloads"] - 49682.7) < 1.0


def test_charts_render_cleanly(bundle: ModrinthDataBundle):
    """Verify Plotly figure rendering functions generate valid figures."""
    fig_rev = render_revenue_velocity_chart(bundle.member)
    assert fig_rev is not None
    assert len(fig_rev.data) == 2  # Bar and Scatter traces

    fig_donut = render_monetization_donut_chart(bundle.monetization)
    assert fig_donut is not None
    assert len(fig_donut.data) == 1  # Pie trace

    fig_dls = render_daily_downloads_chart(bundle.project)
    assert fig_dls is not None
    assert len(fig_dls.data) == 1  # Scatter area trace


def test_empty_dataframe_chart_resilience():
    """Verify chart functions handle empty DataFrames gracefully without crashing."""
    empty_df = pd.DataFrame()
    fig1 = render_revenue_velocity_chart(empty_df)
    fig2 = render_monetization_donut_chart(empty_df)
    fig3 = render_daily_downloads_chart(empty_df)

    assert fig1 is not None
    assert fig2 is not None
    assert fig3 is not None
