"""Static charts for the README / report (matplotlib). All titles say 'pathways'."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .benchmark import control_limits, overdispersed_limits

INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
BLUE, ORANGE, GREY = "#2a78d6", "#eb6834", "#b9b8b2"

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 10, "axes.edgecolor": MUTED,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.titlecolor": INK,
    "axes.titlesize": 12, "axes.titleweight": "bold", "figure.facecolor": "white",
})


def funnel(prov: pd.DataFrame, rate_col: str, p: float, limits: dict, tau2: dict | None,
           title: str, path, min_n: int = 1000, label_top: int = 0):
    fig, ax = plt.subplots(figsize=(9, 6.6), dpi=150)
    n = prov["n"].to_numpy()
    y = prov[rate_col].to_numpy()
    xs = np.logspace(np.log10(n.min() * 0.9), np.log10(n.max() * 1.1), 300)
    z998 = limits["99.8%"]
    lo998, hi998 = control_limits(p, xs, z998)
    lo95, hi95 = control_limits(p, xs, limits["95%"])
    ax.plot(xs, lo95 * 100, color=MUTED, lw=1, ls=":", label="95% binomial limits")
    ax.plot(xs, hi95 * 100, color=MUTED, lw=1, ls=":")
    ax.plot(xs, lo998 * 100, color=MUTED, lw=1.5, ls="--", label="99.8% binomial limits")
    ax.plot(xs, hi998 * 100, color=MUTED, lw=1.5, ls="--")
    if tau2 is not None:
        # tau2: {sector: tau^2}; each provider is judged against its own sector's limits
        olo, ohi = overdispersed_limits(p, xs, z998, tau2["NHS trust"])
        ax.plot(xs, olo * 100, color=INK, lw=2, label="99.8% limits, overdispersed (NHS trusts)")
        ax.plot(xs, ohi * 100, color=INK, lw=2)
        t_i = prov["sector"].map(tau2).to_numpy()
        lo_i, hi_i = overdispersed_limits(p, n, z998, t_i)
    else:
        lo_i, hi_i = control_limits(p, n, z998)
    above, below = y > hi_i, y < lo_i
    inside = ~(above | below)
    trust = (prov["sector"] == "NHS trust").to_numpy()
    for mask, colr, lab in [(inside, GREY, "inside limits"), (above, BLUE, "above 99.8% limit"),
                            (below, ORANGE, "below 99.8% limit")]:
        ax.scatter(n[mask & trust], y[mask & trust] * 100, s=34, c=colr, edgecolor="white", lw=0.8,
                   marker="o", label=f"NHS trust, {lab} ({(mask & trust).sum()})", zorder=3)
        ax.scatter(n[mask & ~trust], y[mask & ~trust] * 100, s=38, c=colr, edgecolor="white", lw=0.8,
                   marker="^", label=f"Independent/other, {lab} ({(mask & ~trust).sum()})", zorder=3)
    ax.axhline(p * 100, color=INK2, lw=1)
    ax.text(n.max() * 1.12, p * 100, f" England {p*100:.1f}%", va="center", color=INK2, fontsize=9)
    ax.set_xscale("log")
    ax.set_xlabel("Waiting list size (incomplete RTT pathways, log scale)")
    ax.set_ylabel("% of pathways waiting under 18 weeks")
    ax.set_title(title, loc="left")
    ax.grid(True, color=GRID, lw=0.6)
    ax.set_ylim(max(0, y.min() * 100 - 3), y.max() * 100 + 3)
    if label_top:
        far = prov.assign(_d=np.abs(y - p) / np.sqrt(p * (1 - p) / n))
        for _, r in far.nlargest(label_top, "_d").iterrows():
            ax.annotate(short(r["provider_name"]), (r["n"], r[rate_col] * 100), fontsize=7,
                        color=INK2, xytext=(4, 2), textcoords="offset points")
    ax.legend(fontsize=7, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3)
    fig.text(0.01, 0.01, "Source: NHS England RTT full CSV, Sept 2026. Counts are pathways, not patients. "
             f"Providers with ≥{min_n:,} pathways.\nOverdispersion is estimated within each sector; "
             "independent providers are judged against their own (much wider) limits, not drawn.", fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def short(name: str) -> str:
    import string
    s = string.capwords(name.lower())
    s = s.replace("Nhs", "NHS").replace(" And ", " and ").replace(" Of ", " of ").replace(" The ", " the ").replace(" NHS Foundation Trust", "").replace(" NHS Trust", "")
    return s.replace("University Hospitals", "UH").replace("Hospitals", "Hosp.").replace("Hospital", "Hosp.")


def slope(rs: pd.DataFrame, title: str, path):
    fig, ax = plt.subplots(figsize=(8, 7.5), dpi=150)
    k = len(rs)
    for _, r in rs.iterrows():
        moved = r["raw_rank"] != r["adj_rank"]
        col = BLUE if r["shift"] > 0 else ORANGE if r["shift"] < 0 else GREY
        ax.plot([0, 1], [r["raw_rank"], r["adj_rank"]], color=col, lw=2.2 if moved else 1.2, zorder=2)
        ax.scatter([0, 1], [r["raw_rank"], r["adj_rank"]], color=col, s=30, zorder=3, edgecolor="white")
        ax.text(-0.04, r["raw_rank"], f"{short(r['provider_name'])}  {r['raw_rate']*100:.1f}%",
                ha="right", va="center", fontsize=7.5, color=INK if moved else INK2)
        ax.text(1.04, r["adj_rank"], f"{r['adj_rate']*100:.1f}%  {short(r['provider_name'])}",
                ha="left", va="center", fontsize=7.5, color=INK if moved else INK2)
    ax.set_xlim(-1.3, 2.3)
    ax.set_ylim(k + 0.8, 0.2)
    ax.set_xticks([0, 1], ["Raw rank\n(% under 18 weeks)", "Specialty-adjusted rank\n(indirectly standardised)"])
    ax.set_yticks([])
    for s in ("left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="x", length=0)
    ax.set_title(title, loc="left")
    fig.text(0.01, 0.01, "Blue = moves up after adjustment, orange = moves down, grey = unchanged. "
             "Rates are % of incomplete pathways under 18 weeks.", fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def specialty_bars(spec_tab: pd.DataFrame, path):
    d = spec_tab.sort_values("pct_within_18")
    fig, ax = plt.subplots(figsize=(8, 7), dpi=150)
    ax.barh(d["tf_name"].str.replace(r" Service$", "", regex=True), d["pct_within_18"], color=BLUE, height=0.7)
    for i, (v, n) in enumerate(zip(d["pct_within_18"], d["pathways"])):
        ax.text(v + 0.5, i, f"{v:.1f}%  ({n/1000:,.0f}k)", va="center", fontsize=7.5, color=INK2)
    ax.set_xlim(0, 100)
    ax.set_xlabel("% of incomplete pathways under 18 weeks (list size in brackets)")
    ax.set_title("Specialty mix matters: % of pathways under 18 weeks by specialty, Sept 2026", loc="left", fontsize=11)
    ax.grid(axis="x", color=GRID, lw=0.6)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def oe_vs_expected(prov: pd.DataFrame, p: float, path):
    """How much the specialty mix alone shifts each provider's expected rate."""
    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    trust = prov["sector"] == "NHS trust"
    ax.scatter(prov.loc[trust, "expected_rate"] * 100, prov.loc[trust, "raw_rate"] * 100, c=BLUE, s=26,
               edgecolor="white", label="NHS trust")
    ax.scatter(prov.loc[~trust, "expected_rate"] * 100, prov.loc[~trust, "raw_rate"] * 100, c=ORANGE, s=30,
               marker="^", edgecolor="white", label="Independent sector / other")
    lim = [40, 100]
    ax.plot(lim, lim, color=MUTED, ls="--", lw=1, label="observed = expected")
    ax.set_xlabel("Expected % under 18 weeks given specialty mix")
    ax.set_ylabel("Observed % under 18 weeks")
    ax.set_title("Observed vs mix-expected performance, by provider (pathways)", loc="left", fontsize=11)
    ax.grid(True, color=GRID, lw=0.6)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def movers(allt: pd.DataFrame, path, top: int = 16):
    """Dumbbell: raw rank -> adjusted rank for the NHS trusts that move most."""
    d = allt.reindex(allt["shift"].abs().sort_values(ascending=False).index).head(top)
    d = d.sort_values("shift")
    N = len(allt)
    fig, ax = plt.subplots(figsize=(9, 6.5), dpi=150)
    for i, (_, r) in enumerate(d.iterrows()):
        col = BLUE if r["shift"] > 0 else ORANGE
        ax.annotate("", xy=(r["adj_rank"], i), xytext=(r["raw_rank"], i),
                    arrowprops=dict(arrowstyle="-|>", color=col, lw=2, mutation_scale=12))
        ax.scatter([r["raw_rank"]], [i], color=GREY, s=30, zorder=3, edgecolor="white")
        ax.text(min(r["raw_rank"], r["adj_rank"]) - 3, i,
                f"{'+' if r['shift'] > 0 else ''}{int(r['shift'])}  ({r['raw_rate']*100:.0f}% → adj. {r['adj_rate']*100:.0f}%)",
                va="center", ha="left", fontsize=7.5, color=INK2)
    ax.set_yticks(range(len(d)), [short(x) for x in d["provider_name"]], fontsize=8)
    ax.set_xlim(N + 1, -45)
    ax.set_xticks([t for t in range(0, N + 1, 20)])
    ax.set_xlabel(f"Rank among {N} NHS trusts (1 = highest % of pathways under 18 weeks)\ngrey dot = raw rank, arrowhead = specialty-adjusted rank")
    ax.set_title("Trusts that move most after specialty-mix adjustment (pathways)", loc="left", fontsize=11)
    ax.grid(axis="x", color=GRID, lw=0.6)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
