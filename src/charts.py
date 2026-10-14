"""Chart generation module for Modrinth Creator Analytics.

Renders dark-themed, responsive Plotly figures adhering to the studio's Komikku
purple/cyan/emerald visual design standard.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Dark palette constants
BG_TRANSPARENT = "rgba(0, 0, 0, 0)"
BG_PLOT = "rgba(15, 23, 42, 0.55)"
GRID_COLOR = "#334155"
TEXT_COLOR = "#F8FAFC"
TEXT_MUTED = "#94A3B8"

COLOR_PURPLE = "#8B5CF6"  # Komikku violet
COLOR_CYAN = "#06B6D4"    # Cyber cyan
COLOR_EMERALD = "#10B981" # Emerald profit
COLOR_SLATE = "#64748B"   # Slate unmonetized
COLOR_AMBER = "#F59E0B"   # Amber warning/legacy
COLOR_PINK = "#EC4899"    # Pink accent
COLOR_INDIGO = "#6366F1"  # Indigo accent
COLOR_FUCHSIA = "#D946EF" # Fuchsia accent
COLOR_BLUE = "#3B82F6"    # Blue accent
COLOR_TEAL = "#14B8A6"    # Teal accent
COLOR_LAVENDER = "#A78BFA"# Lavender modern

SOURCE_COLOR_MAP: Dict[str, str] = {
    "Modrinth App": "#8B5CF6",       # Studio violet
    "Modrinth Website": "#06B6D4",   # Cyber cyan
    "Prism Launcher": "#10B981",     # Emerald
    "PCL2": "#F59E0B",               # Amber
    "Lunar Client": "#EC4899",       # Pink
    "Dawn": "#A855F7",               # Purple
    "Unknown": "#64748B",            # Slate
    "ATLauncher": "#3B82F6",         # Blue
    "Modrinth Hosting": "#14B8A6",   # Teal
    "HMCL": "#EAB308",               # Yellow
    "FCL": "#6366F1",                # Indigo
    "PojavLauncher": "#F97316",      # Orange
    "Feather Client": "#22C55E",     # Green
    "NoRisk Client": "#D946EF",      # Fuchsia
    "PolyMC": "#0284C7",             # Sky
}

REASON_COLOR_MAP: Dict[str, str] = {
    "Standalone": "#06B6D4",
    "Modpack": "#8B5CF6",
    "Update": "#10B981",
    "Dependency": "#F59E0B",
    "Unknown": "#64748B",
}

LOADER_COLOR_MAP: Dict[str, str] = {
    "Fabric": "#8B5CF6",
    "Unknown": "#64748B",
    "NeoForge": "#F59E0B",
    "Forge": "#06B6D4",
    "Quilt": "#EC4899",
}


def get_version_color(version_str: str) -> str:
    """Return theme color mapped to Minecraft generational anchor."""
    v = str(version_str).strip().lower()
    if v == "26.2":
        return "#8B5CF6"  # Sovereign Lead Violet
    elif v == "26.1.2":
        return "#A78BFA"  # Violet lighter
    elif v.startswith("26.3"):
        return "#06B6D4"  # Cyber Cyan
    elif v == "26.1":
        return "#38BDF8"  # Light Cyan
    elif v.startswith("26."):
        return "#818CF8"  # Indigo (26.x snapshots / pre-releases)
    elif v.startswith("1.21"):
        return "#10B981"  # Emerald
    elif v.startswith("1.20"):
        return "#F59E0B"  # Amber
    elif "unknown" in v:
        return "#64748B"  # Slate
    else:
        return "#64748B"  # Slate for other / build versions


def _empty_figure(message: str = "No data available") -> go.Figure:
    """Return an empty placeholder figure with a clean centered message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=14, color=TEXT_MUTED),
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG_TRANSPARENT,
        plot_bgcolor=BG_TRANSPARENT,
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=False, showticklabels=False),
    )
    return fig


