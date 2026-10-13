"""Data loader and normalization engine for Modrinth Creator Analytics.

Loads 10 raw CSV breakdown exports from Modrinth analytics, cleans column types,
parses dates, and enriches version breakdown data with project metadata and
target Minecraft versions from the version catalog.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)

# Streamlit caching wrapper with graceful fallback for headless/script runs
try:
    import streamlit as st
    cache_data_decorator = st.cache_data
except Exception:
    st = None

    def cache_data_decorator(*dargs, **dkwargs):
        def wrapper(func):
            return func
        if len(dargs) == 1 and callable(dargs[0]) and not dkwargs:
            return dargs[0]
        return wrapper


# Manual alias overrides for historical/unresolved hashes
MANUAL_VERSION_ALIASES: Dict[str, Dict[str, str]] = {
    "1nazhfKH": {
        "project_title": "VO: Better Dogs",
        "target_game_version": "26.2",
    }
}


@dataclass
class ModrinthDataBundle:
    """Container holding all 10 normalized Modrinth analytics dataframes."""

    country: pd.DataFrame
    dependent_project: pd.DataFrame
    download_reason: pd.DataFrame
    download_source: pd.DataFrame
    game_version: pd.DataFrame
    loader: pd.DataFrame
    member: pd.DataFrame
    monetization: pd.DataFrame
    project: pd.DataFrame
    project_version: pd.DataFrame

    def as_dict(self) -> Dict[str, pd.DataFrame]:
        """Return bundle as dictionary of table name to dataframe."""
        return {
            "country": self.country,
            "dependent_project": self.dependent_project,
            "download_reason": self.download_reason,
            "download_source": self.download_source,
            "game_version": self.game_version,
            "loader": self.loader,
            "member": self.member,
            "monetization": self.monetization,
            "project": self.project,
            "project_version": self.project_version,
        }

    def __getitem__(self, key: str) -> pd.DataFrame:
        """Allow dict-like access to dataframes."""
        d = self.as_dict()
        if key in d:
            return d[key]
        raise KeyError(f"Unknown table '{key}'. Valid tables: {list(d.keys())}")


def identify_table_name(filename: str) -> Optional[str]:
    """Map CSV file name or uploaded file name to its canonical table key."""
    name = Path(filename).name.lower()
    if "project version" in name or "project_version" in name:
        return "project_version"
    elif "dependent project" in name or "dependent_project" in name:
        return "dependent_project"
    elif "download reason" in name or "download_reason" in name:
        return "download_reason"
    elif "download source" in name or "download_source" in name:
        return "download_source"
    elif "game version" in name or "game_version" in name:
        return "game_version"
    elif "country" in name:
        return "country"
    elif "loader" in name:
        return "loader"
    elif "member" in name:
        return "member"
    elif "monetization" in name:
        return "monetization"
    elif "project" in name:
        return "project"
    return None


def normalize_dataframe(df: pd.DataFrame, default_year: int = 2026) -> pd.DataFrame:
    """Normalize dates and numeric columns in a raw Modrinth dataframe."""
    df = df.copy()

    # Parse and normalize Date column
    if "Date" in df.columns:
        s = df["Date"]
        if not pd.api.types.is_datetime64_any_dtype(s):
            s_str = s.astype(str).str.strip()
            # If string contains 4-digit year, parse directly
            has_year = s_str.str.contains(r"\b(?:19\d\d|20\d\d)\b", regex=True)
            dates = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")

            missing_year = ~has_year
            if missing_year.any():
                dates.loc[missing_year] = pd.to_datetime(
                    s_str.loc[missing_year] + f" {default_year}",
                    format="%b %d %Y",
                    errors="coerce",
                )
            if has_year.any():
                dates.loc[has_year] = pd.to_datetime(
                    s_str.loc[has_year],
                    format="mixed",
                    errors="coerce",
                )
            df["Date"] = dates

    # Standardize numeric columns
    if "Downloads" in df.columns:
        df["Downloads"] = (
            pd.to_numeric(
                df["Downloads"].astype(str).str.replace(",", ""), errors="coerce"
            )
            .fillna(0)
            .astype("int64")
        )

    if "Views" in df.columns:
        df["Views"] = (
            pd.to_numeric(
                df["Views"].astype(str).str.replace(",", ""), errors="coerce"
            )
            .fillna(0)
            .astype("int64")
        )

    if "Revenue" in df.columns:
        df["Revenue"] = (
            pd.to_numeric(
                df["Revenue"].astype(str).str.replace(",", ""), errors="coerce"
            )
            .fillna(0.0)
            .astype("float64")
        )

    if "Playtime (seconds)" in df.columns:
        df["Playtime (seconds)"] = (
            pd.to_numeric(
                df["Playtime (seconds)"].astype(str).str.replace(",", ""),
                errors="coerce",
            )
            .fillna(0)
            .astype("int64")
        )

    return df


def load_version_catalog(
    catalog_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Load the Modrinth version catalog JSON if present."""
    candidate_paths: List[Path] = []
    if catalog_path is not None:
        candidate_paths.append(Path(catalog_path))

    # Standard locations relative to project root or data folder
    base_dir = Path(__file__).resolve().parent.parent
    candidate_paths.extend([
        base_dir / "data" / "modrinth_version_catalog.json",
        Path("data/modrinth_version_catalog.json"),
        Path("../data/modrinth_version_catalog.json"),
    ])

    for p in candidate_paths:
        if p.exists() and p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read catalog at {p}: {e}")

    logger.warning("Modrinth version catalog JSON not found. Operating with fallback aliases only.")
    return {}


