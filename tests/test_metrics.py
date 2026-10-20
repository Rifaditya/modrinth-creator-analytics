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
    render_bingeability_index_chart,
    render_country_engagement_quadrant,
    render_daily_downloads_chart,
    render_dependency_flywheel_chart,
    render_dependent_modpacks_chart,
    render_download_reasons_chart,
    render_download_sources_chart,
    render_ecosystem_correlation_heatmap,
    render_engagement_index_chart,
    render_game_version_timeline_chart,
    render_game_versions_chart,
    render_growth_waterfall,
    render_intent_mix_timeline,
    render_launcher_evolution_timeline,
    render_loader_donut_chart,
    render_modpack_virality_timeline,
    render_monetization_donut_chart,
    render_monetization_quadrant,
    render_naming_linguistics_scatter,
    render_pareto_curve,
    render_pillar_architecture_chart,
    render_project_leaderboard_chart,
    render_project_revenue_attribution_chart,
    render_project_version_adoption_chart,
    render_project_version_matrix_heatmap,
    render_release_cadence_regression_chart,
    render_revenue_velocity_chart,
    render_revenue_vs_views_scatter,
    render_rolling_rpm_trend,
    render_seasonality_heatmap,
    render_single_project_velocity,
    render_spike_attribution_chart,
    render_telemetry_coverage_chart,
    render_top_countries_bar_chart,
    render_us_traffic_diagnostic,
    render_version_disambiguation_bridge_chart,
    render_version_uptake_chart,
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
    assert enriched["modern_26x_downloads"] == 89791
    assert abs(enriched["modern_26x_pct"] - 89.59) < 0.02
    assert enriched["legacy_downloads"] == 4414
    assert abs(enriched["legacy_pct"] - 4.40) < 0.02
    assert enriched["unknown_downloads"] == 179

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
    assert len(fig_rev.data) == 3  # Daily Bar, 7D Rolling Avg, and Cumulative Scatter traces

    fig_donut = render_monetization_donut_chart(bundle.monetization)
    assert fig_donut is not None
    assert len(fig_donut.data) == 1  # Pie trace

    fig_dls = render_daily_downloads_chart(bundle.project)
    assert fig_dls is not None
    assert len(fig_dls.data) == 2  # Daily Scatter area + 7D Rolling Avg trace

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
    assert len(fig_vel.data) == 3  # Daily Downloads, 7D Rolling Avg, Cumulative S-Curve

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


def test_b1_b2_charts_render_cleanly(bundle: ModrinthDataBundle):
    """Verify B1 (telemetry coverage) and B2 (revenue drivers & rolling RPM) charts render cleanly."""
    fig_telemetry = render_telemetry_coverage_chart(bundle)
    assert fig_telemetry is not None
    # 6 tracking dimensions: Game Version, Mod Loader, Geography, Download Reason, Dependent Project, Download Source
    assert len(fig_telemetry.data) == 6
    for trace in fig_telemetry.data:
        assert len(trace.x) > 0
        assert len(trace.y) > 0

    fig_scatter = render_revenue_vs_views_scatter(bundle.monetization, bundle.member)
    assert fig_scatter is not None
    # 2 traces: Scatter observations + OLS linear trendline
    assert len(fig_scatter.data) == 2

    rolling_df = calculate_rolling_rpm(
        bundle.member, bundle.project, bundle.monetization, window_days=30
    )
    fig_rpm = render_rolling_rpm_trend(rolling_df)
    assert fig_rpm is not None
    # 2 traces: Rolling Monetized RPM + Rolling Blended RPM
    assert len(fig_rpm.data) == 2