def render_revenue_velocity_chart(member_df: pd.DataFrame) -> go.Figure:
    """Render daily revenue bars alongside a cumulative revenue line curve.

    Args:
        member_df: DataFrame with 'Date' and 'Revenue' columns.

    Returns:
        Plotly Figure with dual y-axes.
    """
    if member_df.empty or "Revenue" not in member_df.columns:
        return _empty_figure("No revenue data available for this range")

    # Aggregate by date
    daily = (
        member_df.groupby("Date", as_index=False)["Revenue"]
        .sum()
        .sort_values("Date")
        .reset_index(drop=True)
    )
    daily["Cumulative Revenue"] = daily["Revenue"].cumsum()

    fig = make_subplots(
        specs=[[{"secondary_y": True}]],
    )

    # Bar chart for Daily Revenue
    fig.add_trace(
        go.Bar(
            x=daily["Date"],
            y=daily["Revenue"],
            name="Daily Revenue ($)",
            marker=dict(
                color=COLOR_PURPLE,
                line=dict(color="rgba(139, 92, 246, 0.4)", width=1),
            ),
            hovertemplate="<b>%{x|%b %d, %Y}</b><br>Daily Revenue: $%{y:.3f}<extra></extra>",
        ),
        secondary_y=False,
    )

    # Smooth curve for Cumulative Revenue
    fig.add_trace(
        go.Scatter(
            x=daily["Date"],
            y=daily["Cumulative Revenue"],
            name="Cumulative Revenue ($)",
            mode="lines",
            line=dict(
                color=COLOR_EMERALD,
                width=3,
                shape="spline",
            ),
            hovertemplate="<b>%{x|%b %d, %Y}</b><br>Cumulative: $%{y:.2f}<extra></extra>",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title=dict(
            text="<b>Daily Velocity & Cumulative Revenue</b>",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.01,
            y=0.96,
        ),
        template="plotly_dark",
        paper_bgcolor=BG_TRANSPARENT,
        plot_bgcolor=BG_PLOT,
        font=dict(family="Inter, system-ui, sans-serif", color=TEXT_COLOR),
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(30, 41, 59, 0.7)",
            bordercolor=GRID_COLOR,
            borderwidth=1,
            font=dict(size=11),
        ),
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
    )
    fig.update_yaxes(
        title_text="Daily Revenue ($)",
        title_font=dict(size=12, color=COLOR_PURPLE),
        tickprefix="$",
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text="Cumulative ($)",
        title_font=dict(size=12, color=COLOR_EMERALD),
        tickprefix="$",
        showgrid=False,
        zeroline=False,
        secondary_y=True,
    )

    return fig


def render_monetization_donut_chart(monetization_df: pd.DataFrame) -> go.Figure:
    """Render a donut chart comparing Monetized vs Unmonetized downloads.

    Args:
        monetization_df: DataFrame with 'Monetization' and 'Downloads' columns.

    Returns:
        Plotly Figure showing the donut breakdown with center annotation.
    """
    if monetization_df.empty or "Downloads" not in monetization_df.columns:
        return _empty_figure("No monetization breakdown data available")

    agg = (
        monetization_df.groupby("Monetization", as_index=False)["Downloads"]
        .sum()
        .sort_values("Downloads", ascending=False)
        .reset_index(drop=True)
    )

    total_downloads = agg["Downloads"].sum()
    monetized_row = agg[agg["Monetization"] == "Monetized"]
    monetized_dls = monetized_row["Downloads"].iloc[0] if not monetized_row.empty else 0
    monetized_pct = (
        (monetized_dls / total_downloads * 100.0) if total_downloads > 0 else 0.0
    )

    color_map = {
        "Monetized": COLOR_EMERALD,
        "Unmonetized": COLOR_SLATE,
    }
    slice_colors = [color_map.get(lbl, COLOR_PURPLE) for lbl in agg["Monetization"]]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=agg["Monetization"],
                values=agg["Downloads"],
                hole=0.62,
                marker=dict(
                    colors=slice_colors,
                    line=dict(color="#0F172A", width=2),
                ),
                textinfo="percent+label",
                textfont=dict(color=TEXT_COLOR, size=12),
                hovertemplate="<b>%{label}</b><br>Downloads: %{value:,.0f}<br>Share: %{percent}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        title=dict(
            text="<b>Impression Monetization Ratio</b>",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.01,
            y=0.96,
        ),
        template="plotly_dark",
        paper_bgcolor=BG_TRANSPARENT,
        plot_bgcolor=BG_TRANSPARENT,
        font=dict(family="Inter, system-ui, sans-serif", color=TEXT_COLOR),
        margin=dict(l=20, r=20, t=60, b=30),
        showlegend=False,
        annotations=[
            dict(
                text=(
                    f"<b style='font-size:24px;color:{COLOR_EMERALD}'>"
                    f"{monetized_pct:.1f}%</b><br>"
                    f"<span style='font-size:11px;color:{TEXT_MUTED}'>Monetized Rate</span>"
                ),
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(family="Inter, system-ui, sans-serif"),
            )
        ],
    )

    return fig


def render_daily_downloads_chart(project_df: pd.DataFrame) -> go.Figure:
    """Render a daily downloads area/line chart over time.

    Args:
        project_df: DataFrame with 'Date' and 'Downloads' columns.

    Returns:
        Plotly Figure showing daily download volume with smooth spline.
    """
    if project_df.empty or "Downloads" not in project_df.columns:
        return _empty_figure("No download activity available for this range")

    daily = (
        project_df.groupby("Date", as_index=False)["Downloads"]
        .sum()
        .sort_values("Date")
        .reset_index(drop=True)
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=daily["Date"],
            y=daily["Downloads"],
            name="Daily Downloads",
            mode="lines",
            fill="tozeroy",
            line=dict(
                color=COLOR_CYAN,
                width=2.5,
                shape="spline",
            ),
            fillcolor="rgba(6, 182, 212, 0.12)",
            hovertemplate="<b>%{x|%b %d, %Y}</b><br>Downloads: %{y:,.0f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(
            text="<b>Daily Downloads Velocity</b>",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.01,
            y=0.96,
        ),
        template="plotly_dark",
        paper_bgcolor=BG_TRANSPARENT,
        plot_bgcolor=BG_PLOT,
        font=dict(family="Inter, system-ui, sans-serif", color=TEXT_COLOR),
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode="x unified",
        showlegend=False,
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
    )
    fig.update_yaxes(
        title_text="Downloads",
        title_font=dict(size=12, color=COLOR_CYAN),
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
    )

    return fig


