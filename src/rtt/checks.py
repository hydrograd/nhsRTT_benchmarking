"""Data-integrity and reconciliation checks. Each returns a DataFrame of violations (empty = pass)."""
from __future__ import annotations

import pandas as pd

from .load import week_cols

KEY = ["provider_code", "commissioner_code", "part"]


def c999_equals_specialty_sum(spec: pd.DataFrame, c999: pd.DataFrame) -> pd.DataFrame:
    cols = week_cols(spec) + ["total_all"]
    s = spec.groupby(KEY)[cols].sum()
    t = c999.groupby(KEY)[cols].sum()
    s, t = s.align(t, fill_value=0)
    diff = (s - t).abs().sum(axis=1)
    return diff[diff != 0].reset_index(name="abs_diff")


def bands_sum_to_total_all(df: pd.DataFrame, part: str = "Part_2") -> pd.DataFrame:
    d = df[df["part"] == part]
    bad = d[d[week_cols(d)].sum(axis=1) != d["total_all"]]
    return bad[KEY + ["tf_code", "total_all"]]


def completed_total_plus_unknown(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df["part"].isin(["Part_1A", "Part_1B"])]
    bad = d[d["total"].fillna(0) + d["unknown_clock_start"] != d["total_all"]]
    return bad[KEY + ["tf_code", "total", "unknown_clock_start", "total_all"]]


def part2a_le_part2(c999: pd.DataFrame) -> pd.DataFrame:
    p = c999.pivot_table(index="provider_code", columns="part", values="total_all", aggfunc="sum", fill_value=0)
    bad = p[p.get("Part_2A", 0) > p.get("Part_2", 0)]
    return bad.reset_index()


def negatives(df: pd.DataFrame) -> pd.DataFrame:
    cols = week_cols(df) + ["unknown_clock_start", "total_all"]
    return df[(df[cols] < 0).any(axis=1)]


def single_period(df: pd.DataFrame) -> bool:
    return df["period"].nunique() == 1


def reconciliation_table(c999: pd.DataFrame, national: dict, published: dict) -> pd.DataFrame:
    part = c999.groupby("part")["total_all"].sum()
    rows = [
        ("Incomplete pathways (Part_2)", part["Part_2"], published["incomplete_pathways"]),
        ("% within 18 weeks", round(national["pct_within_18"], 2), published["pct_within_18"]),
        ("Median wait (weeks)", round(national["median_weeks"], 2), published["median_weeks"]),
        ("92nd percentile wait (weeks)", round(national["p92_weeks"], 2), published["p92_weeks"]),
        ("Completed admitted (Part_1A)", part["Part_1A"], published["completed_admitted"]),
        ("Completed non-admitted (Part_1B)", part["Part_1B"], published["completed_non_admitted"]),
        ("New RTT periods (Part_3)", part["Part_3"], published["new_periods"]),
    ]
    t = pd.DataFrame(rows, columns=["measure", "this_file", "published"])
    t["gap"] = t["this_file"] - t["published"]
    t["gap_pct"] = 100 * t["gap"] / t["published"]
    return t
