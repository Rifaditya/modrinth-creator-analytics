"""Modrinth Creator Analytics Studio - Streamlit Web Dashboard.

Provides executive analytics, revenue economics, launcher telemetry, and predictive
forecasting for dasikigaijin across all 21 Minecraft mod projects.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

import streamlit as st

from src.charts import (
    render_daily_downloads_chart,
    render_monetization_donut_chart,
    render_revenue_velocity_chart,
)
from src.loader import ModrinthDataBundle, load_all_data
from src.metrics import (
    calculate_kpis,
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
        active_bundle = filter_bundle_by_date(raw_bundle, start_date, end_date)
    else:
        # User is actively picking the range in the widget
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
            generated monetized ad impressions. The remaining 
            <b>{kpis['unmonetized_downloads']:,} (90.1%)</b> were fetched via automated third-party launchers
            (Prism Launcher, CurseForge App, Modrinth App background updates) or adblocked sessions.
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

    proj = project_milestone_earnings(
        target_downloads=target_dl,
        blended_rpm=kpis["blended_rpm"],
        monetized_rpm=kpis["monetized_rpm"],
        monetization_rate=kpis["monetization_rate"],
    )

    with f_col_right:
        p_card1, p_card2, p_card3 = st.columns(3)
        with p_card1:
            st.metric(
                label="Projected Monetized DLs",
                value=f"{proj['projected_monetized_downloads']:,.0f}",
                delta=f"{kpis['monetization_rate']:.1f}% Yield",
            )
        with p_card2:
            blended_proj = (
                "$ •••••"
                if streamer_mode
                else f"${proj['projected_blended_earnings']:,.2f}"
            )
            st.metric(
                label="Projected Payout (USD)",
                value=blended_proj,
                delta=f"@ ${kpis['blended_rpm']:.2f} Blended RPM",
            )
        with p_card3:
            pts_proj = (
                "••••• pts"
                if streamer_mode
                else f"{proj['projected_blended_earnings'] * 100:,.0f} pts"
            )
            st.metric(
                label="Creator Reward Points",
                value=pts_proj,
                delta="NET-60 Redemption",
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

    # 5 Studio Navigation Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "💰 Revenue & Overview",
            "🚀 Launchers & Sources",
            "🎮 Minecraft Demographics",
            "📦 Projects & Modpacks",
            "🌍 Global Geography",
        ]
    )

    with tab1:
        render_tab1_revenue(active_bundle, streamer_mode)

    with tab2:
        st.info(
            "🚀 **Launchers & Distribution Sources**: Scheduled for Step 3 implementation.\n\n"
            "Will feature Prism vs CurseForge App vs Modrinth launcher distribution, API query analysis, and download reasons."
        )

    with tab3:
        st.info(
            "🎮 **Minecraft Demographics & Loader Breakdown**: Scheduled for Step 3 implementation.\n\n"
            "Will feature Minecraft version distributions (MC 26.1, 26.2, 26.3, 1.21.1) and Mod Loader market shares (Fabric vs NeoForge vs Forge)."
        )

    with tab4:
        st.info(
            "📦 **Projects & Modpacks Breakdown**: Scheduled for Step 4 implementation.\n\n"
            "Will feature project leaderboard, version catalogs, dependent modpack telemetry, and playtime rankings."
        )

    with tab5:
        st.info(
            "🌍 **Global Geography Breakdown**: Scheduled for Step 4 implementation.\n\n"
            "Will feature choropleth world map, top country tables, and regional engagement analytics."
        )


if __name__ == "__main__":
    main()