def render_download_sources_chart(source_df: pd.DataFrame) -> go.Figure:
    """Render horizontal bar chart of download sources sorted descending.

    Args:
        source_df: DataFrame with 'Download source' and 'Downloads' columns.

    Returns:
        Plotly Figure showing download volumes per launcher and acquisition channel.
    """
    if (
        source_df.empty
        or "Downloads" not in source_df.columns
        or "Download source" not in source_df.columns
    ):
        return _empty_figure("No download source telemetry available")

    agg = (
        source_df.groupby("Download source", as_index=False)["Downloads"]
        .sum()
        .sort_values("Downloads", ascending=False)
        .reset_index(drop=True)
    )
    total_dls = agg["Downloads"].sum()
    if total_dls == 0:
        return _empty_figure("No download source telemetry available")

    # If more than 12 sources, retain top 11 and bucket remainder into 'Other Launchers'
    if len(agg) > 12:
        top_slice = agg.head(11).copy()
        other_sum = int(agg.iloc[11:]["Downloads"].sum())
        other_df = pd.DataFrame(
            [{"Download source": "Other Launchers", "Downloads": other_sum}]
        )
        plot_df = pd.concat([top_slice, other_df], ignore_index=True)
    else:
        plot_df = agg.copy()

    plot_df["Percentage"] = plot_df["Downloads"] / total_dls * 100.0
    # Ascending sort so highest volume appears at the top in horizontal layout
    plot_df = plot_df.sort_values("Downloads", ascending=True).reset_index(drop=True)

    colors = [
        SOURCE_COLOR_MAP.get(src, "#64748B" if "Other" in src else "#94A3B8")
        for src in plot_df["Download source"]
    ]

    fig = go.Figure(
        go.Bar(
            x=plot_df["Downloads"],
            y=plot_df["Download source"],
            orientation="h",
            marker=dict(
                color=colors,
                line=dict(color="#0F172A", width=1),
            ),
            text=[
                f"{v:,.0f} ({p:.1f}%)"
                for v, p in zip(plot_df["Downloads"], plot_df["Percentage"])
            ],
            textposition="outside",
            textfont=dict(color=TEXT_COLOR, size=11),
            customdata=plot_df["Percentage"],
            hovertemplate="<b>%{y}</b><br>Downloads: %{x:,.0f}<br>Share: %{customdata:.1f}%<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(
            text="<b>Downloads by Launcher & Acquisition Source</b>",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.01,
            y=0.96,
        ),
        template="plotly_dark",
        paper_bgcolor=BG_TRANSPARENT,
        plot_bgcolor=BG_PLOT,
        font=dict(family="Inter, system-ui, sans-serif", color=TEXT_COLOR),
        margin=dict(l=40, r=80, t=60, b=40),
        xaxis=dict(
            title="Downloads",
            showgrid=True,
            gridcolor=GRID_COLOR,
            zeroline=False,
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
        ),
        showlegend=False,
        height=520,
    )
    return fig


def render_download_reasons_chart(reason_df: pd.DataFrame) -> go.Figure:
    """Render donut chart of download reasons (Standalone, Modpack, Update, Dependency, Unknown).

    Args:
        reason_df: DataFrame with 'Download reason' and 'Downloads' columns.

    Returns:
        Plotly Figure illustrating distribution by installation reason with center annotation.
    """
    if (
        reason_df.empty
        or "Downloads" not in reason_df.columns
        or "Download reason" not in reason_df.columns
    ):
        return _empty_figure("No download reason telemetry available")

    agg = (
        reason_df.groupby("Download reason", as_index=False)["Downloads"]
        .sum()
        .sort_values("Downloads", ascending=False)
        .reset_index(drop=True)
    )
    total_dls = agg["Downloads"].sum()
    if total_dls == 0:
        return _empty_figure("No download reason telemetry available")

    colors = [REASON_COLOR_MAP.get(r, "#94A3B8") for r in agg["Download reason"]]

    # Ecosystem installs = Modpack + Dependency
    eco_mask = agg["Download reason"].isin(["Modpack", "Dependency"])
    eco_dls = agg.loc[eco_mask, "Downloads"].sum()
    eco_pct = (eco_dls / total_dls * 100.0) if total_dls > 0 else 0.0

    fig = go.Figure(
        go.Pie(
            labels=agg["Download reason"],
            values=agg["Downloads"],
            hole=0.60,
            marker=dict(
                colors=colors,
                line=dict(color="#0F172A", width=2),
            ),
            textinfo="percent+label",
            textfont=dict(color=TEXT_COLOR, size=11),
            hovertemplate="<b>%{label}</b><br>Downloads: %{value:,.0f}<br>Share: %{percent}<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(
            text="<b>Download Reason Breakdown</b>",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.01,
            y=0.96,
        ),
        template="plotly_dark",
        paper_bgcolor=BG_TRANSPARENT,
        plot_bgcolor=BG_TRANSPARENT,
        font=dict(family="Inter, system-ui, sans-serif", color=TEXT_COLOR),
        margin=dict(l=20, r=20, t=60, b=30),
        showlegend=False,
        annotations=[
            dict(
                text=(
                    f"<b style='font-size:24px;color:{COLOR_PURPLE}'>"
                    f"{eco_pct:.1f}%</b><br>"
                    f"<span style='font-size:11px;color:{TEXT_MUTED}'>Ecosystem Installs<br>(Modpack + Dep)</span>"
                ),
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(family="Inter, system-ui, sans-serif"),
            )
        ],
        height=520,
    )
    return fig


