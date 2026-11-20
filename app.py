"""Provider Records System: a records-database view of RTT provider benchmarking.

Run:  streamlit run app.py   (after python scripts/run_analysis.py)
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))
from rtt import benchmark as bm  # noqa: E402
from rtt.load import load_config  # noqa: E402

st.set_page_config(page_title="RTT Provider Records", page_icon="🗂️", layout="wide",
                   initial_sidebar_state="expanded")
cfg = load_config(ROOT / "config.yaml")

# ---------------------------------------------------------------- palette
INK, INK2, MUTED, RULE = "#1a2733", "#4b5b68", "#8796a2", "#dfe4e8"
TEAL, TEAL_D = "#0e6b7a", "#0a4f5b"
HI, LO, NEUTRAL = "#2a78d6", "#d9541e", "#9aa6af"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
html, body, [class*="css"], .stMarkdown, .stText, button, input, select {{ font-family: 'IBM Plex Sans', sans-serif; }}
code, .mono {{ font-family: 'IBM Plex Mono', monospace !important; }}
header[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1280px; }}
section[data-testid="stSidebar"] {{ background: #0f1f2b; }}
section[data-testid="stSidebar"] * {{ color: #d6dee4; }}
section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div,
section[data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"] > div,
section[data-testid="stSidebar"] .stTextInput input {{ background: #182c3a; border-color: #2a4152; }}
section[data-testid="stSidebar"] div[data-baseweb="select"] span {{ color: #eef3f6; }}

/* system bar */
.sysbar {{ display:flex; justify-content:space-between; align-items:center; background:{TEAL_D};
  color:#e6f1f3; padding:10px 18px; border-radius:6px; margin-bottom:14px; font-size:12.5px; }}
.sysbar .brand {{ font-weight:600; letter-spacing:.04em; font-size:13.5px; }}
.sysbar .brand span {{ opacity:.65; font-weight:400; margin-left:8px; }}
.sysbar .meta {{ font-family:'IBM Plex Mono', monospace; opacity:.85; }}
.sysbar .dot {{ display:inline-block; width:7px; height:7px; border-radius:50%; background:#5fd3a5; margin-right:6px; }}

/* record card */
.record {{ background:#fff; border:1px solid {RULE}; border-left:5px solid {TEAL}; border-radius:6px;
  padding:18px 22px 16px; margin-bottom:14px; }}
.record .kicker {{ font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:{MUTED}; font-weight:600; }}
.record h1 {{ font-size:24px; line-height:1.25; margin:4px 0 14px; color:{INK}; font-weight:600; padding:0; }}
.fields {{ display:grid; grid-template-columns: repeat(6, minmax(0,1fr)); gap:10px 18px;
  border-top:1px dashed {RULE}; padding-top:12px; }}
.field .k {{ font-size:10.5px; letter-spacing:.08em; text-transform:uppercase; color:{MUTED}; }}
.field .v {{ font-size:14px; color:{INK}; font-weight:500; margin-top:2px; }}
.field .v.mono {{ font-family:'IBM Plex Mono', monospace; }}
@media (max-width: 900px) {{ .fields {{ grid-template-columns: repeat(2, minmax(0,1fr)); }} }}

/* status flags */
.flags {{ display:flex; gap:8px; flex-wrap:wrap; margin-top:12px; }}
.flag {{ display:inline-flex; align-items:center; gap:6px; font-size:12px; font-weight:500; padding:4px 10px;
  border-radius:4px; border:1px solid; background:#fff; }}
.flag .lbl {{ color:{MUTED}; font-weight:400; }}
.flag.hi {{ color:{HI}; border-color:{HI}55; background:{HI}0f; }}
.flag.lo {{ color:{LO}; border-color:{LO}55; background:{LO}0f; }}
.flag.ok {{ color:{INK2}; border-color:{RULE}; background:#f7f9fa; }}

/* observation cards */
.obs {{ display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:12px; margin-bottom:6px; }}
@media (max-width: 900px) {{ .obs {{ grid-template-columns: repeat(2, minmax(0,1fr)); }} }}
.ob {{ background:#fff; border:1px solid {RULE}; border-radius:6px; padding:12px 14px; }}
.ob .k {{ font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:{MUTED}; }}
.ob .v {{ font-size:26px; font-weight:600; color:{INK}; margin:2px 0 0; font-variant-numeric: tabular-nums; }}
.ob .s {{ font-size:12px; color:{INK2}; font-family:'IBM Plex Mono', monospace; }}
.ob .s.up {{ color:{HI}; }} .ob .s.down {{ color:{LO}; }}

/* tabs */
.stTabs [data-baseweb="tab-list"] {{ gap:2px; border-bottom:1px solid {RULE}; }}
.stTabs [data-baseweb="tab"] {{ background:#e9edf0; border-radius:5px 5px 0 0; padding:8px 16px; font-size:13px; }}
.stTabs [aria-selected="true"] {{ background:#fff; color:{TEAL} !important; font-weight:600; }}
.stTabs [data-baseweb="tab-panel"] {{ background:#fff; border:1px solid {RULE}; border-top:none;
  border-radius:0 0 6px 6px; padding:16px 18px; }}

.note {{ font-size:12px; color:{INK2}; background:#f7f9fa; border:1px solid {RULE}; border-radius:5px; padding:10px 12px; }}
.sb-h {{ font-size:10.5px; letter-spacing:.14em; text-transform:uppercase; color:#7f95a5 !important; font-weight:600; margin:14px 0 6px; }}
.sb-row {{ display:flex; justify-content:space-between; font-size:12.5px; padding:4px 0; border-bottom:1px solid #1d3242; }}
.sb-row b {{ font-family:'IBM Plex Mono', monospace; font-weight:500; color:#eef3f6 !important; }}
.foot {{ font-size:11px; color:{MUTED}; margin-top:18px; border-top:1px solid {RULE}; padding-top:10px; }}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- data
@st.cache_data
def data():
    prov = pd.read_csv(ROOT / "outputs/tables/provider_benchmark.csv")
    # small committed table (provider x specialty), so the app deploys without the 83 MB extract
    cells = pd.read_csv(ROOT / "outputs/tables/provider_specialty_cells.csv")
    rates = bm.national_specialty_rates(cells)[["tf_code", "p_s"]]
    cells = cells.merge(rates, on="tf_code")
    for col in ("raw_rate", "adj_rate"):
        prov[f"{col}_rank"] = prov.groupby("sector")[col].rank(ascending=False, method="min").astype(int)
    prov["peer_n"] = prov.groupby("sector")["provider_code"].transform("size")
    return prov, cells


prov, cells = data()
p = cells["obs18"].sum() / cells["n"].sum()
z = cfg["benchmark"]["limits"]["99.8%"]
tau2 = {sec: bm.overdispersion_tau2(d["adj_rate"], d["n"], p) for sec, d in prov.groupby("sector")}
period = cfg["period"].replace("RTT-", "").replace("-", " ")

SMALL = {"And", "Of", "The", "For", "On", "Upon", "In"}


def nice(name: str) -> str:
    words = name.title().replace("Nhs", "NHS").replace("'S ", "'s ").split()
    return " ".join(w.lower() if i and w in SMALL else w for i, w in enumerate(words))


FLAG = {
    "above 99.8%": ("hi", "▲ Above 99.8% limit"), "above 95%": ("hi", "△ Above 95% limit"),
    "within 95%": ("ok", "● Within limits"),
    "below 95%": ("lo", "▽ Below 95% limit"), "below 99.8%": ("lo", "▼ Below 99.8% limit"),
}

# ---------------------------------------------------------------- sidebar: record lookup
with st.sidebar:
    st.markdown("<div class='sb-h'>Record lookup</div>", unsafe_allow_html=True)
    sector = st.radio("Peer group", ["NHS trust", "Independent sector / other", "All"], label_visibility="collapsed")
    pool = prov if sector == "All" else prov[prov.sector == sector]
    pool = pool.sort_values("provider_name")
    labels = (pool["provider_code"] + "  ·  " + pool["provider_name"].map(nice)).tolist()
    default = next((i for i, c in enumerate(pool["provider_code"]) if c == "RAJ"), 0)
    pick = st.selectbox("Provider", labels, index=default, help="Type an org code or name to search")
    flag_filter = st.multiselect("Filter by flag (adjusted)", list(FLAG), placeholder="Any flag")
    if flag_filter:
        st.caption(f"{pool.adj_flag_od.isin(flag_filter).sum()} records match: "
                   + ", ".join(pool[pool.adj_flag_od.isin(flag_filter)].provider_code.head(12)))

    st.markdown("<div class='sb-h'>Extract summary</div>", unsafe_allow_html=True)
    rows = [("Period", period), ("Pathways (Part_2)", f"{int(cells.n.sum()):,}"),
            ("Within 18 wks", f"{p*100:.1f}%"), ("Records benchmarked", f"{len(prov)}"),
            ("NHS trusts", f"{(prov.sector=='NHS trust').sum()}"),
            ("Min list size", f"{cfg['benchmark']['min_list_size']:,}")]
    st.markdown("".join(f"<div class='sb-row'><span>{k}</span><b>{v}</b></div>" for k, v in rows),
                unsafe_allow_html=True)
    st.markdown("<div class='sb-h'>Data governance</div>", unsafe_allow_html=True)
    st.caption("Published aggregate statistics (Open Government Licence v3.0). No patient-level data. "
               "All counts are referral-to-treatment pathways, not patients.")

code = pick.split("  ·  ")[0]
r = prov[prov.provider_code == code].iloc[0]

# ---------------------------------------------------------------- system bar + record header
st.markdown(f"""
<div class="sysbar">
  <div class="brand">RTT·PRS<span>Provider Records System — waiting-list benchmarking</span></div>
  <div class="meta"><span class="dot"></span>EXTRACT {cfg['period']} · {len(prov)} RECORDS · SRC NHS ENGLAND (OGL)</div>
