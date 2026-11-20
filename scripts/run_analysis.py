"""Run the full analysis: build Parquet, checks, metrics, benchmarking, tables and charts."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rtt import benchmark as bm, checks, load, metrics, plots  # noqa: E402


def main():
    cfg = load.load_config()
    paths = load.build()
    spec = pd.read_parquet(paths["specialty_wide"])
    c999 = pd.read_parquet(paths["c999_wide"])
    out = Path(cfg["outputs_dir"])
    (out / "tables").mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(parents=True, exist_ok=True)

    # national
    nat = metrics.national_summary(c999)
    recon = checks.reconciliation_table(c999, nat, cfg["published"])
    recon.to_csv(out / "tables/reconciliation.csv", index=False)
    unknown = c999[c999.part.isin(["Part_1A", "Part_1B"])].groupby("part")["unknown_clock_start"].sum()

    # specialty profile (the standard)
    sp = metrics.grouped_summary(spec, ["tf_code", "tf_name"]).sort_values("pathways", ascending=False)
    sp["share_of_list_pct"] = 100 * sp["pathways"] / sp["pathways"].sum()
    sp.to_csv(out / "tables/specialty_profile.csv", index=False)

    # benchmarking
    lim = cfg["benchmark"]["limits"]
    prov = bm.benchmark(spec, cfg["benchmark"]["min_list_size"], lim)
    prov = bm.add_overdispersion(prov, lim)
    p = prov.attrs["national_rate"]
    prov.to_csv(out / "tables/provider_benchmark.csv", index=False)
    bm.specialty_cells(spec).to_csv(out / "tables/provider_specialty_cells.csv", index=False)
    rs = bm.rank_shift(prov, cfg["benchmark"]["top_n_slope"])
    rs.to_csv(out / "tables/rank_shift_top20.csv", index=False)

    # rank shift among all NHS trusts >= min size
    allt = bm.rank_shift(prov, top_n=10_000)
    plots.movers(allt, out / "figures/rank_shift_biggest_movers.png")
    # long waits (52+) by specialty and provider, from specialty rows
    wl = spec[spec.part == "Part_2"]
    o52 = wl[[f"w{k:03d}" for k in range(52, 105)]].sum(axis=1)
    lw_prov = wl.assign(o52=o52).groupby(["provider_code", "provider_name", "sector"], as_index=False)["o52"].sum()
    lw_prov = lw_prov.sort_values("o52", ascending=False)
    lw_prov["share_pct"] = 100 * lw_prov["o52"] / lw_prov["o52"].sum()
    lw_prov.head(25).to_csv(out / "tables/long_waits_52_top_providers.csv", index=False)
    lw_spec = sp[["tf_name", "over_52", "pathways"]].assign(share_pct=lambda d: 100 * d.over_52 / d.over_52.sum())
    lw_spec.sort_values("over_52", ascending=False).to_csv(out / "tables/long_waits_52_by_specialty.csv", index=False)

    # charts
    mn = cfg["benchmark"]["min_list_size"]
    plots.funnel(prov, "raw_rate", p, lim, {k[0]: v for k, v in prov.attrs["tau2"].items() if k[1] == "raw"},
                 "Raw funnel: % of RTT pathways under 18 weeks by provider, Sept 2026",
                 out / "figures/funnel_raw.png", min_n=mn)
    plots.funnel(prov, "adj_rate", p, lim, {k[0]: v for k, v in prov.attrs["tau2"].items() if k[1] == "adj"},
                 "Specialty-adjusted funnel: % of RTT pathways under 18 weeks, Sept 2026",
                 out / "figures/funnel_adjusted.png", min_n=mn)
    plots.slope(rs, "20 largest NHS trusts: raw vs specialty-adjusted rank (pathways)",
                out / "figures/rank_shift.png")
    plots.specialty_bars(sp, out / "figures/specialty_profile.png")
    plots.oe_vs_expected(prov, p, out / "figures/observed_vs_expected.png")

    def count(col, prefix):
        return int(prov[col].str.startswith(prefix).sum())

    raw_out_binom = count("raw_flag", "above 99.8%") + count("raw_flag", "below 99.8%")
    raw_out_od = count("raw_flag_od", "above 99.8%") + count("raw_flag_od", "below 99.8%")
    adj_out_od = count("adj_flag_od", "above 99.8%") + count("adj_flag_od", "below 99.8%")
    raw_out_od_in_adj = int((prov.raw_flag_od.str.contains("99.8") & ~prov.adj_flag_od.str.contains("99.8")).sum())
    adj_out_od_new = int((~prov.raw_flag_od.str.contains("99.8") & prov.adj_flag_od.str.contains("99.8")).sum())
    top10_share = float(lw_prov.head(10)["share_pct"].sum())

    summary = {
        "national": {k: (round(float(v), 3) if isinstance(v, float) else int(v)) for k, v in nat.items()},
        "part_totals": {k: int(v) for k, v in metrics.part_totals(c999).items()},
        "unknown_clock_start": {k: int(v) for k, v in unknown.items()},
        "providers_total": int(spec.provider_code.nunique()),
        "providers_benchmarked": len(prov),
        "benchmarked_by_sector": prov.sector.value_counts().to_dict(),
        "england_oe": float(prov.attrs["national_rate"] and
                            bm.indirect_standardisation(bm.specialty_cells(spec)).pipe(lambda d: d.obs18.sum() / d.exp18.sum())),
        "national_rate": p,
        "tau_sd_pp": {f"{k[0]}|{k[1]}": 100 * v ** 0.5 for k, v in prov.attrs["tau2"].items()},
        "od_flags_adj_by_sector": pd.crosstab(prov.sector, prov.adj_flag_od).to_dict(orient="index"),
        "od_flags_raw_by_sector": pd.crosstab(prov.sector, prov.raw_flag_od).to_dict(orient="index"),
        "outside_99.8_binomial_raw": raw_out_binom,
        "outside_99.8_od_raw": raw_out_od,
        "outside_99.8_od_adj": adj_out_od,
        "flagged_raw_od_but_inside_after_adjustment": raw_out_od_in_adj,
        "newly_flagged_after_adjustment": adj_out_od_new,
        "top20_max_abs_shift": int(rs["shift"].abs().max()),
        "top20_n_moved": int((rs["shift"] != 0).sum()),
        "all_trusts_n": len(allt),
        "all_trusts_moved_5plus": int((allt["shift"].abs() >= 5).sum()),
        "all_trusts_max_abs_shift": int(allt["shift"].abs().max()),
        "expected_rate_range_trusts": [float(prov[prov.sector == "NHS trust"].expected_rate.min()),
                                       float(prov[prov.sector == "NHS trust"].expected_rate.max())],
        "expected_rate_range_all": [float(prov.expected_rate.min()), float(prov.expected_rate.max())],
        "raw_rate_sd": float(prov.raw_rate.std()), "adj_rate_sd": float(prov.adj_rate.std()),
        "top10_share_52plus_pct": top10_share,
        "checks": {
            "c999_mismatches": len(checks.c999_equals_specialty_sum(spec, c999)),
            "bands_vs_total_all_mismatches": len(checks.bands_sum_to_total_all(pd.concat([spec, c999]))),
            "completed_total_unknown_mismatches": len(checks.completed_total_plus_unknown(pd.concat([spec, c999]))),
            "part2a_gt_part2": len(checks.part2a_le_part2(c999)),
            "negatives": len(checks.negatives(pd.concat([spec, c999]))),
            "single_period": checks.single_period(pd.concat([spec, c999])),
        },
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    allt.to_csv(out / "tables/rank_shift_all_trusts.csv", index=False)
    print(json.dumps(summary, indent=2, default=float))
    print(recon.to_string())


if __name__ == "__main__":
    main()