def render_game_versions_chart(
    game_version_df: pd.DataFrame,
    enriched_pv_df: Optional[pd.DataFrame] = None,
    use_enriched: bool = True,
) -> go.Figure:
    """Render vertical bar chart of Minecraft version adoption.

    Args:
        game_version_df: Raw game_version DataFrame.
        enriched_pv_df: Optional enriched project_version DataFrame.
        use_enriched: Whether to prioritize enriched project version data over raw telemetry.

    Returns:
        Plotly Figure showing version volume with anchor-calibrated palette.
    """
    if (
        use_enriched
        and enriched_pv_df is not None
        and not enriched_pv_df.empty
        and "Target Game Version" in enriched_pv_df.columns
        and "Downloads" in enriched_pv_df.columns
    ):
        target_df = enriched_pv_df
        ver_col = "Target Game Version"
        title_tag = "Enriched Engine"
    elif (
        not game_version_df.empty
        and "Game version" in game_version_df.columns
        and "Downloads" in game_version_df.columns
    ):
        target_df = game_version_df
        ver_col = "Game version"
        title_tag = "Raw Telemetry"
    else:
        return _empty_figure("No game version telemetry available")

    agg = (
        target_df.groupby(ver_col, as_index=False)["Downloads"]
        .sum()
        .sort_values("Downloads", ascending=False)
        .reset_index(drop=True)
    )
    total_dls = agg["Downloads"].sum()
    if total_dls == 0:
        return _empty_figure("No game version telemetry available")

    # If more than 10 versions, retain top 9 and bucket rest into 'Other Snapshots'
    if len(agg) > 10:
        top_slice = agg.head(9).copy()
        other_sum = int(agg.iloc[9:]["Downloads"].sum())
        other_df = pd.DataFrame([{ver_col: "Other Snapshots", "Downloads": other_sum}])
        plot_df = pd.concat([top_slice, other_df], ignore_index=True)
    else:
        plot_df = agg.copy()

    plot_df["Percentage"] = plot_df["Downloads"] / total_dls * 100.0
    colors = [get_version_color(v) for v in plot_df[ver_col]]

    fig = go.Figure(
        go.Bar(
            x=plot_df[ver_col],
            y=plot_df["Downloads"],
            marker=dict(
                color=colors,
                line=dict(color="#0F172A", width=1),
            ),
            text=[f"{v:,.0f}" for v in plot_df["Downloads"]],
            textposition="outside",
            textfont=dict(color=TEXT_COLOR, size=11),
            customdata=plot_df["Percentage"],
            hovertemplate="<b>MC %{x}</b><br>Downloads: %{y:,.0f}<br>Share: %{customdata:.1f}%<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(
            text=f"<b>Minecraft Version Adoption ({title_tag})</b>",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.01,
            y=0.96,
        ),
        template="plotly_dark",
        paper_bgcolor=BG_TRANSPARENT,
        plot_bgcolor=BG_PLOT,
        font=dict(family="Inter, system-ui, sans-serif", color=TEXT_COLOR),
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis=dict(
            title="Target Minecraft Anchor",
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            title="Downloads",
            showgrid=True,
            gridcolor=GRID_COLOR,
            zeroline=False,
        ),
        showlegend=False,
        height=480,
    )
    return fig


