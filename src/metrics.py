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


def calculate_source_kpis(
    source_df: pd.DataFrame, reason_df: pd.DataFrame
) -> Dict[str, Any]:
    """Calculate key acquisition source and distribution reason indicators.

    Args:
        source_df: DataFrame with 'Download source' and 'Downloads' columns.
        reason_df: DataFrame with 'Download reason' and 'Downloads' columns.

    Returns:
        Dictionary containing key metrics:
            - total_source_downloads: Total downloads from sources table
            - modrinth_app_downloads: Total downloads via Modrinth App
            - modrinth_app_pct: Percentage of downloads via Modrinth App
            - modrinth_website_downloads: Total downloads via Modrinth Website
            - modrinth_website_pct: Percentage of downloads via Modrinth Website
            - prism_launcher_downloads: Total downloads via Prism Launcher
            - prism_launcher_pct: Percentage of downloads via Prism Launcher
            - native_channels_downloads: Total native downloads (App + Website)
            - native_channels_pct: Percentage of native channels (App + Website)
            - total_reason_downloads: Total downloads in reason table
            - ecosystem_downloads: Total ecosystem downloads (Modpack + Dependency)
            - ecosystem_pct: Percentage of ecosystem downloads (Modpack + Dependency)
            - modpack_downloads: Downloads attributed to modpacks
            - dependency_downloads: Downloads attributed to mod dependencies
    """
    total_src = (
        int(source_df["Downloads"].sum())
        if not source_df.empty and "Downloads" in source_df.columns
        else 0
    )
    if total_src > 0 and "Download source" in source_df.columns:
        s_agg = source_df.groupby("Download source")["Downloads"].sum().to_dict()
    else:
        s_agg = {}

    ma = int(s_agg.get("Modrinth App", 0))
    mw = int(s_agg.get("Modrinth Website", 0))
    pl = int(s_agg.get("Prism Launcher", 0))
    native_dls = ma + mw

    total_reason = (
        int(reason_df["Downloads"].sum())
        if not reason_df.empty and "Downloads" in reason_df.columns
        else 0
    )
    if total_reason > 0 and "Download reason" in reason_df.columns:
        r_agg = reason_df.groupby("Download reason")["Downloads"].sum().to_dict()
    else:
        r_agg = {}

    mp = int(r_agg.get("Modpack", 0))
    dep = int(r_agg.get("Dependency", 0))
    eco_dls = mp + dep

    return {
        "total_source_downloads": total_src,
        "modrinth_app_downloads": ma,
        "modrinth_app_pct": (ma / total_src * 100.0) if total_src > 0 else 0.0,
        "modrinth_website_downloads": mw,
        "modrinth_website_pct": (mw / total_src * 100.0) if total_src > 0 else 0.0,
        "prism_launcher_downloads": pl,
        "prism_launcher_pct": (pl / total_src * 100.0) if total_src > 0 else 0.0,
        "native_channels_downloads": native_dls,
        "native_channels_pct": (native_dls / total_src * 100.0) if total_src > 0 else 0.0,
        "total_reason_downloads": total_reason,
        "ecosystem_downloads": eco_dls,
        "ecosystem_pct": (eco_dls / total_reason * 100.0) if total_reason > 0 else 0.0,
        "modpack_downloads": mp,
        "dependency_downloads": dep,
    }


def calculate_version_kpis(
    game_version_df: pd.DataFrame,
    project_version_df: Optional[pd.DataFrame] = None,
    use_enriched: bool = True,
) -> Dict[str, Any]:
    """Calculate Minecraft version demographics and generational anchor metrics.

    Args:
        game_version_df: Raw game_version DataFrame.
        project_version_df: Optional enriched project_version DataFrame.
        use_enriched: Whether to prioritize enriched project version data over raw telemetry.

    Returns:
        Dictionary containing key metrics:
            - total_version_downloads: Total downloads analyzed
            - lead_version: Name of sovereign lead anchor ("Minecraft 26.2")
            - lead_downloads: Cumulative downloads on 26.2
            - lead_pct: Share of 26.2 downloads
            - modern_26x_downloads: Total downloads on 26.x anchors
            - modern_26x_pct: Share of 26.x downloads
            - legacy_downloads: Total downloads on 1.21.x and 1.20.1 anchors
            - legacy_pct: Share of legacy LTS anchors
            - unknown_downloads: Total unresolved downloads
            - unknown_pct: Share of unresolved downloads
    """
    if (
        use_enriched
        and project_version_df is not None
        and not project_version_df.empty
        and "Target Game Version" in project_version_df.columns
        and "Downloads" in project_version_df.columns
    ):
        df = project_version_df
        col = "Target Game Version"
    elif (
        not game_version_df.empty
        and "Game version" in game_version_df.columns
        and "Downloads" in game_version_df.columns
    ):
        df = game_version_df
        col = "Game version"
    else:
        return {
            "total_version_downloads": 0,
            "lead_version": "Minecraft 26.2",
            "lead_downloads": 0,
            "lead_pct": 0.0,
            "modern_26x_downloads": 0,
            "modern_26x_pct": 0.0,
            "legacy_downloads": 0,
            "legacy_pct": 0.0,
            "unknown_downloads": 0,
            "unknown_pct": 0.0,
        }

    total_dls = int(df["Downloads"].sum())
    if total_dls == 0:
        return {
            "total_version_downloads": 0,
            "lead_version": "Minecraft 26.2",
            "lead_downloads": 0,
            "lead_pct": 0.0,
            "modern_26x_downloads": 0,
            "modern_26x_pct": 0.0,
            "legacy_downloads": 0,
            "legacy_pct": 0.0,
            "unknown_downloads": 0,
            "unknown_pct": 0.0,
        }

    agg = df.groupby(col)["Downloads"].sum().to_dict()
    lead_dls = int(agg.get("26.2", 0))
    modern_26x = sum(int(v) for k, v in agg.items() if str(k).startswith("26."))
    legacy = sum(
        int(v)
        for k, v in agg.items()
        if str(k).startswith("1.21") or str(k).startswith("1.20")
    )
    unknown = sum(int(v) for k, v in agg.items() if "unknown" in str(k).lower())

    return {
        "total_version_downloads": total_dls,
        "lead_version": "Minecraft 26.2",
        "lead_downloads": lead_dls,
        "lead_pct": (lead_dls / total_dls * 100.0) if total_dls > 0 else 0.0,
        "modern_26x_downloads": modern_26x,
        "modern_26x_pct": (modern_26x / total_dls * 100.0) if total_dls > 0 else 0.0,
        "legacy_downloads": legacy,
        "legacy_pct": (legacy / total_dls * 100.0) if total_dls > 0 else 0.0,
        "unknown_downloads": unknown,
        "unknown_pct": (unknown / total_dls * 100.0) if total_dls > 0 else 0.0,
    }