def test_b3_b4_b5_charts_render_cleanly(bundle: ModrinthDataBundle):
    """Verify B3 (monetization quadrant), B4 (dependency flywheel), and B5 (intent dynamics) render cleanly."""
    # B3: Monetization Asymmetry Quadrant
    proj_summary = calculate_project_summary(bundle.project)
    fig_quadrant = render_monetization_quadrant(proj_summary)
    assert fig_quadrant is not None
    # 2 traces: Parity line + Projects scatter
    assert len(fig_quadrant.data) == 2
    # At least 4 annotations: Better Dogs, Dasik Library, and 2 quadrant badges
    assert len(fig_quadrant.layout.annotations) >= 4

    # Better Dogs should have higher revenue share than download share
    bd = proj_summary[proj_summary["Project"] == "VO: Better Dogs"].iloc[0]
    bd_rev_share = bd["Revenue"] / proj_summary["Revenue"].sum() * 100.0
    bd_dl_share = bd["Downloads"] / proj_summary["Downloads"].sum() * 100.0
    assert bd_rev_share > bd_dl_share
    assert abs(bd_rev_share - 38.44) < 0.1
    assert abs(bd_dl_share - 30.96) < 0.1

    # Dasik Library should have higher download share than revenue share
    dl = proj_summary[proj_summary["Project"] == "Dasik Library"].iloc[0]
    dl_rev_share = dl["Revenue"] / proj_summary["Revenue"].sum() * 100.0
    dl_dl_share = dl["Downloads"] / proj_summary["Downloads"].sum() * 100.0
    assert dl_dl_share > dl_rev_share
    assert abs(dl_dl_share - 41.07) < 0.1
    assert abs(dl_rev_share - 21.29) < 0.1

    # B4: Dependency Flywheel
    fig_flywheel = render_dependency_flywheel_chart(bundle.dependent_project)
    assert fig_flywheel is not None
    # 3 traces: Internal Studio Pull-Through, External Modpacks, Other / Unknown
    assert len(fig_flywheel.data) == 3
    # Verify exact volume figures match empirical telemetry
    assert list(fig_flywheel.data[0].x) == [13361, 13361]
    assert list(fig_flywheel.data[1].x) == [8067, 8067]
    assert list(fig_flywheel.data[2].x) == [0, 78642]

    # B5: Intent Dynamics Timeline
    fig_intent = render_intent_mix_timeline(bundle.download_reason)
    assert fig_intent is not None
    # 5 traces: Standalone, Update, Modpack, Dependency, Unknown
    assert len(fig_intent.data) == 5
    # Annotations for August Update peak and September Modpack surge
    assert len(fig_intent.layout.annotations) >= 2


def test_b6_b7_charts_render_cleanly(bundle: ModrinthDataBundle):
    """Verify B6 (engagement dwell-time index) and B7 (US headless traffic diagnostic) render cleanly."""
    # B6: Engagement Dwell-Time Index
    fig_engagement = render_engagement_index_chart(
        bundle.game_version, bundle.project_version
    )
    assert fig_engagement is not None
    assert len(fig_engagement.data) == 1
    trace = fig_engagement.data[0]
    assert len(trace.x) >= 4
    assert len(trace.y) >= 4

    # Verify empirical values match ground truth
    x_list = list(trace.x)
    y_list = [round(float(val), 2) for val in trace.y]
    version_to_y = dict(zip(x_list, y_list))

    assert "1.21.1" in version_to_y
    assert version_to_y["1.21.1"] == 2.49

    assert "1.20.1" in version_to_y
    assert version_to_y["1.20.1"] == 1.51

    assert "26.2" in version_to_y
    assert version_to_y["26.2"] == 1.09

    # Legacy LTS anchors exhibit higher engagement than modern 26.2
    assert version_to_y["1.21.1"] > version_to_y["26.2"]
    assert version_to_y["1.20.1"] > version_to_y["26.2"]

    # Verify annotation callout for 2.3x LTS stickiness
    assert len(fig_engagement.layout.annotations) >= 1
    annot_texts = [a.text for a in fig_engagement.layout.annotations]
    assert any("2.3x" in t for t in annot_texts)

    # B7: US Traffic Diagnostic
    fig_us_diag = render_us_traffic_diagnostic(bundle.country)
    assert fig_us_diag is not None
    # Dual subplots: 2 traces (Downloads per View & Playtime per DL)
    assert len(fig_us_diag.data) == 2

    trace_dl = fig_us_diag.data[0]
    trace_play = fig_us_diag.data[1]

    # Verify US metrics match empirical ground truth (345.4 DLs/view, 0.03 min/DL)
    us_dl_val = float(trace_dl.y[0])
    us_play_val = float(trace_play.y[0])
    assert abs(us_dl_val - 345.4) < 1.0
    assert abs(us_play_val - 0.03) < 0.01

    # Verify Global Non-US and Organic baselines
    non_us_dl_val = float(trace_dl.y[1])
    non_us_play_val = float(trace_play.y[1])
    assert abs(non_us_dl_val - 2.04) < 0.2
    assert abs(non_us_play_val - 0.81) < 0.2

    # Verify Headless anomaly annotation
    assert len(fig_us_diag.layout.annotations) >= 1
    diag_texts = [a.text for a in fig_us_diag.layout.annotations]
    assert any("Headless Modpack Server" in t for t in diag_texts)


