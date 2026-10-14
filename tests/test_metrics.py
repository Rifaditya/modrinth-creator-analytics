"""Unit and integration tests for metrics calculations, filtering, and charts."""

import pytest
import pandas as pd

from src.loader import ModrinthDataBundle, load_all_data
from src.metrics import (
    calculate_kpis,
    calculate_source_kpis,
    calculate_version_kpis,
    filter_bundle_by_date,
    project_milestone_earnings,
)
from src.charts import (
    render_daily_downloads_chart,
    render_download_reasons_chart,
    render_download_sources_chart,
    render_game_version_timeline_chart,
    render_game_versions_chart,
    render_loader_donut_chart,
    render_monetization_donut_chart,
    render_revenue_velocity_chart,
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


def test_calculate_source_kpis(bundle: ModrinthDataBundle):
    """Verify acquisition source KPIs match empirical Modrinth telemetry."""
    src = calculate_source_kpis(bundle.download_source, bundle.download_reason)

    assert src["total_source_downloads"] == 100226
    assert src["modrinth_app_downloads"] == 44055
    assert abs(src["modrinth_app_pct"] - 43.955) < 0.01

    assert src["modrinth_website_downloads"] == 17845
    assert abs(src["modrinth_website_pct"] - 17.804) < 0.01

    assert src["prism_launcher_downloads"] == 16332
    assert abs(src["prism_launcher_pct"] - 16.295) < 0.01

    assert src["native_channels_downloads"] == 44055 + 17845
    assert abs(src["native_channels_pct"] - 61.76) < 0.02

    assert src["ecosystem_downloads"] == 28031
    assert abs(src["ecosystem_pct"] - 27.967) < 0.01


def test_calculate_version_kpis(bundle: ModrinthDataBundle):
    """Verify version demographics calculations for both enriched and raw modes."""
    # Enriched Mode
    enriched = calculate_version_kpis(
        bundle.game_version, bundle.project_version, use_enriched=True
    )
    assert enriched["total_version_downloads"] == 100226
    assert enriched["lead_downloads"] == 32556
    assert abs(enriched["lead_pct"] - 32.48) < 0.02
    assert enriched["modern_26x_downloads"] == 92541
    assert abs(enriched["modern_26x_pct"] - 92.33) < 0.02
    assert enriched["legacy_downloads"] == 7492
    assert abs(enriched["legacy_pct"] - 7.47) < 0.02
    assert enriched["unknown_downloads"] == 189

    # Raw Mode
    raw = calculate_version_kpis(
        bundle.game_version, bundle.project_version, use_enriched=False
    )
    assert raw["total_version_downloads"] == 100226
    assert raw["lead_downloads"] == 33832
    assert abs(raw["lead_pct"] - 33.75) < 0.02
    assert raw["modern_26x_downloads"] == 57487
    assert abs(raw["modern_26x_pct"] - 57.35) < 0.02
    assert raw["legacy_downloads"] == 3956
    assert abs(raw["legacy_pct"] - 3.94) < 0.02
    assert raw["unknown_downloads"] == 38775


def test_charts_render_cleanly(bundle: ModrinthDataBundle):
    """Verify Plotly figure rendering functions generate valid figures."""
    # Tab 1 charts
    fig_rev = render_revenue_velocity_chart(bundle.member)
    assert fig_rev is not None
    assert len(fig_rev.data) == 2  # Bar and Scatter traces

    fig_donut = render_monetization_donut_chart(bundle.monetization)
    assert fig_donut is not None
    assert len(fig_donut.data) == 1  # Pie trace

    fig_dls = render_daily_downloads_chart(bundle.project)
    assert fig_dls is not None
    assert len(fig_dls.data) == 1  # Scatter area trace

    # Tab 2 charts
    fig_sources = render_download_sources_chart(bundle.download_source)
    assert fig_sources is not None
    assert len(fig_sources.data) == 1  # Horizontal bar

    fig_reasons = render_download_reasons_chart(bundle.download_reason)
    assert fig_reasons is not None
    assert len(fig_reasons.data) == 1  # Pie donut

    # Tab 3 charts
    fig_ver_enriched = render_game_versions_chart(
        bundle.game_version, bundle.project_version, use_enriched=True
    )
    assert fig_ver_enriched is not None
    assert len(fig_ver_enriched.data) == 1  # Vertical bar

    fig_ver_raw = render_game_versions_chart(
        bundle.game_version, bundle.project_version, use_enriched=False
    )
    assert fig_ver_raw is not None
    assert len(fig_ver_raw.data) == 1

    fig_timeline = render_game_version_timeline_chart(
        bundle.project_version, version_col="Target Game Version"
    )
    assert fig_timeline is not None
    assert len(fig_timeline.data) >= 1  # Stacked area traces

    fig_loader = render_loader_donut_chart(bundle.loader)
    assert fig_loader is not None
    assert len(fig_loader.data) == 1  # Donut trace


def test_empty_dataframe_chart_resilience():
    """Verify chart functions handle empty DataFrames gracefully without crashing."""
    empty_df = pd.DataFrame()
    fig1 = render_revenue_velocity_chart(empty_df)
    fig2 = render_monetization_donut_chart(empty_df)
    fig3 = render_daily_downloads_chart(empty_df)
    fig4 = render_download_sources_chart(empty_df)
    fig5 = render_download_reasons_chart(empty_df)
    fig6 = render_game_versions_chart(empty_df)
    fig7 = render_game_version_timeline_chart(empty_df)
    fig8 = render_loader_donut_chart(empty_df)

    for fig in [fig1, fig2, fig3, fig4, fig5, fig6, fig7, fig8]:
        assert fig is not None
