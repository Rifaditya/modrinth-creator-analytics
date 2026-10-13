"""Unit and integration tests for Modrinth data loader and normalization."""

from pathlib import Path
import pytest
import pandas as pd

from src.loader import (
    ModrinthDataBundle,
    identify_table_name,
    load_all_data,
    normalize_dataframe,
)


@pytest.fixture(scope="module")
def bundle() -> ModrinthDataBundle:
    """Fixture providing loaded Modrinth analytics bundle."""
    return load_all_data()


def test_bundle_contains_all_10_tables(bundle: ModrinthDataBundle):
    """Verify all 10 expected Modrinth analytics tables are present and non-empty."""
    expected_tables = [
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

    bundle_dict = bundle.as_dict()
    assert set(bundle_dict.keys()) == set(expected_tables), "Bundle table keys mismatch"

    for table_name in expected_tables:
        df = bundle_dict[table_name]
        assert isinstance(df, pd.DataFrame), f"{table_name} is not a DataFrame"
        assert not df.empty, f"{table_name} DataFrame is unexpectedly empty"
        assert len(df) > 0, f"{table_name} has 0 rows"


def test_total_revenue_parity(bundle: ModrinthDataBundle):
    """Verify total revenue matches expected figure of ~29.40 across project and member tables."""
    project_rev = bundle.project["Revenue"].sum()
    member_rev = bundle.member["Revenue"].sum()

    assert abs(project_rev - 29.40) < 0.05, f"Project revenue {project_rev} deviates from 29.40"
    assert abs(member_rev - 29.40) < 0.05, f"Member revenue {member_rev} deviates from 29.40"
    assert abs(project_rev - member_rev) < 1e-4, "Discrepancy between project and member revenue"


def test_total_downloads(bundle: ModrinthDataBundle):
    """Verify total downloads across project breakdown matches 100,226."""
    total_proj_dls = bundle.project["Downloads"].sum()
    assert total_proj_dls == 100226, f"Expected 100,226 downloads, found {total_proj_dls}"


def test_project_version_enrichment(bundle: ModrinthDataBundle):
    """Verify project_version is enriched with Project and Target Game Version."""
    pv = bundle.project_version

    assert "Project" in pv.columns, "Missing 'Project' column in project_version"
    assert "Target Game Version" in pv.columns, "Missing 'Target Game Version' column in project_version"

    total_pv_dls = pv["Downloads"].sum()
    assert total_pv_dls == 100226, f"Expected project_version total downloads 100,226, got {total_pv_dls}"

    mapped_df = pv[pv["Project"] != "Unknown"]
    mapped_dls = mapped_df["Downloads"].sum()
    mapping_ratio = mapped_dls / total_pv_dls

    # Must exceed 97% threshold (>99% actual)
    assert mapping_ratio > 0.97, f"Mapping ratio {mapping_ratio:.4f} is below 97% requirement"


def test_date_column_normalization(bundle: ModrinthDataBundle):
    """Verify Date column is converted to datetime across relevant tables."""
    for name, df in bundle.as_dict().items():
        if "Date" in df.columns:
            assert pd.api.types.is_datetime64_any_dtype(df["Date"]), f"{name}['Date'] is not datetime"
            assert not df["Date"].isna().all(), f"{name}['Date'] has all NaT values"


def test_identify_table_name():
    """Verify filename pattern recognition for all table types."""
    cases = {
        "Modrinth Analytics Country Breakdown - Apr 16, 2026 to Oct 13, 2026.csv": "country",
        "country.csv": "country",
        "dependent_project.csv": "dependent_project",
        "Modrinth Analytics Download reason Breakdown.csv": "download_reason",
        "Modrinth Analytics Download source Breakdown.csv": "download_source",
        "game_version.csv": "game_version",
        "loader.csv": "loader",
        "member.csv": "member",
        "monetization.csv": "monetization",
        "Modrinth Analytics Project Breakdown.csv": "project",
        "Modrinth Analytics Project version Breakdown.csv": "project_version",
    }
    for filename, expected in cases.items():
        assert identify_table_name(filename) == expected, f"Failed identifying {filename}"


def test_dict_access_on_bundle(bundle: ModrinthDataBundle):
    """Verify dictionary-like indexing on bundle."""
    assert bundle["project"] is bundle.project
    with pytest.raises(KeyError):
        _ = bundle["non_existent_table"]
