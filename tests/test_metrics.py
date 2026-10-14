"""Unit and integration tests for metrics calculations, filtering, and charts."""

import pytest
import pandas as pd

from src.loader import ModrinthDataBundle, load_all_data
from src.metrics import (
    calculate_country_summary,
    calculate_kpis,
    calculate_project_summary,
    calculate_rolling_rpm,
    calculate_source_kpis,
    calculate_version_kpis,
    calculate_view_monetization,
    filter_bundle_by_date,
    project_milestone_earnings,
)
from src.charts import (
    render_daily_downloads_chart,
    render_dependent_modpacks_chart,
    render_download_reasons_chart,
    render_download_sources_chart,
    render_game_version_timeline_chart,
    render_game_versions_chart,
    render_loader_donut_chart,
    render_monetization_donut_chart,
    render_project_leaderboard_chart,
    render_project_version_adoption_chart,
    render_revenue_velocity_chart,
    render_single_project_velocity,
    render_top_countries_bar_chart,
    render_world_choropleth_map,
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

    # View monetization and trailing 30d RPMs (A4, A5)
    assert kpis["monetized_views"] == 25140
    assert kpis["unmonetized_views"] == 12739
    assert abs(kpis["monetized_view_rpm"] - 1.1694) < 0.005
    assert abs(kpis["blended_view_rpm"] - 0.7761) < 0.005
    assert kpis["trailing_30d_blended_rpm"] > 0.0
    assert kpis["trailing_30d_monetized_rpm"] > 0.0


def test_calculate_rolling_rpm(bundle: ModrinthDataBundle):
    """Verify rolling RPM calculation produces expected columns and non-null values."""
    rolling_df = calculate_rolling_rpm(
        bundle.member, bundle.project, bundle.monetization, window_days=30
    )

    expected_cols = [
        "Date",
        "Rolling Revenue",
        "Rolling Downloads",
        "Rolling Monetized Downloads",
        "Rolling Blended RPM",
        "Rolling Monetized RPM",
    ]
    assert list(rolling_df.columns) == expected_cols
    assert len(rolling_df) > 30

    # First 6 days are null due to min_periods=7
    assert rolling_df.iloc[:6]["Rolling Revenue"].isna().all()
    assert rolling_df.iloc[:6]["Rolling Downloads"].isna().all()

    # From 7th day onward (index 6+), all values should be non-null
    steady_state = rolling_df.iloc[6:]
    for col in expected_cols[1:]:
        assert not steady_state[col].isna().any(), f"Column {col} has unexpected NaN values"

    # Verify latest rolling rates are within plausible Modrinth bounds
    latest = rolling_df.iloc[-1]
    assert 0.10 <= latest["Rolling Blended RPM"] <= 2.0
    assert 1.0 <= latest["Rolling Monetized RPM"] <= 10.0

    # Empty input resilience
    empty_df = pd.DataFrame()
    empty_res = calculate_rolling_rpm(empty_df, empty_df, empty_df)
    assert list(empty_res.columns) == expected_cols
    assert empty_res.empty


def test_calculate_view_monetization(bundle: ModrinthDataBundle):
    """Verify view-based monetization indicators and view RPM metrics (A5)."""
    res = calculate_view_monetization(bundle.monetization, bundle.member)

    assert res["monetized_views"] == 25140
    assert res["unmonetized_views"] == 12739
    assert res["total_views"] == 25140 + 12739
    assert abs(res["total_revenue"] - 29.3994) < 0.005

    # Monetized view RPM ~ $1.169 / 1k monetized views
    assert abs(res["monetized_view_rpm"] - 1.1694) < 0.005

    # Blended view RPM ~ $0.776 / 1k total views
    assert abs(res["blended_view_rpm"] - 0.7761) < 0.005

    # Empty input resilience
    empty_res = calculate_view_monetization(pd.DataFrame(), pd.DataFrame())
    assert empty_res["monetized_views"] == 0
    assert empty_res["monetized_view_rpm"] == 0.0
    assert empty_res["blended_view_rpm"] == 0.0


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
    """Verify earnings forecaster output with conservative and optimistic scenarios (A4)."""
    target_dls = 500_000
    blended_rpm = 0.2933315
    monetized_rpm = 2.9520476
    monetization_rate = 9.9365434

    # Baseline scenario with trailing_30d_rpm=None
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

    # Verify conservative earnings (blended * 0.85 fallback) and optimistic earnings (1.25x)
    assert proj["conservative_earnings"] < proj["projected_blended_earnings"]
    assert abs(proj["conservative_earnings"] - (146.66575 * 0.85)) < 0.1
    assert proj["optimistic_earnings"] > proj["projected_blended_earnings"]
    assert abs(proj["optimistic_earnings"] - (146.66575 * 1.25)) < 0.1

    # Scenario with explicit trailing 30d RPM ($0.26 / 1k DLs)
    proj_trailing = project_milestone_earnings(
        target_downloads=target_dls,
        blended_rpm=blended_rpm,
        monetized_rpm=monetized_rpm,
        monetization_rate=monetization_rate,
        trailing_30d_rpm=0.26,
    )
    assert abs(proj_trailing["conservative_earnings"] - 130.0) < 0.01
    assert abs(proj_trailing["optimistic_earnings"] - (146.66575 * 1.25)) < 0.1


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
    assert enriched["lead_downloads"] == 28722
    assert abs(enriched["lead_pct"] - 28.66) < 0.02
    assert enriched["modern_26x_downloads"] == 89777
    assert abs(enriched["modern_26x_pct"] - 89.57) < 0.02
    assert enriched["legacy_downloads"] == 4414
    assert abs(enriched["legacy_pct"] - 4.40) < 0.02
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


def test_calculate_project_summary(bundle: ModrinthDataBundle):
    """Verify project catalog summary calculation matches ground truth metrics (A6)."""
    proj_summary = calculate_project_summary(bundle.project)

    assert len(proj_summary) == 21, f"Expected 21 projects, got {len(proj_summary)}"
    assert proj_summary["Downloads"].sum() == 100226

    # Verify descending sort: Dasik Library first, VO: Better Dogs second
    assert proj_summary.iloc[0]["Project"] == "Dasik Library"
    assert proj_summary.iloc[0]["Downloads"] == 41167
    assert abs(proj_summary.iloc[0]["Share %"] - 41.07) < 0.1

    assert proj_summary.iloc[1]["Project"] == "VO: Better Dogs"
    assert proj_summary.iloc[1]["Downloads"] == 31034

    # Verify Share % sums to 100%
    assert abs(proj_summary["Share %"].sum() - 100.0) < 0.01

    # Verify Playtime and conversion rate are computed
    assert proj_summary["Playtime (Hours)"].sum() > 500
    assert (proj_summary["Conversion Rate %"] > 0).all()

    # Verify Downloads per View (x) exists and Dasik Library exceeds 1.0x (A6)
    assert "Downloads per View (x)" in proj_summary.columns
    dasik_dpv = proj_summary.iloc[0]["Downloads per View (x)"]
    assert dasik_dpv > 1.0
    assert abs(dasik_dpv - 11.40) < 0.05

    # Verify VO: Better Dogs has ~2.16x downloads per view
    dogs_dpv = proj_summary.iloc[1]["Downloads per View (x)"]
    assert abs(dogs_dpv - 2.16) < 0.05

    # Verify backward-compatible alias relationship
    assert abs(proj_summary.iloc[0]["Conversion Rate %"] - dasik_dpv * 100.0) < 1e-6


def test_calculate_country_summary(bundle: ModrinthDataBundle):
    """Verify geographic country telemetry calculations and KPIs (A2)."""
    # When calibrated against total bundle downloads
    summary_df, kpis = calculate_country_summary(
        bundle.country, total_bundle_downloads=100226
    )

    assert len(summary_df) == 9
    assert kpis["total_downloads"] == 100226
    assert kpis["other_downloads"] == 76315
    assert abs(kpis["other_pct"] - 76.14) < 0.1

    assert kpis["identified_downloads"] == 23911
    assert abs(kpis["identified_pct"] - 23.86) < 0.1

    assert kpis["top_country"] == "United States"
    assert kpis["top_country_downloads"] == 20381
    assert abs(kpis["top_country_pct"] - 20.33) < 0.1

    # Dynamic calculation evaluates to exactly 8 sovereign nations (A2)
    assert kpis["identified_countries_count"] == 8

    # When run without total_bundle_downloads, fallback to country table sum
    raw_summary, raw_kpis = calculate_country_summary(bundle.country)
    assert raw_kpis["country_table_downloads"] == 97551
    assert raw_kpis["top_country"] == "United States"
    assert raw_kpis["top_country_downloads"] == 20381
    assert raw_kpis["identified_countries_count"] == 8

    # Empty DataFrame check
    empty_df = pd.DataFrame()
    _, empty_kpis = calculate_country_summary(empty_df)
    assert empty_kpis["total_downloads"] == 0
    assert empty_kpis["top_country"] == "None"


def test_tab4_and_tab5_charts_render_cleanly(bundle: ModrinthDataBundle):
    """Verify Tab 4 and Tab 5 chart rendering functions generate valid figures."""
    proj_summary = calculate_project_summary(bundle.project)

    # Tab 4 charts
    fig_lead = render_project_leaderboard_chart(proj_summary)
    assert fig_lead is not None
    assert len(fig_lead.data) == 1

    fig_dep = render_dependent_modpacks_chart(bundle.dependent_project)
    assert fig_dep is not None
    assert len(fig_dep.data) == 1

    fig_vel = render_single_project_velocity(bundle.project, "Dasik Library")
    assert fig_vel is not None
    assert len(fig_vel.data) == 1

    fig_ver = render_project_version_adoption_chart(
        bundle.project_version, "Dasik Library"
    )
    assert fig_ver is not None
    assert len(fig_ver.data) == 1

    # Tab 5 charts
    fig_map_dl = render_world_choropleth_map(
        bundle.country, metric="Downloads", use_log=False
    )
    assert fig_map_dl is not None
    assert len(fig_map_dl.data) == 1

    fig_map_log = render_world_choropleth_map(
        bundle.country, metric="Downloads", use_log=True
    )
    assert fig_map_log is not None

    fig_map_play = render_world_choropleth_map(
        bundle.country, metric="Playtime (Hours)", use_log=False
    )
    assert fig_map_play is not None

    fig_top_c = render_top_countries_bar_chart(bundle.country, metric="Downloads")
    assert fig_top_c is not None
    assert len(fig_top_c.data) == 1

    fig_top_play = render_top_countries_bar_chart(
        bundle.country, metric="Playtime (Hours)"
    )
    assert fig_top_play is not None
    assert len(fig_top_play.data) == 1


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
    fig9 = render_project_leaderboard_chart(empty_df)
    fig10 = render_dependent_modpacks_chart(empty_df)
    fig11 = render_single_project_velocity(empty_df, "Dasik Library")
    fig12 = render_project_version_adoption_chart(empty_df, "Dasik Library")
    fig13 = render_world_choropleth_map(empty_df)
    fig14 = render_top_countries_bar_chart(empty_df)

    for fig in [
        fig1,
        fig2,
        fig3,
        fig4,
        fig5,
        fig6,
        fig7,
        fig8,
        fig9,
        fig10,
        fig11,
        fig12,
        fig13,
        fig14,
    ]:
        assert fig is not None

