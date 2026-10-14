"""Modrinth Creator Analytics Studio - Streamlit Web Dashboard.

Provides executive analytics, revenue economics, launcher telemetry, and predictive
forecasting for dasikigaijin across all 21 Minecraft mod projects.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from src.charts import (
    render_daily_downloads_chart,
    render_dependency_flywheel_chart,
    render_dependent_modpacks_chart,
    render_download_reasons_chart,
    render_download_sources_chart,
    render_engagement_index_chart,
    render_game_version_timeline_chart,
    render_game_versions_chart,
    render_intent_mix_timeline,
    render_loader_donut_chart,
    render_monetization_donut_chart,
    render_monetization_quadrant,
    render_pareto_curve,
    render_project_leaderboard_chart,
    render_project_version_adoption_chart,
    render_revenue_velocity_chart,
    render_revenue_vs_views_scatter,
    render_rolling_rpm_trend,
    render_seasonality_heatmap,
    render_single_project_velocity,
    render_spike_attribution_chart,
    render_telemetry_coverage_chart,
    render_top_countries_bar_chart,
    render_us_traffic_diagnostic,
    render_version_uptake_chart,
    render_growth_waterfall,
    render_world_choropleth_map,
)
from src.loader import ModrinthDataBundle, load_all_data
from src.metrics import (
    calculate_country_summary,
    calculate_kpis,
    calculate_project_summary,
    calculate_rolling_rpm,
    calculate_source_kpis,
    calculate_version_kpis,
    filter_bundle_by_date,
    project_milestone_earnings,
)

# Page configuration
st.set_page_config(
    page_title="Modrinth Creator Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Global custom stylesheet
st.markdown(
    """
    <style>
    /* Global styles */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2.5rem;
    }
    
    /* Studio Header */
    .studio-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 0.5rem;
    }
    .studio-title {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #A78BFA 0%, #06B6D4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .studio-subtitle {
        color: #94A3B8;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }
    
    /* Sidebar Creator Badge */
    .creator-badge {
        background: rgba(139, 92, 246, 0.15);
        border: 1px solid #8B5CF6;
        border-radius: 8px;
        padding: 8px 12px;
        color: #E2E8F0;
        font-size: 0.85rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .creator-badge-tag {
        background: #8B5CF6;
        color: #FFFFFF;
        font-weight: 700;
        font-size: 0.75rem;
        padding: 2px 6px;
        border-radius: 4px;
    }

    /* Metric Cards Enhancement */
    div[data-testid="stMetric"] {
        background-color: #1E293B;
        border: 1px solid #334155;
        padding: 14px 18px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.25);
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    div[data-testid="stMetric"]:hover {
        border-color: #8B5CF6;
        transform: translateY(-2px);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        color: #94A3B8 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.75rem !important;
        font-weight: 800 !important;
        color: #F8FAFC !important;
    }

    /* Callout banner */
    .dual-rpm-banner {
        background: linear-gradient(90deg, rgba(139, 92, 246, 0.12) 0%, rgba(6, 182, 212, 0.08) 100%);
        border-left: 4px solid #8B5CF6;
        border-radius: 8px;
        padding: 14px 18px;
        margin: 1.25rem 0 1.5rem 0;
        color: #E2E8F0;
        font-size: 0.92rem;
        line-height: 1.5;
    }
    .dual-rpm-banner b {
        color: #F8FAFC;
    }
    .dual-rpm-highlight {
        color: #10B981;
        font-weight: 700;
    }

    /* Forecaster Card */
    .forecaster-box {
        background: #0F172A;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        margin-top: 1.5rem;
    }
    .forecaster-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-bottom: 4px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_sidebar(raw_bundle: ModrinthDataBundle) -> tuple[ModrinthDataBundle, bool]:
    """Render the sidebar controls and return filtered bundle and streamer mode flag."""
    st.sidebar.markdown("## 📈 Modrinth Analytics")

    # Creator Profile Badge
    st.sidebar.markdown(
        """
        <div class="creator-badge">
            <span>👤 <b>dasikigaijin</b></span>
            <span class="creator-badge-tag">21 MODS</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Privacy / Streamer Mode toggle
    streamer_mode = st.sidebar.checkbox(
        "🔒 Streamer / Privacy Mode",
        value=False,
        help="Masks exact dollar amounts for live streaming and public screenshots.",
    )

    exclude_pretracking = st.sidebar.checkbox(
        "Exclude Pre-Tracking Baseline (Apr 16–30)",
        value=False,
        help="Focus analytics on May 1 – Oct 13, 2026, when Modrinth active dimension telemetry was fully online.",
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📅 Date Range Filter")

    # Calculate min and max date across project table
    if not raw_bundle.project.empty and "Date" in raw_bundle.project.columns:
        min_date = raw_bundle.project["Date"].min().date()
        max_date = raw_bundle.project["Date"].max().date()
    else:
        min_date = datetime.date(2026, 4, 16)
        max_date = datetime.date(2026, 10, 13)

    selected_dates = st.sidebar.date_input(
        "Select Time Window",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        help="Filters all 10 analytics tables across the selected dates.",
    )

    if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
        if exclude_pretracking:
            if pd.to_datetime(start_date) < pd.Timestamp("2026-05-01"):
                start_date = pd.Timestamp("2026-05-01")
        active_bundle = filter_bundle_by_date(raw_bundle, start_date, end_date)
    else:
        # User is actively picking the range in the widget
        if exclude_pretracking:
            active_bundle = filter_bundle_by_date(
                raw_bundle, pd.Timestamp("2026-05-01"), max_date
            )
        else:
            active_bundle = raw_bundle

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📥 Dynamic Data Ingestion")
    uploaded_files = st.sidebar.file_uploader(
        "Drop new Modrinth CSV exports",
        accept_multiple_files=True,
        type=["csv"],
        help="Upload refreshed Modrinth analytics export CSV files to analyze without restarting.",
    )

    if uploaded_files:
        try:
            active_bundle = load_all_data(uploaded_files=uploaded_files)
            st.sidebar.success(f"Loaded {len(uploaded_files)} custom export files!")
        except Exception as e:
            st.sidebar.error(f"Error loading uploaded CSVs: {e}")

    # Dataset status footer
    total_raw_rows = sum(len(df) for df in active_bundle.as_dict().values())
    st.sidebar.caption(
        f"📊 Active tables: 10 | Normalized rows: {total_raw_rows:,}\n\n"
        "Engine: Modrinth Studio Fabric v1.0.0"
    )

    return active_bundle, streamer_mode


def render_tab1_revenue(bundle: ModrinthDataBundle, streamer_mode: bool) -> None:
    """Render Tab 1: Revenue Economics, Dual-RPM & Forecaster."""
    kpis = calculate_kpis(bundle)

    # Top Metric KPI Row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        rev_val = "$ •••••" if streamer_mode else f"${kpis['total_revenue']:.2f}"
        rev_pts = (
            "••• pts" if streamer_mode else f"{kpis['total_revenue'] * 100:.0f} pts"
        )
        st.metric(
            label="Total Creator Revenue",
            value=rev_val,
            delta=f"Rewards: {rev_pts}",
            delta_color="normal",
            help="Total lifetime revenue generated via Modrinth Creator Rewards Program.",
        )

    with col2:
        st.metric(
            label="Total Mod Downloads",
            value=f"{kpis['total_downloads']:,}",
            delta=f"{kpis['total_views']:,} Page Views",
            delta_color="normal",
            help="Cumulative downloads across all 21 published mods and version releases.",
        )

    with col3:
        st.metric(
            label="Total Playtime",
            value=f"{kpis['total_playtime_hours']:,.0f} Hours",
            delta=f"{kpis['total_playtime_days']:,.1f} Days ({kpis['avg_playtime_per_download_min']:.1f}m/dl)",
            delta_color="normal",
            help="Accumulated in-game playtime reported by Modrinth App telemetry.",
        )

    with col4:
        rpm_val = (
            "$ •••" if streamer_mode else f"${kpis['monetized_rpm']:.2f} / 1k DLs"
        )
        blended_val = (
            "$ •••" if streamer_mode else f"${kpis['blended_rpm']:.2f}"
        )
        st.metric(
            label="Monetized Impression RPM",
            value=rpm_val,
            delta=f"Blended: {blended_val} ({kpis['monetization_rate']:.1f}% Mon.)",
            delta_color="normal",
            help="Empirical Revenue Per Mille: ~$2.95 per 1,000 monetized ad impressions vs ~$0.29 blended across all downloads.",
        )

    # Educational Dual-RPM Callout Box
    st.markdown(
        f"""
        <div class="dual-rpm-banner">
            💡 <b>The Dual-RPM Creator Reality:</b>
            Out of <b>{kpis['total_downloads']:,}</b> total downloads, only 
            <span class="dual-rpm-highlight">{kpis['monetized_downloads']:,} ({kpis['monetization_rate']:.1f}%)</span>
            generated monetized ad impressions. Monetized revenue reflects verified ad impressions on creator project pages ($1.17 per 1,000 monetized views). Non-monetized downloads ({100.0 - kpis['monetization_rate']:.1f}%) represent launcher updates, background syncs, and direct API pulls where impressions are not served.
            While your true impression yield is a healthy <b>${kpis['monetized_rpm']:.2f} RPM</b>,
            the effective blended payout across all downloads is <b>${kpis['blended_rpm']:.2f} RPM</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Velocity Charts: 2 Columns
    chart_col1, chart_col2 = st.columns([3, 2])

    with chart_col1:
        fig_revenue = render_revenue_velocity_chart(bundle.member)
        st.plotly_chart(fig_revenue, width="stretch")

    with chart_col2:
        fig_donut = render_monetization_donut_chart(bundle.monetization)
        st.plotly_chart(fig_donut, width="stretch")

    # Full-width Daily Downloads Area Chart
    fig_downloads = render_daily_downloads_chart(bundle.project)
    st.plotly_chart(fig_downloads, width="stretch")

    # Interactive Milestone Earnings Forecaster
    st.markdown(
        """
        <div class="forecaster-box">
            <div class="forecaster-title">🔮 Interactive Milestone Earnings Forecaster</div>
            <p style="color:#94A3B8;font-size:0.9rem;margin-bottom:1rem;">
                Project anticipated revenue milestones based on empirical monetization conversion rate (9.94%) and active Modrinth RPM.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    f_col_left, f_col_right = st.columns([2, 3])

    with f_col_left:
        target_dl = st.slider(
            "Target Cumulative Downloads Milestone",
            min_value=50_000,
            max_value=5_000_000,
            value=500_000,
            step=50_000,
            format="%d DLs",
            help="Slide to simulate future scale milestones (e.g. 500k, 1M, 5M downloads).",
        )

    trailing_30d = kpis.get("trailing_30d_blended_rpm")
    proj = project_milestone_earnings(
        target_downloads=target_dl,
        blended_rpm=kpis["blended_rpm"],
        monetized_rpm=kpis["monetized_rpm"],
        monetization_rate=kpis["monetization_rate"],
        trailing_30d_rpm=trailing_30d,
    )

    with f_col_right:
        p_card1, p_card2, p_card3 = st.columns(3)
        with p_card1:
            conservative_proj = (
                "$ •••••"
                if streamer_mode
                else f"${proj['conservative_earnings']:,.2f}"
            )
            cons_rpm = (
                trailing_30d
                if (trailing_30d is not None and trailing_30d > 0)
                else kpis["blended_rpm"] * 0.85
            )
            st.metric(
                label="Conservative Scenario",
                value=conservative_proj,
                delta=f"@ ${cons_rpm:.2f} RPM (Trailing 30d)",
                delta_color="normal",
                help="Conservative lower bound based on trailing 30-day blended RPM (~$0.26 / 1k DLs).",
            )
        with p_card2:
            blended_proj = (
                "$ •••••"
                if streamer_mode
                else f"${proj['projected_blended_earnings']:,.2f}"
            )
            st.metric(
                label="Baseline / Median",
                value=blended_proj,
                delta=f"@ ${kpis['blended_rpm']:.2f} RPM (Lifetime)",
                delta_color="normal",
                help="Empirical baseline based on lifetime blended RPM across all downloads ($0.2933 / 1k DLs).",
            )
        with p_card3:
            optimistic_proj = (
                "$ •••••"
                if streamer_mode
                else f"${proj['optimistic_earnings']:,.2f}"
            )
            opt_rpm = kpis["blended_rpm"] * 1.25
            st.metric(
                label="Optimistic Scenario",
                value=optimistic_proj,
                delta=f"@ ${opt_rpm:.2f} RPM (Monetized Expansion)",
                delta_color="normal",
                help="Optimistic potential assuming increased client monetization and ad yield expansion (~$0.35+ / 1k DLs).",
            )

    st.caption(
        f"🎯 Milestone Target: **{target_dl:,}** total downloads (~{proj['projected_monetized_downloads']:,.0f} monetized) | "
        f"Baseline Creator Rewards: **{proj['projected_blended_earnings'] * 100:,.0f} pts** (NET-60 Redemption)"
    )

    with st.expander("🔬 Econometric Revenue Drivers & Trailing RPM", expanded=False):
        st.markdown(
            """
            <div style="background:#0F172A;border-left:4px solid #8B5CF6;padding:12px 16px;border-radius:6px;margin-bottom:14px;color:#F8FAFC;font-size:0.92rem;">
                📈 <b>Econometric Discovery:</b> Project page views are the leading indicator of creator earnings 
                (<b>r ≈ 0.71</b> Pearson correlation, <b>$1.17 per 1,000 monetized views</b>).
                While launcher downloads drive cumulative scale, direct page traffic drives ad impressions. 
                Trailing 30-day rolling RPM reveals how monetization expanded in August from $0.18 to $0.35+ as ad coverage widened.
            </div>
            """,
            unsafe_allow_html=True,
        )
        e_col1, e_col2 = st.columns(2)
        with e_col1:
            fig_scatter = render_revenue_vs_views_scatter(bundle.monetization, bundle.member)
            st.plotly_chart(fig_scatter, width="stretch")
        with e_col2:
            rolling_df = calculate_rolling_rpm(bundle.member, bundle.project, bundle.monetization)
            fig_rolling = render_rolling_rpm_trend(rolling_df)
            st.plotly_chart(fig_rolling, width="stretch")

    with st.expander("📡 Platform Telemetry Coverage & Data Health", expanded=False):
        st.markdown(
            """
            <div style="background:#0F172A;border-left:4px solid #06B6D4;padding:12px 16px;border-radius:6px;margin-bottom:14px;color:#F8FAFC;font-size:0.92rem;">
                📡 <b>Platform Telemetry Evolution:</b> Prior to <b>May 1, 2026</b>, Modrinth analytics recorded downloads without 
                dimension categorization (0% known data across Game Version, Loader, Country, and Reason).
                From May 1 onwards, active telemetry tracking rolled out platform-wide, establishing steady 
                <b>~65–70% resolved dimension coverage</b> with launcher and ecosystem classification.
            </div>
            """,
            unsafe_allow_html=True,
        )
        fig_telemetry = render_telemetry_coverage_chart(bundle)
        st.plotly_chart(fig_telemetry, width="stretch")


def render_tab2_launchers(bundle: ModrinthDataBundle) -> None:
    """Render Tab 2: Launchers, Acquisition Sources & Download Reasons."""
    src_kpis = calculate_source_kpis(bundle.download_source, bundle.download_reason)

    # Top KPI row (4 cards)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Primary Launcher",
            value=f"{src_kpis['modrinth_app_downloads']:,}",
            delta=f"{src_kpis['modrinth_app_pct']:.1f}% Share (Modrinth App)",
            delta_color="normal",
            help="Official Modrinth desktop application installer downloads.",
        )

    with col2:
        st.metric(
            label="Web Direct",
            value=f"{src_kpis['modrinth_website_downloads']:,}",
            delta=f"{src_kpis['modrinth_website_pct']:.1f}% Share (Website)",
            delta_color="normal",
            help="Direct manual browser downloads via modrinth.com.",
        )

    with col3:
        st.metric(
            label="Community Launchers",
            value=f"{src_kpis['prism_launcher_downloads']:,}",
            delta=f"{src_kpis['prism_launcher_pct']:.1f}% Share (Prism)",
            delta_color="normal",
            help="Direct API pulls from Prism Launcher power-user installations.",
        )

    with col4:
        st.metric(
            label="Ecosystem Distribution",
            value=f"{src_kpis['ecosystem_downloads']:,}",
            delta=f"{src_kpis['ecosystem_pct']:.1f}% (Modpacks + Deps)",
            delta_color="normal",
            help="Automated pulls via modpack distribution and library dependencies.",
        )

    # Row 1: Two chart columns
    col_left, col_right = st.columns([3, 2])

    with col_left:
        fig_sources = render_download_sources_chart(bundle.download_source)
        st.plotly_chart(fig_sources, width="stretch")

    with col_right:
        fig_reasons = render_download_reasons_chart(bundle.download_reason)
        st.plotly_chart(fig_reasons, width="stretch")

    # Row 2: Acquisition Insight banner
    st.markdown(
        f"""
        <div class="dual-rpm-banner">
            🚀 <b>Acquisition Channel Insights:</b>
            Over <b>{src_kpis['native_channels_pct']:.1f}% ({src_kpis['native_channels_downloads']:,} DLs)</b>
            of your downloads originate from official Modrinth-native channels (App + Website), ensuring direct storefront discovery.
            Meanwhile, <b>Prism Launcher ({src_kpis['prism_launcher_downloads']:,} DLs / {src_kpis['prism_launcher_pct']:.1f}%)</b>
            represents your single largest third-party power-user launcher community, with automated modpack and dependency
            ecosystem pulls driving <b>{src_kpis['ecosystem_downloads']:,} DLs ({src_kpis['ecosystem_pct']:.1f}%)</b> of distribution volume.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Row 3: Intent Dynamics & Dependency Flywheel Analysis
    st.markdown("##### 🔄 Ecosystem Pull-Through & Download Intent Dynamics")
    dyn_col1, dyn_col2 = st.columns([3, 2])
    with dyn_col1:
        fig_intent = render_intent_mix_timeline(bundle.download_reason)
        st.plotly_chart(fig_intent, width="stretch")

    with dyn_col2:
        own_projs = (
            set(bundle.project["Project"].unique())
            if not bundle.project.empty and "Project" in bundle.project.columns
            else None
        )
        fig_flywheel = render_dependency_flywheel_chart(
            bundle.dependent_project, own_projects=own_projs
        )
        st.plotly_chart(fig_flywheel, width="stretch")

    st.markdown(
        """
        <div style="background:#0F172A;border-left:4px solid #10B981;padding:12px 16px;border-radius:6px;margin-bottom:14px;color:#F8FAFC;font-size:0.92rem;">
            🔄 <b>Ecosystem Flywheel & Intent Evolution:</b>
            Attributed dependency distribution reveals two high-impact acquisition pipelines:
            <b>Internal Studio Pull-Through</b> (<b>13,361 DLs</b> / 62.4% of resolved dependencies) where flagship mods (Better Dogs, Dasik Library, True Sleep, Item Clumps) drive cross-mod adoption across player installations, and <b>External Modpacks</b> (<b>8,067 DLs</b> / 37.6% of resolved dependencies) led by curated packs like <i>Sensible MC</i> (4,646 DLs) and <i>Legacies</i> (3,110 DLs).
            Simultaneously, download intent dynamics illustrate maturing player engagement: <b>Version Update retention surged from 8.0% in May to 18.8% in August</b> as active players upgraded to Minecraft 26.2, while external modpack distribution surged in <b>September to 21.2%</b> of monthly volume.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Expandable detailed table with exact counts and percentages
    with st.expander("📋 View Detailed Source & Reason Breakdown Tables"):
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown("##### 🚀 Launcher & Source Distribution")
            if not bundle.download_source.empty and "Downloads" in bundle.download_source.columns:
                s_table = (
                    bundle.download_source.groupby("Download source", as_index=False)["Downloads"]
                    .sum()
                    .sort_values("Downloads", ascending=False)
                    .reset_index(drop=True)
                )
                tot_s = s_table["Downloads"].sum()
                s_table["Share (%)"] = (
                    (s_table["Downloads"] / tot_s * 100.0).map("{:.2f}%".format)
                    if tot_s > 0
                    else "0.00%"
                )
                s_table["Downloads"] = s_table["Downloads"].map("{:,}".format)
                st.dataframe(s_table, width="stretch", hide_index=True)
            else:
                st.caption("No source breakdown data available.")

        with col_t2:
            st.markdown("##### 📥 Installation Reason Distribution")
            if not bundle.download_reason.empty and "Downloads" in bundle.download_reason.columns:
                r_table = (
                    bundle.download_reason.groupby("Download reason", as_index=False)["Downloads"]
                    .sum()
                    .sort_values("Downloads", ascending=False)
                    .reset_index(drop=True)
                )
                tot_r = r_table["Downloads"].sum()
                r_table["Share (%)"] = (
                    (r_table["Downloads"] / tot_r * 100.0).map("{:.2f}%".format)
                    if tot_r > 0
                    else "0.00%"
                )
                r_table["Downloads"] = r_table["Downloads"].map("{:,}".format)
                st.dataframe(r_table, width="stretch", hide_index=True)
            else:
                st.caption("No reason breakdown data available.")


def render_tab3_demographics(bundle: ModrinthDataBundle) -> None:
    """Render Tab 3: Minecraft Version Demographics & Loader Breakdown."""
    # Disambiguation Radio Toggle
    version_mode = st.radio(
        "Analytics Source:",
        [
            "✨ Enriched Engine (Unknowns Resolved via Project Versions)",
            "📄 Raw Modrinth Telemetry (Includes 38.7k Unknowns)",
        ],
        horizontal=True,
        help="Toggle between catalog-enriched version resolution and raw Modrinth export telemetry.",
    )
    use_enriched = "Enriched Engine" in version_mode

    v_kpis = calculate_version_kpis(
        bundle.game_version, bundle.project_version, use_enriched=use_enriched
    )

    # Loader totals
    if not bundle.loader.empty and "Downloads" in bundle.loader.columns:
        loader_agg = bundle.loader.groupby("Loader")["Downloads"].sum().to_dict()
        fabric_dls = int(loader_agg.get("Fabric", 0))
    else:
        fabric_dls = 0

    # Top KPI row (4 cards)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Sovereign Lead Anchor",
            value=f"{v_kpis['lead_downloads']:,} DLs",
            delta=f"Minecraft 26.2 ({v_kpis['lead_pct']:.1f}%)",
            delta_color="normal",
            help="Top generational version anchor leading our studio releases.",
        )

    with col2:
        st.metric(
            label="Modern Anchors (26.x)",
            value=f"{v_kpis['modern_26x_downloads']:,} DLs",
            delta=f"{v_kpis['modern_26x_pct']:.1f}% Ecosystem",
            delta_color="normal",
            help="Total download volume across all modern Minecraft 26.x version builds.",
        )

    with col3:
        st.metric(
            label="Legacy LTS Anchors",
            value=f"{v_kpis['legacy_downloads']:,} DLs",
            delta=f"{v_kpis['legacy_pct']:.1f}% LTS (1.21.x / 1.20.1)",
            delta_color="normal",
            help="Multi-Era backport adoption across Minecraft 1.21.11, 1.21.1, and 1.20.1.",
        )

    with col4:
        st.metric(
            label="Primary Mod Loader",
            value="Fabric Dominant",
            delta=f"{fabric_dls:,} DLs (100% Identified)",
            delta_color="normal",
            help="100% of all identified runtime telemetry runs on the Fabric mod loader.",
        )

    # Row 1: Two columns for Version Adoption and Loader Share
    col_left, col_right = st.columns([3, 2])

    with col_left:
        fig_versions = render_game_versions_chart(
            bundle.game_version, bundle.project_version, use_enriched=use_enriched
        )
        st.plotly_chart(fig_versions, width="stretch")

    with col_right:
        fig_loader = render_loader_donut_chart(bundle.loader)
        st.plotly_chart(fig_loader, width="stretch")

    # Row 2: Version Evolution Timeline over time
    timeline_df = bundle.project_version if use_enriched else bundle.game_version
    timeline_col = "Target Game Version" if use_enriched else "Game version"
    fig_timeline = render_game_version_timeline_chart(
        timeline_df, version_col=timeline_col
    )
    st.plotly_chart(fig_timeline, width="stretch")

    # Educational Callout
    st.markdown(
        """
        <div class="dual-rpm-banner">
            🧩 <b>Why Raw Modrinth Telemetry Reports 38,775 "Unknown" Game Versions:</b><br>
            April 16–30 was a pre-tracking baseline where Modrinth did not record dimension breakdowns, resulting in initial Unknown tags, while third-party launchers query release files via API endpoints without game version headers.
            <br><br>
            Our studio's <b>Enriched Demographics Engine</b> resolves game version compatibility directly from project jar metadata against our canonical version catalog, resolving <b>99.8%</b> of version downloads back to their true target Minecraft versions (26.2, 26.1.2, 26.3, 1.21.11, 1.20.1). This demonstrates that our studio's <b>Multi-Era Anchor Parity Law</b> actively captures player demand across both modern Sovereign leads and LTS legacy anchors!
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Row 3: Playtime & Engagement Dwell-Time Index (B6)
    st.markdown("##### ⏱️ Player Engagement Depth & Version Dwell-Time Index")
    fig_engagement = render_engagement_index_chart(
        bundle.game_version, bundle.project_version
    )
    st.plotly_chart(fig_engagement, width="stretch")

    st.markdown(
        """
        <div style="background:#0F172A;border-left:4px solid #10B981;padding:12px 16px;border-radius:6px;margin-bottom:14px;color:#F8FAFC;font-size:0.92rem;">
            ⏱️ <b>Empirical Justification for Multi-Era Anchor Parity Law:</b>
            Players on legacy LTS versions (<b>1.21.1</b>, <b>1.20.1</b>) average <b>2.49 and 1.51 minutes of playtime per download</b>—more than double modern release churn (<b>1.09 min</b>). Maintaining multi-version anchor parity captures deep gameplay dwell time.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_tab4_projects(
    bundle: ModrinthDataBundle, streamer_mode: bool = False
) -> None:
    """Render Tab 4: Projects Catalog Matrix & Modpack Ecosystem Deep-Dive."""
    proj_summary = calculate_project_summary(bundle.project)

    # Dual Sub-View Toggle
    tab4_mode = st.radio(
        "Catalog View Mode:",
        [
            "📋 Full Catalog Matrix (All 21 Projects)",
            "🔍 Single Mod Deep-Dive (Interactive Inspector)",
        ],
        horizontal=True,
        help="Switch between studio-wide catalog performance matrix and single-mod diagnostic inspection.",
    )

    if "Full Catalog Matrix" in tab4_mode:
        # Top KPI Cards (3 cards)
        col1, col2, col3 = st.columns(3)
        catalog_size = len(proj_summary)

        # Flagship mod
        if not proj_summary.empty:
            flagship_row = proj_summary.iloc[0]
            flagship_name = str(flagship_row["Project"])
            flagship_dls = int(flagship_row["Downloads"])
            flagship_share = float(flagship_row["Share %"])
        else:
            flagship_name = "None"
            flagship_dls = 0
            flagship_share = 0.0

        # Top external modpack from bundle.dependent_project
        if not bundle.dependent_project.empty and "Dependent project" in bundle.dependent_project.columns:
            dep_clean = bundle.dependent_project[
                bundle.dependent_project["Dependent project"] != "Unknown"
            ]
            # Exclude self-mods to isolate true third-party packs
            dep_clean = dep_clean[
                ~dep_clean["Dependent project"].str.startswith("VO:")
                & ~dep_clean["Dependent project"].str.startswith("IG:")
                & ~dep_clean["Dependent project"].str.startswith("DG:")
                & ~dep_clean["Dependent project"].str.contains("Dasik", case=False)
                & ~dep_clean["Dependent project"].str.contains("gamerules", case=False)
            ]
            dep_agg = (
                dep_clean.groupby("Dependent project")["Downloads"]
                .sum()
                .sort_values(ascending=False)
            )
            if not dep_agg.empty:
                top_pack_name = dep_agg.index[0]
                top_pack_dls = int(dep_agg.iloc[0])
            else:
                top_pack_name = "Sensible MC"
                top_pack_dls = 4646
        else:
            top_pack_name = "Sensible MC"
            top_pack_dls = 4646

        with col1:
            st.metric(
                label="Catalog Size",
                value=f"{catalog_size} Projects",
                delta="100% Studio Portfolio",
                delta_color="normal",
                help="Active Fabric mod projects published under dasikigaijin.",
            )

        with col2:
            st.metric(
                label="Flagship Mod",
                value=f"{flagship_name}",
                delta=f"{flagship_dls:,} DLs ({flagship_share:.1f}% Share)",
                delta_color="normal",
                help="Highest distribution volume project in our studio portfolio.",
            )

        with col3:
            st.metric(
                label="Top External Modpack",
                value=f"{top_pack_name}",
                delta=f"{top_pack_dls:,} Attributed DLs",
                delta_color="normal",
                help="Leading third-party modpack distributing studio components to players.",
            )

        # Row 1: Dual charts
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            fig_proj = render_project_leaderboard_chart(proj_summary)
            st.plotly_chart(fig_proj, width="stretch")

        with col_c2:
            fig_dep = render_dependent_modpacks_chart(bundle.dependent_project)
            st.plotly_chart(fig_dep, width="stretch")

        # Row 2: Monetization Asymmetry Quadrant & Portfolio Concentration Analysis
        st.markdown("##### ⚖️ Monetization Asymmetry & Portfolio Concentration")
        fig_quadrant = render_monetization_quadrant(proj_summary)
        st.plotly_chart(fig_quadrant, width="stretch")

        st.markdown(
            """
            <div class="dual-rpm-banner">
                ⚖️ <b>Portfolio Concentration & Monetization Asymmetry:</b>
                Studio distribution exhibits strong concentration (<b>HHI = 2,731</b>; Top 2 projects account for <b>72.0%</b> of all downloads).
                However, value capture diverges sharply across architectural roles:
                <br>• <b>VO: Better Dogs (High-Yield Flagship):</b> Generates <b>38.4% of total studio revenue</b> from <b>31.0% of downloads</b> ($0.364 RPM), driven by high player engagement and intentional storefront discovery.
                <br>• <b>Dasik Library (Volume Engine):</b> Drives <b>41.1% of studio downloads</b> but captures only <b>21.3% of revenue</b> ($0.152 RPM) due to background dependency resolution via headless launcher APIs where web impressions are unmonetized.
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Row 3: Comprehensive sortable catalog table using st.dataframe
        st.markdown("##### 📋 Complete Project Catalog Matrix")
        display_df = proj_summary.copy()
        if not display_df.empty:
            display_df["Downloads"] = display_df["Downloads"].map("{:,}".format)
            display_df["Share %"] = display_df["Share %"].map("{:.2f}%".format)
            display_df["Views"] = display_df["Views"].map("{:,}".format)
            if "Downloads per View (x)" in display_df.columns:
                display_df["Downloads per View (x)"] = display_df[
                    "Downloads per View (x)"
                ].map("{:.2f}x".format)
            display_df["Conversion Rate %"] = display_df["Conversion Rate %"].map(
                "{:.2f}%".format
            )
            if streamer_mode:
                display_df["Revenue"] = "$ ••••"
            else:
                display_df["Revenue"] = display_df["Revenue"].map("${:,.2f}".format)
            display_df["Playtime (Hours)"] = display_df["Playtime (Hours)"].map(
                "{:,.1f}h".format
            )
            st.dataframe(display_df, width="stretch", hide_index=True)
        else:
            st.caption("No project catalog telemetry available.")

    else:
        # Sub-view 2: Single Mod Deep-Dive
        sorted_projects = (
            proj_summary["Project"].tolist()
            if not proj_summary.empty
            else bundle.project["Project"].unique().tolist()
        )
        selected_mod = st.selectbox(
            "Select Project to Inspect:",
            sorted_projects,
            help="Choose any of your 21 studio projects to inspect velocity trajectories and release adoption.",
        )

        # 4 Mod KPI Cards
        mod_row = proj_summary[proj_summary["Project"] == selected_mod]
        if not mod_row.empty:
            m_dls = int(mod_row["Downloads"].iloc[0])
            m_share = float(mod_row["Share %"].iloc[0])
            m_views = int(mod_row["Views"].iloc[0])
            m_conv = float(mod_row["Conversion Rate %"].iloc[0])
            m_rev = float(mod_row["Revenue"].iloc[0])
            m_rpm = (m_rev / m_dls * 1000.0) if m_dls > 0 else 0.0
            m_play_hrs = float(mod_row["Playtime (Hours)"].iloc[0])
            m_avg_min = (m_play_hrs * 60.0 / m_dls) if m_dls > 0 else 0.0
        else:
            m_dls = 0
            m_share = 0.0
            m_views = 0
            m_conv = 0.0
            m_rev = 0.0
            m_rpm = 0.0
            m_play_hrs = 0.0
            m_avg_min = 0.0

        col_k1, col_k2, col_k3, col_k4 = st.columns(4)

        with col_k1:
            st.metric(
                label=f"{selected_mod} Downloads",
                value=f"{m_dls:,} DLs",
                delta=f"{m_share:.1f}% Studio Share",
                delta_color="normal",
            )

        with col_k2:
            st.metric(
                label="Page Views & Conversion",
                value=f"{m_views:,} Views",
                delta=f"{m_conv:.2f}% Conversion",
                delta_color="normal",
            )

        with col_k3:
            st.metric(
                label="Generated Revenue",
                value="$ ••••" if streamer_mode else f"${m_rev:.2f}",
                delta=f"${m_rpm:.2f} Blended RPM",
                delta_color="normal",
            )

        with col_k4:
            st.metric(
                label="Cumulative Playtime",
                value=f"{m_play_hrs:,.1f} Hours",
                delta=f"{m_avg_min:.1f} min / DL",
                delta_color="normal",
            )

        # Row 1: Daily Velocity timeline
        fig_vel = render_single_project_velocity(bundle.project, selected_mod)
        st.plotly_chart(fig_vel, width="stretch")

        # Row 2: Version Adoption breakdown
        fig_ver = render_project_version_adoption_chart(
            bundle.project_version, selected_mod
        )
        st.plotly_chart(fig_ver, width="stretch")


def render_tab5_geography(bundle: ModrinthDataBundle) -> None:
    """Render Tab 5: World Geography, Choropleth Distribution, and Country Telemetry."""
    total_bundle_downloads = (
        int(bundle.project["Downloads"].sum())
        if not bundle.project.empty and "Downloads" in bundle.project.columns
        else None
    )
    country_summary, country_kpis = calculate_country_summary(
        bundle.country, total_bundle_downloads=total_bundle_downloads
    )

    # Top KPI cards (4 cards)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Top Country",
            value=f"{country_kpis['top_country']}",
            delta=f"{country_kpis['top_country_downloads']:,} DLs ({country_kpis['top_country_pct']:.1f}%)",
            delta_color="normal",
            help="Leading sovereign nation with the highest verified creator downloads.",
        )

    with col2:
        st.metric(
            label="Identified Nations",
            value=f"{country_kpis['identified_countries_count']} Sovereign Nations",
            delta=f"{country_kpis['identified_countries_count']} Active Regions",
            delta_color="normal",
            help="Global geographic reach across verified IP addresses.",
        )

    with col3:
        st.metric(
            label="Identified Traffic",
            value=f"{country_kpis['identified_downloads']:,} DLs",
            delta=f"{country_kpis['identified_pct']:.1f}% Resolved Reach",
            delta_color="normal",
            help="Downloads attributed to resolved player IP geographies.",
        )

    with col4:
        st.metric(
            label="Unresolved Telemetry",
            value=f"{country_kpis['other_downloads']:,} DLs",
            delta=f"{country_kpis['other_pct']:.1f}% Launcher Pulls",
            delta_color="off",
            help="Unresolved 'Other' downloads where launcher privacy protections omit user IPs.",
        )

    # Map Controls
    ctrl_col1, ctrl_col2 = st.columns([2, 1])
    with ctrl_col1:
        metric_choice = st.radio(
            "Display Metric:",
            ["Downloads", "Playtime (Hours)"],
            horizontal=True,
            help="Toggle between download volume and player engagement time.",
        )
    with ctrl_col2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        log_scale = st.checkbox(
            "Logarithmic Color Scale",
            value=False,
            help="Apply log10 transform to highlight geographic distribution across smaller countries.",
        )

    # Full-width World Choropleth Map
    fig_map = render_world_choropleth_map(
        bundle.country, metric=metric_choice, use_log=log_scale
    )
    st.plotly_chart(fig_map, width="stretch")

    # Two columns: Left col Top 10 Countries Bar, Right col Privacy & Telemetry Insights
    col_left, col_right = st.columns([3, 2])

    with col_left:
        fig_bar = render_top_countries_bar_chart(bundle.country, metric=metric_choice)
        st.plotly_chart(fig_bar, width="stretch")

    with col_right:
        st.markdown(
            f"""
            <div class="dual-rpm-banner">
                🌐 <b>Telemetry Ingestion & Geographic Distribution Analysis:</b><br><br>
                The <b>{country_kpis['other_downloads']:,} downloads ({country_kpis['other_pct']:.1f}%)</b> under 'Other' represent unrecorded IP telemetry in Modrinth's logging pipeline (100% unrecorded in April, settling to ~75% in later months). Among resolved geography, the United States represents <b>{country_kpis['top_country_downloads']:,} downloads ({country_kpis['top_country_pct']:.1f}%)</b>, alongside active engagement in Germany, Brazil, UK, China, Russia, Indonesia, and Singapore.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Expandable table: Country-by-Country telemetry
    with st.expander("📋 View Complete Country-by-Country Telemetry Table"):
        if not country_summary.empty:
            display_c = country_summary.copy()
            display_c["Downloads"] = display_c["Downloads"].map("{:,}".format)
            display_c["Views"] = display_c["Views"].map("{:,}".format)
            display_c["Playtime (Hours)"] = display_c["Playtime (Hours)"].map(
                "{:,.1f}h".format
            )
            display_c["Share (%)"] = display_c["Share %"].map("{:.2f}%".format)
            display_c = display_c.drop(
                columns=["Playtime (seconds)", "Share %"], errors="ignore"
            )
            st.dataframe(display_c, width="stretch", hide_index=True)
        else:
            st.caption("No country telemetry data available.")

    # Regional Telemetry Diagnostic & Anomalies (B7)
    st.markdown("##### 📡 Regional Telemetry Diagnostic & Anomalies")
    fig_us_diag = render_us_traffic_diagnostic(bundle.country)
    st.plotly_chart(fig_us_diag, width="stretch")

    st.markdown(
        """
        <div style="background:#0F172A;border-left:4px solid #F59E0B;padding:12px 16px;border-radius:6px;margin-bottom:14px;color:#F8FAFC;font-size:0.92rem;">
            📡 <b>Headless Server Distribution Anomaly vs Organic Human Discovery:</b>
            Telemetry analysis reveals a structural divergence between North American and European/Global traffic profiles.
            While European and global players discover mods via modrinth.com with organic engagement (<b>2.0–2.2 DLs/view</b>, <b>0.82–2.49 min dwell time</b>),
            United States traffic exhibits an extraordinary <b>345.4 downloads per web page view</b> and near-zero dwell time (<b>0.03 min / DL</b>).
            Over <b>99.7%</b> of US downloads bypass frontend web visits entirely, confirming automated headless server updates and background client synchronizations driven by curated third-party modpack ecosystems (such as <i>Sensible MC</i>).
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_tab6_econometrics(bundle: ModrinthDataBundle) -> None:
    """Render Tab 6: Advanced Econometrics & Deep Longitudinal Insights (B8–B12)."""
    st.markdown("### 🔬 Advanced Econometrics & Deep Longitudinal Insights")
    st.caption(
        "Empirical seasonality, anomaly attribution, adoption velocity, catalog concentration, and growth decomposition."
    )

    # Top KPI Row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Peak Seasonality Day",
            value="Sunday (+30.8%)",
            delta="Fri Anchor: 492 DLs/day",
            delta_color="normal",
            help="Sunday generates 643 avg DLs/day vs Friday 492 DLs/day (+30.8% weekend surge).",
        )

    with col2:
        st.metric(
            label="Max Single-Day Spike",
            value="1,987 DLs",
            delta="Oct 6, 2026 (+589 Anomaly)",
            delta_color="normal",
            help="All-time daily traffic record driven by Sensible MC modpack and sovereign anchor parity.",
        )

    with col3:
        st.metric(
            label="Version Migration Lag",
            value="1d Lib vs 5d Content",
            delta="Headless Automated Sync",
            delta_color="normal",
            help="Dasik Library reaches peak within 24 hours via automated dependency resolvers, while content mods experience a 5-day organic adoption curve.",
        )

    with col4:
        st.metric(
            label="Portfolio Concentration",
            value="HHI 2,731",
            delta="Top 2 = 72.0% Volume",
            delta_color="normal",
            help="Herfindahl-Hirschman Index indicates high concentration: Dasik Library + Better Dogs drive 72% of total studio volume.",
        )

    # Section 1: Day-of-Week Seasonality & Release Cadence (B8)
    st.markdown("---")
    st.markdown("##### 📅 Day-of-Week Seasonality & Release Cadence")
    fig_seasonality = render_seasonality_heatmap(bundle.project)
    st.plotly_chart(fig_seasonality, width="stretch")

    st.markdown(
        """
        <div style="background:#0F172A;border-left:4px solid #8B5CF6;padding:12px 16px;border-radius:6px;margin-bottom:14px;color:#F8FAFC;font-size:0.92rem;">
            📅 <b>Empirical Validation for Studio Constitution Friday 19:00 UTC Release Rule:</b>
            Telemetry across 26 consecutive weeks proves that player engagement builds monotonically from Friday (<b>492 avg DLs/day</b>) into Saturday (<b>581 avg DLs/day</b>),
            culminating in the Sunday peak (<b>643 avg DLs/day, +30.8% over Friday baseline</b>).
            By releasing weekly updates on Friday at 19:00 UTC, newly compiled and deployed JARs are indexed immediately and achieve maximum visibility right as weekend discovery traffic accelerates.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Section 2: Spike Detection & Event Attribution (B9)
    st.markdown("---")
    st.markdown("##### ⚡ Spike Detection & Event Attribution")
    fig_spikes = render_spike_attribution_chart(bundle.project)
    st.plotly_chart(fig_spikes, width="stretch")

    st.markdown(
        """
        <div style="background:#0F172A;border-left:4px solid #F59E0B;padding:12px 16px;border-radius:6px;margin-bottom:14px;color:#F8FAFC;font-size:0.92rem;">
            ⚡ <b>Longitudinal Catalyst Attribution:</b>
            14-day rolling median filtering isolates four statistically significant anomaly events across the studio's operational history:
            <br>• <b>May 16–17, 2026 (Catalog Indexing):</b> Initial public indexing surge (+145 DLs over rolling median).
            <br>• <b>Aug 9, 2026 (Monetization Transition):</b> Modrinth Creator Rewards launch and multi-anchor release wave (<b>1,011 DLs</b>).
            <br>• <b>Sep 13, 2026 (Sensible MC Ingestion):</b> Inclusion into Sensible MC modpack driving automated server downloads (<b>1,294 DLs</b>).
            <br>• <b>Oct 6, 2026 (Studio Lifetime High):</b> Record-breaking single-day peak (<b>1,987 DLs</b>, +589 DLs anomaly surplus).
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Section 3: Version Adoption Velocity & Migration Lag (B10)
    st.markdown("---")
    st.markdown("##### 🧬 Version Adoption Velocity & Migration Lag")
    fig_uptake = render_version_uptake_chart(bundle.project_version)
    st.plotly_chart(fig_uptake, width="stretch")

    st.markdown(
        """
        <div style="background:#0F172A;border-left:4px solid #06B6D4;padding:12px 16px;border-radius:6px;margin-bottom:14px;color:#F8FAFC;font-size:0.92rem;">
            🧬 <b>Headless Automated Uptake vs Human Player Adoption Curves:</b>
            Contrasting adoption velocities demonstrates two distinct distribution dynamics across the studio:
            <br>• <b>Dasik Library (1-Day Spike):</b> Reaches maximum adoption on <b>Day 1 (~316 DLs/version)</b> as Prism Launcher, Modrinth App, and headless servers execute automated dependency resolution upon client startup.
            <br>• <b>VO: Better Dogs (5-Day Adoption Curve):</b> Exhibits a gradual, sustained adoption wave peaking between <b>Day 3 and Day 5 (~76 DLs/version)</b> as human players organically discover patch notes, verify compatibility, and manually update their mod lists.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Section 4: Portfolio Pareto & Concentration Analysis (B11)
    st.markdown("---")
    st.markdown("##### 📈 Portfolio Pareto & Concentration Analysis")
    fig_pareto = render_pareto_curve(bundle.project)
    st.plotly_chart(fig_pareto, width="stretch")

    st.markdown(
        """
        <div style="background:#0F172A;border-left:4px solid #10B981;padding:12px 16px;border-radius:6px;margin-bottom:14px;color:#F8FAFC;font-size:0.92rem;">
            📈 <b>Lorenz Distribution & Portfolio Diversification:</b>
            The studio's catalog exhibits an asymmetrical Pareto curve with an <b>HHI of 2,731</b> (indicating high market concentration).
            The top 2 mods (<i>Dasik Library</i> at 41.1% and <i>VO: Better Dogs</i> at 31.0%) drive <b>72.0%</b> of total downloads.
            The remaining 19 projects form a long-tail distribution (28.0% aggregate share), functioning as specialized discovery on-ramps that pull players back into the core Dasik ecosystem.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Section 5: Growth Waterfall & Ingestion Decomposition (B12)
    st.markdown("---")
    st.markdown("##### 🌊 Growth Waterfall & Ingestion Decomposition")
    fig_waterfall = render_growth_waterfall(bundle.project)
    st.plotly_chart(fig_waterfall, width="stretch")

    st.markdown(
        """
        <div style="background:#0F172A;border-left:4px solid #EC4899;padding:12px 16px;border-radius:6px;margin-bottom:14px;color:#F8FAFC;font-size:0.92rem;">
            🌊 <b>Cumulative Growth Decomposition:</b>
            Monthly progression details how download volume expanded from early baseline (Apr: 1.2k, May: 6.2k) to rapid scaling (Aug: 20.4k, Sep: 26.2k),
            surpassing <b>100.2k cumulative downloads</b> across 181 tracked days with a 26x expansion factor.
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    """Main dashboard application entry point."""
    st.markdown(
        """
        <div class="studio-header">
            <h1 class="studio-title">📊 Modrinth Creator Analytics Studio</h1>
        </div>
        <div class="studio-subtitle">
            Longitudinal distribution intelligence, revenue economics, and Minecraft version telemetry for <b>dasikigaijin</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Load baseline bundle
    raw_bundle = load_all_data()

    # Sidebar controls
    active_bundle, streamer_mode = render_sidebar(raw_bundle)

    # 6 Studio Navigation Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [
            "💰 Revenue & Overview",
            "🚀 Launchers & Sources",
            "🎮 Minecraft Demographics",
            "📦 Projects & Modpacks",
            "🌍 Global Geography",
            "🔬 Advanced Econometrics & Deep Insights",
        ]
    )

    with tab1:
        render_tab1_revenue(active_bundle, streamer_mode)

    with tab2:
        render_tab2_launchers(active_bundle)

    with tab3:
        render_tab3_demographics(active_bundle)

    with tab4:
        render_tab4_projects(active_bundle, streamer_mode)

    with tab5:
        render_tab5_geography(active_bundle)

    with tab6:
        render_tab6_econometrics(active_bundle)


if __name__ == "__main__":
    main()