</div>""", unsafe_allow_html=True)


def flag_html(label, status):
    cls, text = FLAG[status]
    return f"<span class='flag {cls}'><span class='lbl'>{label}</span>{text}</span>"


fields = [("Org code", r.provider_code, True), ("Peer group", r.sector, False),
          ("Waiting list", f"{int(r.n):,} pathways", False), ("Specialties", f"{int(r.n_specialties)}", False),
          ("Rank (raw → adj.)", f"{r.raw_rate_rank} → {r.adj_rate_rank} / {r.peer_n}", True),
          ("O/E ratio", f"{r.oe:.3f}", True)]
st.markdown(f"""
<div class="record">
  <div class="kicker">Provider record · {period}</div>
  <h1>{nice(r.provider_name)}</h1>
  <div class="fields">{''.join(f"<div class='field'><div class='k'>{k}</div><div class='v{' mono' if m else ''}'>{v}</div></div>" for k, v, m in fields)}</div>
  <div class="flags">{flag_html('Raw funnel', r.raw_flag_od)}{flag_html('Specialty-adjusted', r.adj_flag_od)}</div>
</div>""", unsafe_allow_html=True)

# ---------------------------------------------------------------- observations
d_raw = (r.raw_rate - p) * 100
d_adj = (r.adj_rate - p) * 100


def sign_cls(v):
    return "up" if v > 0 else "down" if v < 0 else ""


obs = [
    ("Under 18 weeks · raw", f"{r.raw_rate*100:.1f}%", f"{d_raw:+.1f} pp vs England", sign_cls(d_raw)),
    ("Expected from mix", f"{r.expected_rate*100:.1f}%", "national specialty rates", ""),
    ("Under 18 weeks · adjusted", f"{r.adj_rate*100:.1f}%", f"{d_adj:+.1f} pp vs England", sign_cls(d_adj)),
    ("England benchmark", f"{p*100:.1f}%", f"{int(cells.n.sum())/1e6:.2f}M pathways", ""),
]
st.markdown("<div class='obs'>" + "".join(
    f"<div class='ob'><div class='k'>{k}</div><div class='v'>{v}</div><div class='s {c}'>{s}</div></div>"
    for k, v, s, c in obs) + "</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------- tabs
PLOT_LAYOUT = dict(
    font=dict(family="IBM Plex Sans, sans-serif", size=12, color=INK2), paper_bgcolor="#fff", plot_bgcolor="#fff",
    margin=dict(t=20, r=20, b=50, l=60), hoverlabel=dict(bgcolor="#0f1f2b", font=dict(color="#fff", family="IBM Plex Mono")),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11)),
)
AX = dict(gridcolor="#eef1f3", zerolinecolor=RULE, linecolor=RULE, ticks="outside", tickcolor=RULE)

t1, t2, t3, t4 = st.tabs(["Funnel position", "Specialty breakdown", "Record fields", "Method notes"])

with t1:
    peers = prov[prov.sector == r.sector]
    xs = np.logspace(np.log10(prov.n.min() * 0.9), np.log10(prov.n.max() * 1.1), 200)
    lo, hi = bm.overdispersed_limits(p, xs, z, tau2[r.sector])
    lo95, hi95 = bm.overdispersed_limits(p, xs, 1.96, tau2[r.sector])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=np.r_[xs, xs[::-1]], y=np.r_[hi, lo[::-1]] * 100, fill="toself",
                             fillcolor="rgba(14,107,122,0.06)", line=dict(width=0), hoverinfo="skip",
                             name="Inside 99.8% limits"))
    for y in (hi, lo):
        fig.add_trace(go.Scatter(x=xs, y=y * 100, mode="lines", line=dict(color=TEAL, width=1.6),
                                 hoverinfo="skip", showlegend=False))
    for y in (hi95, lo95):
        fig.add_trace(go.Scatter(x=xs, y=y * 100, mode="lines", line=dict(color=TEAL, width=1, dash="dot"),
                                 hoverinfo="skip", showlegend=False))
    others = peers[peers.provider_code != code]
    fig.add_trace(go.Scatter(
        x=others.n, y=others.adj_rate * 100, mode="markers", name=f"Peer records ({r.sector})",
        marker=dict(color=NEUTRAL, size=7, opacity=.75, line=dict(color="#fff", width=.8)),
        customdata=np.c_[others.provider_code, others.provider_name.map(nice)],
        hovertemplate="<b>%{customdata[0]}</b> %{customdata[1]}<br>%{x:,} pathways · %{y:.1f}% adj.<extra></extra>"))
    fig.add_trace(go.Scatter(x=[r.n, r.n], y=[r.raw_rate * 100, r.adj_rate * 100], mode="lines",
                             line=dict(color=INK, width=1.5), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=[r.n], y=[r.raw_rate * 100], mode="markers", name="This record · raw",
                             marker=dict(color="#fff", size=12, line=dict(color=INK, width=2)),
                             hovertemplate="Raw %{y:.1f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=[r.n], y=[r.adj_rate * 100], mode="markers", name="This record · adjusted",
                             marker=dict(color=TEAL, size=13, line=dict(color="#fff", width=1.5)),
                             hovertemplate="Adjusted %{y:.1f}%<extra></extra>"))
    fig.add_hline(y=p * 100, line=dict(color=INK2, width=1), annotation_text=f"England {p*100:.1f}%",
                  annotation_font=dict(size=11, color=INK2), annotation_position="top left")
    fig.update_layout(**PLOT_LAYOUT, height=470)
    fig.update_xaxes(type="log", title="Waiting list size (incomplete pathways, log scale)", **AX)
    fig.update_yaxes(title="% of pathways under 18 weeks (specialty-adjusted)", ticksuffix="%", **AX)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown(f"<div class='note'>Solid band: 99.8% limits; dotted: 95%. Both are overdispersion-adjusted for the "
                f"<b>{r.sector}</b> peer group (between-provider SD ≈ {np.sqrt(tau2[r.sector])*100:.1f} pp). "
                "Outside the limits means unlikely to be chance at this list size — not ‘failing’.</div>",
                unsafe_allow_html=True)

with t2:
    cb = cells[(cells.provider_code == code) & (cells.n > 0)].copy()
    cb["provider_pct"] = cb.obs18 / cb.n * 100
    cb["england_pct"] = cb.p_s * 100
    cb["gap"] = cb.provider_pct - cb.england_pct
    cb["share"] = cb.n / cb.n.sum() * 100
    cb["specialty"] = cb.tf_name.str.replace(r" Service$", "", regex=True)
    cb = cb.sort_values("n", ascending=False)
    c1, c2 = st.columns([0.7, 1.3])
    with c1:
        bar = go.Figure(go.Bar(
            y=cb.specialty, x=cb.gap, orientation="h",
            marker=dict(color=np.where(cb.gap >= 0, HI, LO), cornerradius=3),
            customdata=np.c_[cb.n, cb.provider_pct, cb.england_pct],
            hovertemplate="<b>%{y}</b><br>%{customdata[0]:,} pathways<br>%{customdata[1]:.1f}% vs England "
                          "%{customdata[2]:.1f}%<extra></extra>"))
        bar.update_layout(**{**PLOT_LAYOUT, "margin": dict(t=10, r=10, b=40, l=10)},
                          height=max(260, 26 * len(cb) + 60), bargap=.35)
        bar.update_xaxes(title="pp vs England rate for the same specialty", ticksuffix=" pp", **AX)
        bar.update_yaxes(autorange="reversed", **{**AX, "ticks": ""})
        st.plotly_chart(bar, use_container_width=True, config={"displayModeBar": False})
    with c2:
        st.dataframe(
            cb[["specialty", "n", "share", "provider_pct", "england_pct", "gap"]],
            hide_index=True, use_container_width=True, height=max(260, 35 * len(cb) + 38),
            column_config={
                "tf_code": None,
                "specialty": st.column_config.TextColumn("Specialty"),
                "n": st.column_config.NumberColumn("Pathways", format="localized"),
                "share": st.column_config.ProgressColumn("Share of list", format="%.1f%%", min_value=0,
                                                         max_value=float(cb.share.max())),
                "provider_pct": st.column_config.NumberColumn("<18 wks", format="%.1f%%"),
                "england_pct": st.column_config.NumberColumn("England", format="%.1f%%"),
                "gap": st.column_config.NumberColumn("Gap", format="%+.1f pp"),
            })

with t3:
    rec = pd.DataFrame([
        ("provider_code", r.provider_code, "Organisation code"),
        ("provider_name", r.provider_name, "As submitted"),
        ("sector", r.sector, "Derived from name (NHS + TRUST)"),
        ("n", f"{int(r.n):,}", "Incomplete pathways (Part_2), all commissioners"),
        ("obs18", f"{int(r.obs18):,}", "Observed pathways under 18 weeks"),
        ("exp18", f"{r.exp18:,.1f}", "Σ n_s × national rate_s"),
        ("raw_rate", f"{r.raw_rate:.4f}", "obs18 / n"),
        ("expected_rate", f"{r.expected_rate:.4f}", "exp18 / n"),
        ("oe", f"{r.oe:.4f}", "obs18 / exp18"),
        ("adj_rate", f"{r.adj_rate:.4f}", "oe × England rate"),
        ("raw_flag_binomial", r.raw_flag, "Plain binomial limits (for reference)"),
        ("raw_flag_od", r.raw_flag_od, "Overdispersion-adjusted, peer group"),
        ("adj_flag_od", r.adj_flag_od, "Overdispersion-adjusted, peer group"),
    ], columns=["Field", "Value", "Definition"])
    st.dataframe(rec, hide_index=True, use_container_width=True, height=490,
                 column_config={"Field": st.column_config.TextColumn(width="medium"),
                                "Definition": st.column_config.TextColumn(width="large")})
    st.download_button("Export record (CSV)", rec.to_csv(index=False).encode(),
                       file_name=f"rtt_record_{code}.csv", mime="text/csv")

with t4:
    st.markdown("""
**Specialty adjustment (indirect standardisation).** Expected within-18 = Σ over the provider's specialties of its
pathways × the England rate for that specialty. O/E = observed ÷ expected; adjusted rate = O/E × England rate.
England's O/E is exactly 1. Adjusted rates can exceed 100% for providers far above expectation.

**Funnel limits.** p ± z·√(p(1−p)/n + τ²), z = 1.96 (95%) or 3.09 (99.8%). τ² is the between-provider variance
(Spiegelhalter 2005), estimated separately for NHS trusts and independent providers. Plain binomial limits flag
almost every large trust and are shown in *Record fields* for reference only.

**Not adjusted for.** Complexity within a specialty, deprivation, referral thresholds and demand. One month only.

**Reconciliation.** This commissioner-based extract runs ~0.4% above NHS England's published provider-based totals;
long-wait (65/78/104-week) counts are not yet reconciled and are not shown here.
""")

st.markdown("<div class='foot'>Source: NHS England, Referral to Treatment waiting times, full CSV extract "
            f"({period}). Open Government Licence v3.0. Counts are pathways, not patients. "
            "Six trusts submitted no data for this period.</div>", unsafe_allow_html=True)
