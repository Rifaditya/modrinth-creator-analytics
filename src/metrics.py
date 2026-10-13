"""Metrics calculation, filtering, and forecasting engine for Modrinth analytics.

Provides KPI computation (revenue, downloads, playtime, blended and monetized RPM),
date-range filtering across all 10 normalized analytics tables, and milestone earnings
forecasting based on empirical monetization conversion rates.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Union
import pandas as pd

from src.loader import ModrinthDataBundle


def calculate_kpis(bundle: ModrinthDataBundle) -> Dict[str, Any]:
    """Calculate key performance indicators across the Modrinth data bundle.

    Args:
        bundle: The normalized ModrinthDataBundle containing all analytics tables.

    Returns:
        Dictionary containing aggregate metrics:
            - total_revenue: Total earnings in USD ($)
            - total_downloads: Total mod downloads
            - total_views: Total project page views
            - total_playtime_seconds: Cumulative playtime in seconds
            - total_playtime_hours: Cumulative playtime in hours
            - total_playtime_days: Cumulative playtime in days
            - blended_rpm: Revenue per 1,000 total downloads
            - monetized_downloads: Count of downloads generating ad impressions
            - unmonetized_downloads: Count of unmonetized / launcher / adblocked downloads
            - monetization_rate: Percentage of downloads that are monetized (%)
            - monetized_rpm: Revenue per 1,000 monetized downloads
            - avg_playtime_per_download_min: Average playtime per download in minutes
    """
    # Revenue: member table has exact creator payout, project table has project-level revenue
    if not bundle.member.empty and "Revenue" in bundle.member.columns:
        total_revenue = float(bundle.member["Revenue"].sum())
    elif not bundle.project.empty and "Revenue" in bundle.project.columns:
        total_revenue = float(bundle.project["Revenue"].sum())
    else:
        total_revenue = 0.0

    # Project-level aggregates
    if not bundle.project.empty and "Downloads" in bundle.project.columns:
        total_downloads = int(bundle.project["Downloads"].sum())
    else:
        total_downloads = 0

    if not bundle.project.empty and "Views" in bundle.project.columns:
        total_views = int(bundle.project["Views"].sum())
    else:
        total_views = 0

    if not bundle.project.empty and "Playtime (seconds)" in bundle.project.columns:
        total_playtime_seconds = int(bundle.project["Playtime (seconds)"].sum())
    else:
        total_playtime_seconds = 0

    total_playtime_hours = total_playtime_seconds / 3600.0
    total_playtime_days = total_playtime_seconds / 86400.0

    # Monetization breakdowns
    if not bundle.monetization.empty and "Monetization" in bundle.monetization.columns:
        m_df = bundle.monetization
        monetized_mask = m_df["Monetization"] == "Monetized"
        unmonetized_mask = m_df["Monetization"] == "Unmonetized"

        monetized_downloads = int(m_df.loc[monetized_mask, "Downloads"].sum())
        unmonetized_downloads = int(m_df.loc[unmonetized_mask, "Downloads"].sum())
    else:
        monetized_downloads = 0
        unmonetized_downloads = total_downloads

    # Rate and RPM derivations
    blended_rpm = (
        (total_revenue / total_downloads * 1000.0) if total_downloads > 0 else 0.0
    )
    monetization_rate = (
        (monetized_downloads / total_downloads * 100.0) if total_downloads > 0 else 0.0
    )
    monetized_rpm = (
        (total_revenue / monetized_downloads * 1000.0)
        if monetized_downloads > 0
        else 0.0
    )
    avg_playtime_per_download_min = (
        (total_playtime_seconds / total_downloads / 60.0)
        if total_downloads > 0
        else 0.0
    )

    return {
        "total_revenue": total_revenue,
        "total_downloads": total_downloads,
        "total_views": total_views,
        "total_playtime_seconds": total_playtime_seconds,
        "total_playtime_hours": total_playtime_hours,
        "total_playtime_days": total_playtime_days,
        "blended_rpm": blended_rpm,
        "monetized_downloads": monetized_downloads,
        "unmonetized_downloads": unmonetized_downloads,
        "monetization_rate": monetization_rate,
        "monetized_rpm": monetized_rpm,
        "avg_playtime_per_download_min": avg_playtime_per_download_min,
    }


def filter_bundle_by_date(
    bundle: ModrinthDataBundle,
    start_date: Optional[Union[str, pd.Timestamp, Any]] = None,
    end_date: Optional[Union[str, pd.Timestamp, Any]] = None,
) -> ModrinthDataBundle:
    """Filter all tables containing a 'Date' column between start_date and end_date.

    Args:
        bundle: Input ModrinthDataBundle.
        start_date: Inclusive lower bound (string, date, or Timestamp). If None, unbounded below.
        end_date: Inclusive upper bound (string, date, or Timestamp). If None, unbounded above.

    Returns:
        A new ModrinthDataBundle instance containing the sliced dataframes.
    """
    start_ts = pd.to_datetime(start_date) if start_date is not None else None
    end_ts = pd.to_datetime(end_date) if end_date is not None else None

    filtered_tables: Dict[str, pd.DataFrame] = {}

    for name, df in bundle.as_dict().items():
        if "Date" in df.columns:
            mask = pd.Series(True, index=df.index)
            if start_ts is not None:
                mask &= df["Date"] >= start_ts
            if end_ts is not None:
                mask &= df["Date"] <= end_ts
            filtered_tables[name] = df[mask].copy().reset_index(drop=True)
        else:
            filtered_tables[name] = df.copy()

    return ModrinthDataBundle(**filtered_tables)


def project_milestone_earnings(
    target_downloads: int,
    blended_rpm: float,
    monetized_rpm: float,
    monetization_rate: float,
) -> Dict[str, float]:
    """Compute projected earnings for a given milestone download target.

    Args:
        target_downloads: Milestone target total downloads (e.g. 500,000).
        blended_rpm: Effective blended revenue per 1,000 total downloads.
        monetized_rpm: Revenue per 1,000 monetized impression downloads.
        monetization_rate: Proportion of downloads generating monetized impressions (%).

    Returns:
        Dictionary containing projected metrics:
            - target_downloads: float representation of the target downloads
            - projected_blended_earnings: Projected USD revenue using blended RPM
            - projected_monetized_downloads: Estimated monetized downloads count
            - projected_monetized_earnings: Projected USD revenue using monetized RPM
    """
    target_dl_float = float(target_downloads)
    projected_blended_earnings = (target_dl_float / 1000.0) * blended_rpm
    projected_monetized_downloads = target_dl_float * (monetization_rate / 100.0)
    projected_monetized_earnings = (
        (projected_monetized_downloads / 1000.0) * monetized_rpm
    )

    return {
        "target_downloads": target_dl_float,
        "projected_blended_earnings": projected_blended_earnings,
        "projected_monetized_downloads": projected_monetized_downloads,
        "projected_monetized_earnings": projected_monetized_earnings,
    }