def render_game_version_timeline_chart(
    df: pd.DataFrame, version_col: str = "Target Game Version"
) -> go.Figure:
    """Render daily stacked area chart showing top 5 game versions over time.

    Args:
        df: DataFrame containing 'Date', 'Downloads', and a version column.
        version_col: Column name identifying the Minecraft version.

    Returns:
        Plotly Figure with smooth stacked area curves.
    """
    if df.empty or "Date" not in df.columns or "Downloads" not in df.columns:
        return _empty_figure("No version timeline data available")

    # Fallback column resolution
    if version_col not in df.columns:
        if "Target Game Version" in df.columns:
            version_col = "Target Game Version"
        elif "Game version" in df.columns:
            version_col = "Game version"
        else:
            return _empty_figure("No version column found in timeline data")

    # Identify top 5 versions by cumulative downloads
    top_versions = (
        df.groupby(version_col)["Downloads"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .index.tolist()
    )

    if not top_versions:
        return _empty_figure("No version data available for timeline")

    sub_df = df[df[version_col].isin(top_versions)].copy()
    timeline = (
        sub_df.groupby(["Date", version_col], as_index=False)["Downloads"]
        .sum()
    )

    pivot = (
        timeline.pivot(index="Date", columns=version_col, values="Downloads")
        .fillna(0)
        .sort_index()
    )

    fig = go.Figure()

    for v in top_versions:
        if v not in pivot.columns:
            continue
        color = get_version_color(v)
        fig.add_trace(
            go.Scatter(
                x=pivot.index,
                y=pivot[v],
                name=f"MC {v}",
                mode="lines",
                stackgroup="one",
                line=dict(color=color, width=1.5),
                hovertemplate=f"<b>MC {v}</b>: %{{y:,.0f}} DLs<extra></extra>",
            )
        )

    fig.update_layout(
        title=dict(
            text="<b>Game Version Adoption Velocity (Top 5 Anchors Over Time)</b>",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.01,
            y=0.96,
        ),
        template="plotly_dark",
        paper_bgcolor=BG_TRANSPARENT,
        plot_bgcolor=BG_PLOT,
        font=dict(family="Inter, system-ui, sans-serif", color=TEXT_COLOR),
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(30, 41, 59, 0.7)",
            bordercolor=GRID_COLOR,
            borderwidth=1,
            font=dict(size=11),
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor=GRID_COLOR,
            zeroline=False,
        ),
        yaxis=dict(
            title="Daily Downloads",
            showgrid=True,
            gridcolor=GRID_COLOR,
            zeroline=False,
        ),
        height=450,
    )
    return fig


def render_loader_donut_chart(loader_df: pd.DataFrame) -> go.Figure:
    """Render donut chart showing Fabric vs Unknown mod loader distribution.

    Args:
        loader_df: DataFrame with 'Loader' and 'Downloads' columns.

    Returns:
        Plotly Figure showing loader shares with center annotation.
    """
    if (
        loader_df.empty
        or "Downloads" not in loader_df.columns
        or "Loader" not in loader_df.columns
    ):
        return _empty_figure("No mod loader telemetry available")

    agg = (
        loader_df.groupby("Loader", as_index=False)["Downloads"]
        .sum()
        .sort_values("Downloads", ascending=False)
        .reset_index(drop=True)
    )
    total_dls = agg["Downloads"].sum()
    if total_dls == 0:
        return _empty_figure("No mod loader telemetry available")

    colors = [LOADER_COLOR_MAP.get(ldr, "#94A3B8") for ldr in agg["Loader"]]

    fig = go.Figure(
        go.Pie(
            labels=agg["Loader"],
            values=agg["Downloads"],
            hole=0.62,
            marker=dict(
                colors=colors,
                line=dict(color="#0F172A", width=2),
            ),
            textinfo="percent+label",
            textfont=dict(color=TEXT_COLOR, size=12),
            hovertemplate="<b>%{label}</b><br>Downloads: %{value:,.0f}<br>Share: %{percent}<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(
            text="<b>Mod Loader Distribution</b>",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.01,
            y=0.96,
        ),
        template="plotly_dark",
        paper_bgcolor=BG_TRANSPARENT,
        plot_bgcolor=BG_TRANSPARENT,
        font=dict(family="Inter, system-ui, sans-serif", color=TEXT_COLOR),
        margin=dict(l=20, r=20, t=60, b=30),
        showlegend=False,
        annotations=[
            dict(
                text=(
                    f"<b style='font-size:22px;color:{COLOR_PURPLE}'>Fabric 100%</b><br>"
                    f"<span style='font-size:11px;color:{TEXT_MUTED}'>Identified Runtime</span>"
                ),
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(family="Inter, system-ui, sans-serif"),
            )
        ],
        height=480,
    )
    return fig


