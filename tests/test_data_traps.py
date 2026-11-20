"""One test per data trap / reconciliation check in the brief. Requires the raw extract."""
import pandas as pd
import pytest

from rtt import benchmark as bm, checks, metrics


def test_single_period(raw):
    assert checks.single_period(raw)


def test_shape(raw):
    assert raw.shape[0] == 183_346


def test_c999_equals_sum_of_specialties(spec, c999):
    assert checks.c999_equals_specialty_sum(spec, c999).empty


def test_part2_bands_sum_to_total_all(raw):
    assert checks.bands_sum_to_total_all(raw, "Part_2").empty


def test_part2_total_column_is_blank(raw):
    assert raw.loc[raw.part == "Part_2", "total"].isna().all()


def test_completed_total_plus_unknown_equals_total_all(raw):
    assert checks.completed_total_plus_unknown(raw).empty


def test_unknown_clock_starts_only_in_completed_parts(c999):
    u = c999.groupby("part")["unknown_clock_start"].sum()
    assert u["Part_1A"] == 86 and u["Part_1B"] == 830
    assert u[["Part_2", "Part_2A", "Part_3"]].sum() == 0


def test_part2a_le_part2_except_known(c999, cfg):
    bad = set(checks.part2a_le_part2(c999)["provider_code"])
    assert bad <= set(cfg["known_data_issues"]["part2a_exceeds_part2"])


def test_no_negative_counts(raw):
    assert checks.negatives(raw).empty


def test_never_sum_c999_and_specialty(raw, c999):
    # summing everything would double the list: guard the trap explicitly
    both = raw.loc[raw.part == "Part_2", "total_all"].sum()
    assert both == 2 * c999.loc[c999.part == "Part_2", "total_all"].sum()


def test_national_reproduces_published(c999, cfg):
    nat = metrics.national_summary(c999)
    pub = cfg["published"]
    assert nat["pathways"] == 7_104_965
    assert round(nat["pct_within_18"], 1) == pub["pct_within_18"]
    assert round(nat["median_weeks"], 1) == pub["median_weeks"]
    # 37.750 vs published 37.7: within 0.06 weeks; the published figure is from the
    # provider-based return (0.4% smaller list), so exact rounding is not expected.
    assert abs(nat["p92_weeks"] - pub["p92_weeks"]) < 0.06


def test_england_oe_equals_one(spec):
    p = bm.indirect_standardisation(bm.specialty_cells(spec))
    assert p["obs18"].sum() / p["exp18"].sum() == pytest.approx(1.0, abs=1e-12)


def test_specialty_cells_match_c999_list(spec, c999):
    cells = bm.specialty_cells(spec)
    assert cells["n"].sum() == c999.loc[c999.part == "Part_2", "total_all"].sum()