def test_b8_b12_charts_render_cleanly(bundle: ModrinthDataBundle):
    """Verify B8-B12 econometric charts render cleanly with expected data structures and annotations."""
    # B8: Seasonality Heatmap / Day of Week
    fig_seasonality = render_seasonality_heatmap(bundle.project)
    assert fig_seasonality is not None
    assert len(fig_seasonality.data) == 1
    dow_trace = fig_seasonality.data[0]
    assert len(dow_trace.x) == 7
    # Verify Sunday is peak and greater than Friday
    dow_dict = dict(zip(dow_trace.x, dow_trace.y))
    assert "Sunday" in dow_dict and "Friday" in dow_dict
    assert dow_dict["Sunday"] > dow_dict["Friday"]
    assert abs(dow_dict["Sunday"] - 642.9) < 1.0
    assert abs(dow_dict["Friday"] - 491.7) < 1.0
    # Annotations for Friday Release rule and Sunday Peak
    assert len(fig_seasonality.layout.annotations) >= 2
    annot_texts = [a.text for a in fig_seasonality.layout.annotations]
    assert any("Release Anchor" in t for t in annot_texts)
    assert any("Weekly Peak" in t for t in annot_texts)

    # B9: Spike Detection & Anomaly Attribution
    fig_spikes = render_spike_attribution_chart(bundle.project)
    assert fig_spikes is not None
    # 3 traces: Daily volume, Rolling median line, Catalyst markers
    assert len(fig_spikes.data) == 3
    daily_trace = fig_spikes.data[0]
    median_trace = fig_spikes.data[1]
    catalyst_trace = fig_spikes.data[2]
    assert len(daily_trace.x) >= 175
    assert len(median_trace.x) >= 175
    assert len(catalyst_trace.x) == 4
    # Annotations for key catalysts
    assert len(fig_spikes.layout.annotations) >= 4
    spike_annots = [a.text for a in fig_spikes.layout.annotations]
    assert any("Catalog Indexing" in t for t in spike_annots)
    assert any("Monetization Transition" in t for t in spike_annots)
    assert any("Sensible MC" in t for t in spike_annots)
    assert any("Peak Traffic Day" in t for t in spike_annots)

    # B10: Version Adoption Velocity
    fig_uptake = render_version_uptake_chart(bundle.project_version)
    assert fig_uptake is not None
    # 2 traces: Dasik Library and VO: Better Dogs
    assert len(fig_uptake.data) == 2
    lib_trace = fig_uptake.data[0]
    dogs_trace = fig_uptake.data[1]
    assert "Dasik Library" in lib_trace.name
    assert "Better Dogs" in dogs_trace.name
    # Dasik Library Day 1 spike (> 250 DLs/version) vs Better Dogs steady curve
    assert lib_trace.y[1] > 250.0
    assert dogs_trace.y[1] < lib_trace.y[1]
    # Annotations for Headless 1-day spike and Organic 5-day curve
    assert len(fig_uptake.layout.annotations) >= 2
    uptake_annots = [a.text for a in fig_uptake.layout.annotations]
    assert any("Automated Headless Uptake" in t for t in uptake_annots)
    assert any("Organic Discovery Curve" in t for t in uptake_annots)

    # B11: Portfolio Pareto / Lorenz Concentration Curve
    fig_pareto = render_pareto_curve(bundle.project)
    assert fig_pareto is not None
    # 3 traces: 45-degree line of perfect equality, Lorenz curve, Top 2 marker
    assert len(fig_pareto.data) == 3
    eq_trace = fig_pareto.data[0]
    lorenz_trace = fig_pareto.data[1]
    top2_trace = fig_pareto.data[2]
    assert list(eq_trace.x) == [0, 100]
    assert list(eq_trace.y) == [0, 100]
    assert len(lorenz_trace.x) >= 20
    # Top 2 marker share should be ~72.0%
    assert abs(top2_trace.y[0] - 72.0) < 1.0
    # Annotation for Top 2 mods and HHI
    assert len(fig_pareto.layout.annotations) >= 1
    pareto_annots = [a.text for a in fig_pareto.layout.annotations]
    assert any("72.0%" in t for t in pareto_annots)
    assert any("2,731" in t for t in pareto_annots)

    # B12: Growth Waterfall
    fig_waterfall = render_growth_waterfall(bundle.project)
    assert fig_waterfall is not None
    assert len(fig_waterfall.data) == 1
    waterfall_trace = fig_waterfall.data[0]
    assert "total" in waterfall_trace.measure
    # Ending total equals total downloads (100,226)
    assert waterfall_trace.y[-1] == 100226