def render_project_leaderboard_chart(project_summary_df: pd.DataFrame) -> go.Figure:
    """Render horizontal bar chart ranking projects by total downloads.

    Args:
        project_summary_df: DataFrame with 'Project', 'Downloads', and optional 'Share %', 'Views'.

    Returns:
        Plotly Figure styled with violet-to-cyan gradient and value labels.
    """
    if (
        project_summary_df.empty
        or "Downloads" not in project_summary_df.columns
        or "Project" not in project_summary_df.columns
    ):
        return _empty_figure("No project catalog telemetry available")

    # Sort ascending for horizontal display so top project is at the top
    plot_df = (
        project_summary_df.sort_values("Downloads", ascending=True)
        .reset_index(drop=True)
    )

    n = len(plot_df)
    # Generate smooth gradient from cyan (#06B6D4) at bottom to violet (#8B5CF6) at top
    colors = []
    for i in range(n):
        ratio = i / max(n - 1, 1)
        r = int(6 + (139 - 6) * ratio)
        g = int(182 + (92 - 182) * ratio)
        b = int(212 + (246 - 212) * ratio)
        colors.append(f"rgb({r}, {g}, {b})")

    # Format text labels
    if "Share %" in plot_df.columns:
        text_labels = [
            f"{v:,.0f} ({p:.1f}%)"
            for v, p in zip(plot_df["Downloads"], plot_df["Share %"])
        ]
    else:
        text_labels = [f"{v:,.0f}" for v in plot_df["Downloads"]]

    customdata = (
        plot_df[["Share %", "Views"]]
        if {"Share %", "Views"}.issubset(plot_df.columns)
        else None
    )
    hovertemplate = (
        "<b>%{y}</b><br>Downloads: %{x:,.0f}<br>Share: %{customdata[0]:.1f}%<br>Views: %{customdata[1]:,.0f}<extra></extra>"
        if customdata is not None
        else "<b>%{y}</b><br>Downloads: %{x:,.0f}<extra></extra>"
    )

    fig = go.Figure(
        go.Bar(
            x=plot_df["Downloads"],
            y=plot_df["Project"],
            orientation="h",
            marker=dict(
                color=colors,
                line=dict(color="#0F172A", width=1),
            ),
            text=text_labels,
            textposition="outside",
            textfont=dict(color=TEXT_COLOR, size=11),
            customdata=customdata,
            hovertemplate=hovertemplate,
        )
    )

    fig.update_layout(
        title=dict(
            text="<b>Project Download Catalog Leaderboard</b>",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.01,
            y=0.96,
        ),
        template="plotly_dark",
        paper_bgcolor=BG_TRANSPARENT,
        plot_bgcolor=BG_PLOT,
        font=dict(family="Inter, system-ui, sans-serif", color=TEXT_COLOR),
        margin=dict(l=40, r=80, t=60, b=40),
        xaxis=dict(
            title="Total Downloads",
            showgrid=True,
            gridcolor=GRID_COLOR,
            zeroline=False,
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
        ),
        showlegend=False,
        height=max(500, n * 26),
    )
    return fig


def render_dependent_modpacks_chart(
    dep_df: pd.DataFrame, top_n: int = 12
) -> go.Figure:
    """Render horizontal bar chart of top dependent modpacks and consumer projects.

    Args:
        dep_df: DataFrame with 'Dependent project' and 'Downloads' columns.
        top_n: Number of top dependent projects to display.

    Returns:
        Plotly Figure styled with emerald/amber markers and download count labels.
    """
    if (
        dep_df.empty
        or "Dependent project" not in dep_df.columns
        or "Downloads" not in dep_df.columns
    ):
        return _empty_figure("No dependent modpack telemetry available")

    # Exclude unresolved 'Unknown' consumer rows to isolate identified modpacks & mods
    sub = dep_df[dep_df["Dependent project"] != "Unknown"]
    if sub.empty:
        return _empty_figure("No identified external dependent modpacks")

    agg = (
        sub.groupby("Dependent project", as_index=False)["Downloads"]
        .sum()
        .sort_values("Downloads", ascending=False)
        .head(top_n)
    )

    # Sort ascending for horizontal bar display so highest volume is on top
    plot_df = agg.sort_values("Downloads", ascending=True).reset_index(drop=True)

    def _is_third_party(name: str) -> bool:
        s = str(name).strip()
        return not (
            s.startswith("VO:")
            or s.startswith("IG:")
            or s.startswith("DG:")
            or "Dasik" in s
            or "gamerules" in s.lower()
        )

    # Emerald for external modpacks (Sensible MC, Legacies), amber for studio internal dependencies
    colors = [
        COLOR_EMERALD if _is_third_party(p) else COLOR_AMBER
        for p in plot_df["Dependent project"]
    ]

    fig = go.Figure(
        go.Bar(
            x=plot_df["Downloads"],
            y=plot_df["Dependent project"],
            orientation="h",
            marker=dict(
                color=colors,
                line=dict(color="#0F172A", width=1),
            ),
            text=[f"{v:,.0f}" for v in plot_df["Downloads"]],
            textposition="outside",
            textfont=dict(color=TEXT_COLOR, size=11),
            hovertemplate="<b>%{y}</b><br>Attributed Downloads: %{x:,.0f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(
            text="<b>Top Dependent Modpacks & Ecosystem Consumers</b>",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.01,
            y=0.96,
        ),
        template="plotly_dark",
        paper_bgcolor=BG_TRANSPARENT,
        plot_bgcolor=BG_PLOT,
        font=dict(family="Inter, system-ui, sans-serif", color=TEXT_COLOR),
        margin=dict(l=40, r=70, t=60, b=40),
        xaxis=dict(
            title="Downloads Attributed",
            showgrid=True,
            gridcolor=GRID_COLOR,
            zeroline=False,
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
        ),
        showlegend=False,
        height=max(420, len(plot_df) * 32),
    )
    return fig


