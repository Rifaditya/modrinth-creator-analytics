"""Metrics calculation, filtering, and forecasting engine for Modrinth analytics.

Provides KPI computation (revenue, downloads, playtime, blended and monetized RPM),
date-range filtering across all 10 normalized analytics tables, and milestone earnings
forecasting based on empirical monetization conversion rates.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, Union
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


def calculate_project_summary(project_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate aggregated performance metrics across all studio projects.

    Args:
        project_df: DataFrame containing 'Project', 'Downloads', 'Views', 'Revenue',
            and 'Playtime (seconds)' columns.

    Returns:
        DataFrame aggregated by Project, sorted descending by Downloads:
            - Project: Project title string
            - Downloads: Total download count
            - Share %: Percentage of total downloads across all projects
            - Views: Total page views
            - Conversion Rate %: Downloads / Views * 100 (0 if Views == 0)
            - Revenue: Total USD earnings
            - Playtime (Hours): Cumulative playtime in hours
    """
    if project_df.empty or "Project" not in project_df.columns:
        return pd.DataFrame(
            columns=[
                "Project",
                "Downloads",
                "Share %",
                "Views",
                "Conversion Rate %",
                "Revenue",
                "Playtime (Hours)",
            ]
        )

    df = project_df.copy()
    for col in ["Downloads", "Views", "Revenue", "Playtime (seconds)"]:
        if col not in df.columns:
            df[col] = 0

    agg = (
        df.groupby("Project", as_index=False)
        .agg(
            {
                "Downloads": "sum",
                "Views": "sum",
                "Revenue": "sum",
                "Playtime (seconds)": "sum",
            }
        )
    )

    total_downloads = agg["Downloads"].sum()
    agg["Share %"] = (
        (agg["Downloads"] / total_downloads * 100.0) if total_downloads > 0 else 0.0
    )
    agg["Conversion Rate %"] = agg.apply(
        lambda r: (r["Downloads"] / r["Views"] * 100.0) if r["Views"] > 0 else 0.0,
        axis=1,
    )
    agg["Playtime (Hours)"] = agg["Playtime (seconds)"] / 3600.0

    summary_df = (
        agg[
            [
                "Project",
                "Downloads",
                "Share %",
                "Views",
                "Conversion Rate %",
                "Revenue",
                "Playtime (Hours)",
            ]
        ]
        .sort_values("Downloads", ascending=False)
        .reset_index(drop=True)
    )

    return summary_df


def calculate_country_summary(
    country_df: pd.DataFrame, total_bundle_downloads: Optional[int] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Calculate geographic telemetry metrics and country-by-country summary.

    Args:
        country_df: DataFrame containing 'Country', 'Downloads', 'Views', and
            'Playtime (seconds)'.
        total_bundle_downloads: Optional total downloads across all studio projects.
            If provided, percentage calculations are calibrated against studio total.

    Returns:
        Tuple containing:
            - country_summary_df: Aggregated DataFrame sorted descending by Downloads:
                - Country: Country name string
                - Downloads: Total download count
                - Views: Total page views
                - Playtime (seconds): Total playtime in seconds
                - Playtime (Hours): Cumulative playtime in hours
                - Share %: Percentage of downloads
            - country_kpis: Dictionary of summary indicators:
                - total_downloads: Reference total downloads (bundle or country table)
                - country_table_downloads: Sum of downloads in country table
                - other_downloads: Unresolved launcher IP downloads ('Other')
                - other_pct: Share of downloads from 'Other' (%)
                - identified_downloads: Downloads from resolved geographic countries
                - identified_pct: Share of downloads from resolved countries (%)
                - top_country: Country with highest resolved downloads
                - top_country_downloads: Downloads for top country
                - top_country_pct: Share of downloads for top country (%)
                - identified_countries_count: Count of identified non-'Other' countries
                - total_views: Total page views in country table
                - identified_views: Views from resolved countries
                - other_views: Views from 'Other'
    """
    if country_df.empty or "Country" not in country_df.columns:
        empty_df = pd.DataFrame(
            columns=[
                "Country",
                "Downloads",
                "Views",
                "Playtime (seconds)",
                "Playtime (Hours)",
                "Share %",
            ]
        )
        empty_kpis = {
            "total_downloads": 0,
            "country_table_downloads": 0,
            "other_downloads": 0,
            "other_pct": 0.0,
            "identified_downloads": 0,
            "identified_pct": 0.0,
            "top_country": "None",
            "top_country_downloads": 0,
            "top_country_pct": 0.0,
            "identified_countries_count": 0,
            "total_views": 0,
            "identified_views": 0,
            "other_views": 0,
        }
        return empty_df, empty_kpis

    df = country_df.copy()
    for col in ["Downloads", "Views", "Playtime (seconds)"]:
        if col not in df.columns:
            df[col] = 0

    agg = (
        df.groupby("Country", as_index=False)
        .agg(
            {
                "Downloads": "sum",
                "Views": "sum",
                "Playtime (seconds)": "sum",
            }
        )
    )
    agg["Playtime (Hours)"] = agg["Playtime (seconds)"] / 3600.0

    table_total_dls = int(agg["Downloads"].sum())
    ref_total_dls = (
        total_bundle_downloads
        if (total_bundle_downloads is not None and total_bundle_downloads > 0)
        else table_total_dls
    )

    agg["Share %"] = (
        (agg["Downloads"] / ref_total_dls * 100.0) if ref_total_dls > 0 else 0.0
    )

    summary_df = agg.sort_values("Downloads", ascending=False).reset_index(drop=True)

    other_mask = summary_df["Country"] == "Other"
    other_row = summary_df[other_mask]
    other_dls = int(other_row["Downloads"].iloc[0]) if not other_row.empty else 0
    other_views = int(other_row["Views"].iloc[0]) if not other_row.empty else 0

    non_other_df = summary_df[~other_mask]
    total_views = int(summary_df["Views"].sum())
    identified_views = int(non_other_df["Views"].sum())

    if total_bundle_downloads is not None and total_bundle_downloads > 0:
        identified_dls = total_bundle_downloads - other_dls
    else:
        identified_dls = int(non_other_df["Downloads"].sum())

    if not non_other_df.empty:
        top_country_name = str(non_other_df.iloc[0]["Country"])
        top_country_dls = int(non_other_df.iloc[0]["Downloads"])
    else:
        top_country_name = "None"
        top_country_dls = 0

    other_pct = (other_dls / ref_total_dls * 100.0) if ref_total_dls > 0 else 0.0
    identified_pct = (
        (identified_dls / ref_total_dls * 100.0) if ref_total_dls > 0 else 0.0
    )
    top_country_pct = (
        (top_country_dls / ref_total_dls * 100.0) if ref_total_dls > 0 else 0.0
    )

    kpis = {
        "total_downloads": ref_total_dls,
        "country_table_downloads": table_total_dls,
        "other_downloads": other_dls,
        "other_pct": other_pct,
        "identified_downloads": identified_dls,
        "identified_pct": identified_pct,
        "top_country": top_country_name,
        "top_country_downloads": top_country_dls,
        "top_country_pct": top_country_pct,
        "identified_countries_count": len(non_other_df),
        "total_views": total_views,
        "identified_views": identified_views,
        "other_views": other_views,
    }

    return summary_df, kpis

