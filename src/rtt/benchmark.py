"""Provider benchmarking: funnel-plot control limits and indirect standardisation."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .load import week_cols
from .metrics import WITHIN_18_MAX_LOWER


def _within18(df: pd.DataFrame) -> pd.Series:
    wc = week_cols(df)
    return df[wc[: WITHIN_18_MAX_LOWER + 1]].sum(axis=1)


def specialty_cells(spec: pd.DataFrame) -> pd.DataFrame:
    """Part_2 provider x specialty cells (commissioner rows aggregated): n and observed within-18."""
    wl = spec[spec["part"] == "Part_2"].copy()
    wl["n"] = wl[week_cols(wl)].sum(axis=1)
    wl["obs18"] = _within18(wl)
    return (
        wl.groupby(["provider_code", "provider_name", "sector", "tf_code", "tf_name"], as_index=False)[["n", "obs18"]]
        .sum()
    )


def national_specialty_rates(cells: pd.DataFrame) -> pd.DataFrame:
    s = cells.groupby(["tf_code", "tf_name"], as_index=False)[["n", "obs18"]].sum()
    s["p_s"] = s["obs18"] / s["n"]
    return s


def indirect_standardisation(cells: pd.DataFrame) -> pd.DataFrame:
    """Per provider: observed, expected (sum n_js * p_s), O/E and the adjusted rate.

    Adjusted rate = (O/E) * national rate, the conventional indirectly standardised rate.
    """
    rates = national_specialty_rates(cells)[["tf_code", "p_s"]]
    c = cells.merge(rates, on="tf_code", validate="many_to_one")
    c["exp18"] = c["n"] * c["p_s"]
    p = c.groupby(["provider_code", "provider_name", "sector"], as_index=False)[["n", "obs18", "exp18"]].sum()
    national = cells["obs18"].sum() / cells["n"].sum()
    p["raw_rate"] = p["obs18"] / p["n"]
    p["oe"] = p["obs18"] / p["exp18"]
    p["adj_rate"] = p["oe"] * national
    p["expected_rate"] = p["exp18"] / p["n"]
    p.attrs["national_rate"] = national
    return p


def control_limits(p: float, n, z: float):
    """Binomial (normal-approximation) funnel limits p +/- z*sqrt(p(1-p)/n)."""
    n = np.asarray(n, dtype=float)
    se = np.sqrt(p * (1 - p) / n)
    return np.clip(p - z * se, 0, 1), np.clip(p + z * se, 0, 1)


def classify(rate: pd.Series, n: pd.Series, p: float, limits: dict[str, float]) -> pd.Series:
    """Label each provider by the widest control limit it falls outside."""
    out = pd.Series("within 95%", index=rate.index)
    for label, z in sorted(limits.items(), key=lambda kv: kv[1]):
        lo, hi = control_limits(p, n, z)
        out[rate > hi] = f"above {label}"
        out[rate < lo] = f"below {label}"
    return out


def benchmark(spec: pd.DataFrame, min_list_size: int, limits: dict[str, float]) -> pd.DataFrame:
    cells = specialty_cells(spec)
    prov = indirect_standardisation(cells)
    p = prov.attrs["national_rate"]
    prov = prov[prov["n"] >= min_list_size].copy()
    prov["raw_flag"] = classify(prov["raw_rate"], prov["n"], p, limits)
    prov["adj_flag"] = classify(prov["adj_rate"], prov["n"], p, limits)
    prov["n_specialties"] = cells[cells["n"] > 0].groupby("provider_code").size().reindex(prov["provider_code"]).to_numpy()
    prov.attrs["national_rate"] = p
    return prov.sort_values("n", ascending=False).reset_index(drop=True)


def rank_shift(prov: pd.DataFrame, top_n: int = 20, sector: str = "NHS trust") -> pd.DataFrame:
    """Raw vs adjusted rank among the top_n largest providers in a sector (1 = best)."""
    t = prov[prov["sector"] == sector].nlargest(top_n, "n").copy()
    t["raw_rank"] = t["raw_rate"].rank(ascending=False, method="min").astype(int)
    t["adj_rank"] = t["adj_rate"].rank(ascending=False, method="min").astype(int)
    t["shift"] = t["raw_rank"] - t["adj_rank"]  # positive = moves up once mix is adjusted
    return t.sort_values("adj_rank").reset_index(drop=True)


def overdispersion_tau2(rate: pd.Series, n: pd.Series, p: float, winsor: float = 0.10) -> float:
    """Additive random-effects variance (Spiegelhalter 2005, Stat Med 24:1185).

    With list sizes in the tens of thousands, binomial limits are so narrow that
    almost every provider falls outside them. tau^2 estimates the genuine
    between-provider variance beyond chance; limits become p +/- z*sqrt(s_i^2 + tau^2).
    z-scores are winsorised at 10%/90% so extreme providers do not inflate tau^2.
    """
    n = np.asarray(n, dtype=float)
    y = np.asarray(rate, dtype=float)
    s2 = p * (1 - p) / n
    z = (y - p) / np.sqrt(s2)
    lo, hi = np.quantile(z, [winsor, 1 - winsor])
    zw = np.clip(z, lo, hi)
    k = len(z)
    phi = np.mean(zw**2)
    w = 1 / s2
    tau2 = (k * phi - (k - 1)) / (w.sum() - (w**2).sum() / w.sum())
    return float(max(tau2, 0.0))


def overdispersed_limits(p: float, n, z: float, tau2: float):
    n = np.asarray(n, dtype=float)
    se = np.sqrt(p * (1 - p) / n + tau2)
    return np.clip(p - z * se, 0, 1), np.clip(p + z * se, 0, 1)


def classify_od(rate: pd.Series, n: pd.Series, p: float, limits: dict[str, float], tau2: float) -> pd.Series:
    out = pd.Series("within 95%", index=rate.index)
    for label, z in sorted(limits.items(), key=lambda kv: kv[1]):
        lo, hi = overdispersed_limits(p, n, z, tau2)
        out[rate > hi] = f"above {label}"
        out[rate < lo] = f"below {label}"
    return out


def add_overdispersion(prov: pd.DataFrame, limits: dict[str, float]) -> pd.DataFrame:
    """Overdispersion-adjusted flags, with tau^2 estimated *within each sector*.

    NHS trusts and independent-sector providers are separate peer groups: the
    independent sector is far more heterogeneous, and pooling would inflate tau^2
    and hide genuine NHS-trust outliers. tau^2 is estimated separately for raw and
    adjusted rates. attrs['tau2'] = {(sector, 'raw'|'adj'): tau^2}.
    """
    p = prov.attrs["national_rate"]
    prov = prov.copy()
    prov["raw_flag_od"] = ""
    prov["adj_flag_od"] = ""
    tau = {}
    for sector, idx in prov.groupby("sector").groups.items():
        d = prov.loc[idx]
        for kind in ("raw", "adj"):
            t = overdispersion_tau2(d[f"{kind}_rate"], d["n"], p)
            tau[(sector, kind)] = t
            prov.loc[idx, f"{kind}_flag_od"] = classify_od(d[f"{kind}_rate"], d["n"], p, limits, t)
    prov.attrs.update(national_rate=p, tau2=tau)
    return prov