def render_single_project_velocity(
    project_df: pd.DataFrame, project_name: str
) -> go.Figure:
    """Render daily downloads area curve over time for a single mod project.

    Args:
        project_df: DataFrame with 'Date', 'Project', and 'Downloads' columns.
        project_name: The name of the project to isolate.

    Returns:
        Plotly Figure showing daily download trajectory.
    """
    if (
        project_df.empty
        or "Project" not in project_df.columns
        or "Date" not in project_df.columns
        or "Downloads" not in project_df.columns
    ):
        return _empty_figure(f"No velocity telemetry available for {project_name}")

    sub = project_df[project_df["Project"] == project_name]
    if sub.empty:
        return _empty_figure(f"No velocity telemetry available for {project_name}")

    daily = (
        sub.groupby("Date", as_index=False)["Downloads"]
        .sum()
        .sort_values("Date")
        .reset_index(drop=True)
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily["Date"],
            y=daily["Downloads"],
            name="Daily Downloads",
            mode="lines",
            fill="tozeroy",
            line=dict(
                color=COLOR_PURPLE,
                width=2.5,
                shape="spline",
            ),
            fillcolor="rgba(139, 92, 246, 0.15)",
            hovertemplate="<b>%{x|%b %d, %Y}</b><br>Downloads: %{y:,.0f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(
            text=f"<b>Daily Velocity: {project_name}</b>",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.01,
            y=0.96,
        ),
        template="plotly_dark",
        paper_bgcolor=BG_TRANSPARENT,
        plot_bgcolor=BG_PLOT,
        font=dict(family="Inter, system-ui, sans-serif", color=TEXT_COLOR),
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode="x unified",
        showlegend=False,
        height=380,
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID_COLOR, zeroline=False)
    fig.update_yaxes(
        title="Downloads",
        title_font=dict(size=12, color=COLOR_PURPLE),
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
    )
    return fig


