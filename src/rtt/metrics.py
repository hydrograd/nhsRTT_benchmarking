"""Waiting-list metrics computed from weekly wait bands.

All counts are referral-to-treatment *pathways*, not patients.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .load import week_cols

WITHIN_18_MAX_LOWER = 17   # bands 0-1 ... 17-18 weeks are "within 18 weeks"
LONG_WAIT_THRESHOLDS = (52, 65, 78, 104)


def band_counts(df: pd.DataFrame) -> np.ndarray:
    """Sum the 105 week bands over all rows of df -> array of length 105."""
    return df[week_cols(df)].to_numpy().sum(axis=0)


def pct_within_18(counts: np.ndarray) -> float:
    total = counts.sum()
    return 100 * counts[: WITHIN_18_MAX_LOWER + 1].sum() / total if total else np.nan


def over_weeks(counts: np.ndarray, weeks: int) -> int:
    """Pathways waiting more than `weeks` weeks (bands with lower bound >= weeks)."""
    return int(counts[weeks:].sum())


def percentile_weeks(counts: np.ndarray, q: float) -> float:
    """Wait at quantile q (0-1), linearly interpolated within the weekly band.

    Band k covers (k, k+1] weeks. This is the NHS England method for the published
    median and 92nd-percentile waits.
    """
    counts = np.asarray(counts, dtype=float)
    total = counts.sum()
    if total == 0:
        return np.nan
    target = q * total
    cum = np.cumsum(counts)
    k = int(np.searchsorted(cum, target, side="left"))
    before = cum[k - 1] if k > 0 else 0.0
    return k + (target - before) / counts[k]


def summary(counts: np.ndarray) -> dict:
    out = {
        "pathways": int(counts.sum()),
        "pct_within_18": pct_within_18(counts),
        "median_weeks": percentile_weeks(counts, 0.5),
        "p92_weeks": percentile_weeks(counts, 0.92),
    }
    for t in LONG_WAIT_THRESHOLDS:
        out[f"over_{t}"] = over_weeks(counts, t)
    return out


def waiting_list(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["part"] == "Part_2"]


def national_summary(c999: pd.DataFrame) -> dict:
    """National Part_2 headline figures from the C_999 total rows."""
    return summary(band_counts(waiting_list(c999)))


def grouped_summary(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Summary metrics per group (e.g. specialty or provider) from Part_2 rows."""
    wl = waiting_list(df)
    wc = week_cols(wl)
    g = wl.groupby(by)[wc].sum()
    rows = [dict(zip(by if len(by) > 1 else by, k if isinstance(k, tuple) else (k,))) | summary(v)
            for k, v in zip(g.index, g.to_numpy())]
    return pd.DataFrame(rows)


def part_totals(c999: pd.DataFrame) -> pd.Series:
    """Total All by RTT part, from C_999 rows (no double counting)."""
    return c999.groupby("part")["total_all"].sum()
