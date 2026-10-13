"""Chart generation module for Modrinth Creator Analytics.

Renders dark-themed, responsive Plotly figures adhering to the studio's Komikku
purple/cyan/emerald visual design standard.
"""

from __future__ import annotations

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