def render_project_version_adoption_chart(
    project_version_df: pd.DataFrame, project_name: str
) -> go.Figure:
    """Render vertical bar chart of downloads by project version for a single mod.

    Args:
        project_version_df: DataFrame with 'Project', 'Project version', and 'Downloads'.
        project_name: Target project name to filter by.

    Returns:
        Plotly Figure showing top release version adoption.
    """
    if (
        project_version_df.empty
        or "Project" not in project_version_df.columns
        or "Project version" not in project_version_df.columns
        or "Downloads" not in project_version_df.columns
    ):
        return _empty_figure(f"No version telemetry available for {project_name}")

    sub = project_version_df[project_version_df["Project"] == project_name]
    if sub.empty:
        return _empty_figure(f"No version telemetry available for {project_name}")

    total_mod_dls = sub["Downloads"].sum()
    agg = (
        sub.groupby("Project version", as_index=False)["Downloads"]
        .sum()
        .sort_values("Downloads", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )

    agg["Percentage"] = (
        (agg["Downloads"] / total_mod_dls * 100.0) if total_mod_dls > 0 else 0.0
    )

    fig = go.Figure(
        go.Bar(
            x=agg["Project version"],
            y=agg["Downloads"],
            marker=dict(
                color=COLOR_CYAN,
                line=dict(color="#0F172A", width=1),
            ),
            text=[f"{v:,.0f}" for v in agg["Downloads"]],
            textposition="outside",
            textfont=dict(color=TEXT_COLOR, size=11),
            customdata=agg["Percentage"],
            hovertemplate="<b>v%{x}</b><br>Downloads: %{y:,.0f}<br>Share: %{customdata:.1f}%<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(
            text=f"<b>Version Adoption (Top Releases): {project_name}</b>",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.01,
            y=0.96,
        ),
        template="plotly_dark",
        paper_bgcolor=BG_TRANSPARENT,
        plot_bgcolor=BG_PLOT,
        font=dict(family="Inter, system-ui, sans-serif", color=TEXT_COLOR),
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis=dict(
            title="Project Release Version",
            showgrid=False,
            zeroline=False,
            type="category",
        ),
        yaxis=dict(
            title="Downloads",
            showgrid=True,
            gridcolor=GRID_COLOR,
            zeroline=False,
        ),
        showlegend=False,
        height=380,
    )
    return fig


def render_world_choropleth_map(
    country_df: pd.DataFrame, metric: str = "Downloads", use_log: bool = False
) -> go.Figure:
    """Render global choropleth map of creator audience across verified countries.

    Args:
        country_df: DataFrame with 'Country' and metric columns ('Downloads', 'Playtime (seconds)').
        metric: Metric string to display ('Downloads' or 'Playtime (Hours)').
        use_log: Whether to use a logarithmic scale for color mapping.

    Returns:
        Plotly Figure with natural earth choropleth projection.
    """
    if country_df.empty or "Country" not in country_df.columns:
        return _empty_figure("No geographic country telemetry available")

    # Exclude 'Other' unresolved launcher pulls to render clean sovereign boundaries
    sub = country_df[country_df["Country"] != "Other"].copy()
    if sub.empty:
        return _empty_figure("No resolved country telemetry available")

    if metric == "Playtime (Hours)":
        if "Playtime (Hours)" not in sub.columns:
            if "Playtime (seconds)" in sub.columns:
                sub["Playtime (Hours)"] = sub["Playtime (seconds)"] / 3600.0
            else:
                sub["Playtime (Hours)"] = 0.0
        val_col = "Playtime (Hours)"
        unit = "Hours"
    else:
        if "Downloads" not in sub.columns:
            sub["Downloads"] = 0
        val_col = "Downloads"
        unit = "DLs"

    agg = sub.groupby("Country", as_index=False)[val_col].sum()

    if use_log:
        z_vals = np.log10(np.clip(agg[val_col], a_min=0, a_max=None) + 1.0)
        colorbar_title = f"Log10({unit})"
    else:
        z_vals = agg[val_col]
        colorbar_title = unit

    hover_texts = [
        (
            f"<b>{c}</b><br>{metric}: {v:,.1f} {unit}"
            if metric == "Playtime (Hours)"
            else f"<b>{c}</b><br>{metric}: {int(v):,} {unit}"
        )
        for c, v in zip(agg["Country"], agg[val_col])
    ]

    fig = go.Figure(
        go.Choropleth(
            locations=agg["Country"],
            locationmode="country names",
            z=z_vals,
            text=hover_texts,
            hoverinfo="text",
            colorscale=[
                [0.0, "#1E1B4B"],
                [0.2, "#312E81"],
                [0.4, "#4C1D95"],
                [0.6, "#7C3AED"],
                [0.8, "#8B5CF6"],
                [1.0, "#06B6D4"],
            ],
            marker_line_color="#334155",
            marker_line_width=0.6,
            colorbar=dict(
                title=dict(
                    text=colorbar_title,
                    font=dict(color=TEXT_COLOR, size=11),
                ),
                tickfont=dict(color=TEXT_MUTED, size=10),
                len=0.75,
                bgcolor="rgba(15, 23, 42, 0.75)",
                bordercolor=GRID_COLOR,
                borderwidth=1,
            ),
        )
    )

    fig.update_layout(
        title=dict(
            text=f"<b>Global Creator Audience Distribution ({metric})</b>",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.01,
            y=0.96,
        ),
        template="plotly_dark",
        paper_bgcolor=BG_TRANSPARENT,
        plot_bgcolor=BG_TRANSPARENT,
        font=dict(family="Inter, system-ui, sans-serif", color=TEXT_COLOR),
        margin=dict(l=0, r=0, t=50, b=0),
        geo=dict(
            bgcolor=BG_TRANSPARENT,
            lakecolor="#0F172A",
            landcolor="#1E293B",
            oceancolor="#0F172A",
            showocean=True,
            showlakes=True,
            projection_type="natural earth",
            showcoastlines=True,
            coastlinewidth=0.5,
            coastlinecolor="#334155",
            showframe=False,
        ),
        height=500,
    )
    return fig


def render_top_countries_bar_chart(
    country_df: pd.DataFrame, metric: str = "Downloads"
) -> go.Figure:
    """Render horizontal bar chart of top countries by the chosen metric.

    Args:
        country_df: DataFrame with 'Country' and metric columns.
        metric: Metric string ('Downloads' or 'Playtime (Hours)').

    Returns:
        Plotly Figure showing top nations ranked with value labels.
    """
    if country_df.empty or "Country" not in country_df.columns:
        return _empty_figure("No country breakdown telemetry available")

    sub = country_df[country_df["Country"] != "Other"].copy()
    if sub.empty:
        return _empty_figure("No resolved country telemetry available")

    if metric == "Playtime (Hours)":
        if "Playtime (Hours)" not in sub.columns:
            if "Playtime (seconds)" in sub.columns:
                sub["Playtime (Hours)"] = sub["Playtime (seconds)"] / 3600.0
            else:
                sub["Playtime (Hours)"] = 0.0
        val_col = "Playtime (Hours)"
        fmt = lambda v: f"{v:,.1f}h"
    else:
        if "Downloads" not in sub.columns:
            sub["Downloads"] = 0
        val_col = "Downloads"
        fmt = lambda v: f"{int(v):,}"

    agg = (
        sub.groupby("Country", as_index=False)[val_col]
        .sum()
        .sort_values(val_col, ascending=False)
        .head(10)
    )

    plot_df = agg.sort_values(val_col, ascending=True).reset_index(drop=True)

    fig = go.Figure(
        go.Bar(
            x=plot_df[val_col],
            y=plot_df["Country"],
            orientation="h",
            marker=dict(
                color=COLOR_CYAN,
                line=dict(color="#0F172A", width=1),
            ),
            text=[fmt(v) for v in plot_df[val_col]],
            textposition="outside",
            textfont=dict(color=TEXT_COLOR, size=11),
            hovertemplate=f"<b>%{{y}}</b><br>{metric}: %{{x:,.1f}}<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(
            text=f"<b>Top Countries by {metric}</b>",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.01,
            y=0.96,
        ),
        template="plotly_dark",
        paper_bgcolor=BG_TRANSPARENT,
        plot_bgcolor=BG_PLOT,
        font=dict(family="Inter, system-ui, sans-serif", color=TEXT_COLOR),
        margin=dict(l=40, r=60, t=60, b=40),
        xaxis=dict(
            title=metric,
            showgrid=True,
            gridcolor=GRID_COLOR,
            zeroline=False,
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
        ),
        showlegend=False,
        height=max(380, len(plot_df) * 36),
    )
    return fig

