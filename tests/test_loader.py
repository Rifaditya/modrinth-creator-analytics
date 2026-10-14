"""Unit and integration tests for Modrinth data loader and normalization."""

from pathlib import Path
import pytest
import pandas as pd

from src.loader import (
    PRETRACKING_END_DATE,
    ModrinthDataBundle,
    get_proportional_game_version_breakdown,
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


def test_supported_game_versions_preserved(bundle: ModrinthDataBundle):
    """Verify Supported Game Versions column exists and contains lists of versions for catalog items."""
    pv = bundle.project_version
    assert "Supported Game Versions" in pv.columns, "Missing 'Supported Game Versions' column"

    # Known catalog single-version item
    row_single = pv[pv["Project version"] == "1.0.50+1.21.11"]
    assert not row_single.empty
    assert row_single["Supported Game Versions"].iloc[0] == ["1.21.11"]

    # Known catalog multi-version item (1.8.38)
    row_multi = pv[pv["Project version"] == "1.8.38"]
    assert not row_multi.empty
    gvs = row_multi["Supported Game Versions"].iloc[0]
    assert isinstance(gvs, list)
    assert len(gvs) > 1
    assert "26.2" in gvs
    assert "26.3" in gvs


def test_multiversion_classification_not_snapshot(bundle: ModrinthDataBundle):
    """Verify 1.8.38 and multi-version jars are not collapsed to snapshot-1, but categorized as multi-version."""
    pv = bundle.project_version

    row_1838 = pv[pv["Project version"] == "1.8.38"]
    assert not row_1838.empty
    target_1838 = row_1838["Target Game Version"].iloc[0]
    assert target_1838 != "26.1-snapshot-1", "1.8.38 must not collapse to snapshot-1"
    assert target_1838 == "26.x Multi-Version"

    # Verify multi-version jars with 26.x are labeled with 26.x Multi-Version
    multi_26 = pv[pv["Target Game Version"] == "26.x Multi-Version"]
    assert not multi_26.empty
    assert multi_26["Downloads"].sum() > 0


def test_proportional_game_version_breakdown(bundle: ModrinthDataBundle):
    """Verify proportional allocation returns 100% of total downloads (100,226) without dropping rows."""
    prop_df = get_proportional_game_version_breakdown(
        bundle.project_version, bundle.game_version
    )

    expected_cols = ["Game version", "Downloads", "Playtime (seconds)"]
    assert list(prop_df.columns) == expected_cols, f"Columns mismatch: {list(prop_df.columns)}"

    total_dls = prop_df["Downloads"].sum()
    assert round(total_dls) == 100226, f"Expected 100,226 downloads, got {total_dls}"
    assert abs(total_dls - 100226) < 1e-4

    # Verify key versions are represented
    versions = set(prop_df["Game version"])
    assert "26.2" in versions
    assert "26.1.2" in versions
    assert "26.3" in versions
    assert "1.21.11" in versions


def test_1nazhfKH_alias_containment(bundle: ModrinthDataBundle):
    """Verify 1nazhfKH maps to Better Dogs with multi-version support."""
    pv = bundle.project_version
    row = pv[pv["Project version"] == "1nazhfKH"]
    assert not row.empty, "1nazhfKH not found in project_version table"

    record = row.iloc[0]
    assert record["Project"] == "VO: Better Dogs"
    assert record["Target Game Version"] == "Universal / Multi-Version"
    assert record["Supported Game Versions"] == ["26.1.2", "26.2"]


def test_is_pretracking_column(bundle: ModrinthDataBundle):
    """Verify April dates have Is Pretracking == True and May+ have False."""
    for table_name, df in bundle.as_dict().items():
        if "Date" in df.columns:
            assert "Is Pretracking" in df.columns, f"Missing 'Is Pretracking' in {table_name}"
            # Check April dates (pre-tracking)
            apr_mask = df["Date"] <= PRETRACKING_END_DATE
            if apr_mask.any():
                assert df.loc[apr_mask, "Is Pretracking"].all(), f"April rows not True in {table_name}"
            # Check May+ dates (post-tracking)
            may_mask = df["Date"] > PRETRACKING_END_DATE
            if may_mask.any():
                assert not df.loc[may_mask, "Is Pretracking"].any(), f"May+ rows not False in {table_name}"


def test_263_and_build_manual_aliases(bundle: ModrinthDataBundle):
    """Verify 26.3 hashes and build.x hashes are mapped accurately via manual aliases."""
    pv = bundle.project_version

    # Assert 1.0.2+26.3 maps to IG: Combat Cooldown Adjuster on 26.3
    row_cca = pv[pv["Project version"] == "1.0.2+26.3"]
    assert not row_cca.empty, "1.0.2+26.3 not found in project_version table"
    assert (row_cca["Project"] == "IG: Combat Cooldown Adjuster").all()
    assert (row_cca["Target Game Version"] == "26.3").all()

    # Assert 5NKdFCi1, dertltvr, gq5ErCd3, iV88z6NB, and b9Fhgcka map to 26.3
    hashes_263 = ["5NKdFCi1", "dertltvr", "gq5ErCd3", "iV88z6NB", "b9Fhgcka"]
    for h in hashes_263:
        row = pv[pv["Project version"] == h]
        assert not row.empty, f"Hash {h} not found in project_version table"
        assert (row["Target Game Version"] == "26.3").all(), f"Hash {h} does not map to 26.3"

    # Assert 1.0.0+build.1 and 1.0.0+build.5 map to Collapsible gamerules screen on 26.1.2
    for b_ver in ["1.0.0+build.1", "1.0.0+build.5"]:
        row = pv[pv["Project version"] == b_ver]
        assert not row.empty, f"{b_ver} not found in project_version table"
        assert (row["Project"] == "Collapsible gamerules screen").all()
        assert (row["Target Game Version"] == "26.1.2").all()

    # Assert no rows in bundle.project_version["Target Game Version"] contain 'build.1' or 'build.5'
    assert not pv["Target Game Version"].astype(str).str.contains(r"build\.1|build\.5").any(), (
        "Target Game Version contains 'build.1' or 'build.5'"
    )