def enrich_project_version(
    df: pd.DataFrame, catalog: Dict[str, Any]
) -> pd.DataFrame:
    """Enrich project_version dataframe with Project and Target Game Version."""
    df = df.copy()
    if "Project version" not in df.columns:
        return df

    projects: List[str] = []
    game_versions: List[str] = []

    for val in df["Project version"]:
        val_str = str(val).strip()
        if val_str in MANUAL_VERSION_ALIASES:
            entry = MANUAL_VERSION_ALIASES[val_str]
            projects.append(entry.get("project_title", "Unknown"))
            game_versions.append(entry.get("target_game_version", "Unknown"))
        elif val_str in catalog:
            entry = catalog[val_str]
            projects.append(entry.get("project_title", "Unknown"))
            gv = entry.get("primary_game_version")
            if not gv and entry.get("game_versions"):
                gv = entry["game_versions"][0]
            game_versions.append(gv or "Unknown")
        else:
            projects.append("Unknown")
            # Extract target game version heuristic from tag if present (+26.3, -26.1.2)
            if "+" in val_str:
                suffix = val_str.split("+")[-1]
                game_versions.append(
                    suffix if any(c.isdigit() for c in suffix) else "Unknown"
                )
            elif "-" in val_str and any(c.isdigit() for c in val_str.split("-")[-1]):
                game_versions.append(val_str.split("-")[-1])
            else:
                game_versions.append("Unknown")

    df["Project"] = projects
    df["Target Game Version"] = game_versions
    return df


def _read_data_frames(
    data_dir: Optional[Union[str, Path]] = None,
    uploaded_files: Optional[List[Any]] = None,
    catalog_path: Optional[Union[str, Path]] = None,
) -> ModrinthDataBundle:
    """Internal reader loading and normalizing the 10 dataframes."""
    raw_dfs: Dict[str, pd.DataFrame] = {}

    if uploaded_files:
        for file_obj in uploaded_files:
            file_name = getattr(file_obj, "name", str(file_obj))
            table_name = identify_table_name(file_name)
            if table_name:
                raw_dfs[table_name] = pd.read_csv(file_obj)
    else:
        if data_dir is None:
            data_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
        else:
            data_dir = Path(data_dir)

        if not data_dir.exists():
            raise FileNotFoundError(f"Data directory does not exist: {data_dir}")

        for csv_file in data_dir.glob("*.csv"):
            table_name = identify_table_name(csv_file.name)
            if table_name:
                raw_dfs[table_name] = pd.read_csv(csv_file)

    required_tables = [
        "country",
        "dependent_project",
        "download_reason",
        "download_source",
        "game_version",
        "loader",
        "member",
        "monetization",
        "project",
        "project_version",
    ]

    missing = [t for t in required_tables if t not in raw_dfs]
    if missing:
        raise ValueError(f"Missing required Modrinth breakdown tables: {missing}")

    # Load catalog
    catalog = load_version_catalog(catalog_path)

    # Normalize all dataframes
    normalized: Dict[str, pd.DataFrame] = {}
    for name, df in raw_dfs.items():
        clean_df = normalize_dataframe(df)
        if name == "project_version":
            clean_df = enrich_project_version(clean_df, catalog)
        normalized[name] = clean_df

    return ModrinthDataBundle(
        country=normalized["country"],
        dependent_project=normalized["dependent_project"],
        download_reason=normalized["download_reason"],
        download_source=normalized["download_source"],
        game_version=normalized["game_version"],
        loader=normalized["loader"],
        member=normalized["member"],
        monetization=normalized["monetization"],
        project=normalized["project"],
        project_version=normalized["project_version"],
    )


@cache_data_decorator
def load_all_data(
    data_dir: Optional[Union[str, Path]] = None,
    uploaded_files: Optional[List[Any]] = None,
    catalog_path: Optional[Union[str, Path]] = None,
) -> ModrinthDataBundle:
    """Load and normalize all 10 Modrinth analytics CSV exports.

    Args:
        data_dir: Directory containing raw CSV exports. Defaults to
            `data/raw` relative to project root.
        uploaded_files: Optional list of UploadedFile objects from Streamlit.
        catalog_path: Optional explicit path to modrinth_version_catalog.json.

    Returns:
        ModrinthDataBundle with all 10 normalized and enriched DataFrames.
    """
    return _read_data_frames(
        data_dir=data_dir,
        uploaded_files=uploaded_files,
        catalog_path=catalog_path,
    )