def test_new_advanced_charts_render_cleanly(bundle: ModrinthDataBundle):
    """Verify all 11 new econometric, pillar, disambiguation, and virality charts render cleanly."""
    proj_summary = calculate_project_summary(bundle.project)

    fig_rev_attr = render_project_revenue_attribution_chart(bundle.project)
    assert fig_rev_attr is not None
    assert len(fig_rev_attr.data) >= 5

    fig_l_evo = render_launcher_evolution_timeline(bundle.download_source)
    assert fig_l_evo is not None
    assert len(fig_l_evo.data) >= 4

    fig_mp_vir = render_modpack_virality_timeline(bundle.dependent_project)
    assert fig_mp_vir is not None
    assert len(fig_mp_vir.data) >= 3

    fig_bridge = render_version_disambiguation_bridge_chart(
        bundle.game_version, bundle.project_version
    )
    assert fig_bridge is not None
    assert len(fig_bridge.data) == 2

    fig_pv_mat = render_project_version_matrix_heatmap(bundle.project_version)
    assert fig_pv_mat is not None
    assert len(fig_pv_mat.data) == 1

    fig_pillar = render_pillar_architecture_chart(proj_summary)
    assert fig_pillar is not None
    assert len(fig_pillar.data) == 5  # 4 share bar series + 1 Blended RPM line

    fig_binge = render_bingeability_index_chart(proj_summary)
    assert fig_binge is not None
    assert len(fig_binge.data) == 1

    fig_naming = render_naming_linguistics_scatter(proj_summary)
    assert fig_naming is not None
    assert len(fig_naming.data) == 2  # Scatter + Log-OLS trendline

    fig_geo_quad = render_country_engagement_quadrant(bundle.country)
    assert fig_geo_quad is not None
    assert len(fig_geo_quad.data) == 3  # 3 distinct geographic telemetry regimes

    fig_corr = render_ecosystem_correlation_heatmap(bundle.project)
    assert fig_corr is not None
    assert len(fig_corr.data) == 1

    fig_cadence = render_release_cadence_regression_chart(
        bundle.project, bundle.project_version
    )
    assert fig_cadence is not None
    assert len(fig_cadence.data) == 4  # 2 subplots x (scatter + OLS line)


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
    fig15 = render_telemetry_coverage_chart(None)
    fig16 = render_revenue_vs_views_scatter(empty_df, empty_df)
    fig17 = render_rolling_rpm_trend(empty_df)
    fig18 = render_monetization_quadrant(empty_df)
    fig19 = render_dependency_flywheel_chart(empty_df)
    fig20 = render_intent_mix_timeline(empty_df)
    fig21 = render_engagement_index_chart(empty_df)
    fig22 = render_us_traffic_diagnostic(empty_df)
    fig23 = render_seasonality_heatmap(empty_df)
    fig24 = render_spike_attribution_chart(empty_df)
    fig25 = render_version_uptake_chart(empty_df)
    fig26 = render_pareto_curve(empty_df)
    fig27 = render_growth_waterfall(empty_df)
    fig28 = render_project_revenue_attribution_chart(empty_df)
    fig29 = render_launcher_evolution_timeline(empty_df)
    fig30 = render_modpack_virality_timeline(empty_df)
    fig31 = render_version_disambiguation_bridge_chart(empty_df, empty_df)
    fig32 = render_project_version_matrix_heatmap(empty_df)
    fig33 = render_pillar_architecture_chart(empty_df)
    fig34 = render_bingeability_index_chart(empty_df)
    fig35 = render_naming_linguistics_scatter(empty_df)
    fig36 = render_country_engagement_quadrant(empty_df)
    fig37 = render_ecosystem_correlation_heatmap(empty_df)
    fig38 = render_release_cadence_regression_chart(empty_df, empty_df)

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
        fig15,
        fig16,
        fig17,
        fig18,
        fig19,
        fig20,
        fig21,
        fig22,
        fig23,
        fig24,
        fig25,
        fig26,
        fig27,
        fig28,
        fig29,
        fig30,
        fig31,
        fig32,
        fig33,
        fig34,
        fig35,
        fig36,
        fig37,
        fig38,
    ]:
        assert fig is not None


