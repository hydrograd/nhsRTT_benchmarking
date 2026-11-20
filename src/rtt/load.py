"""Read the NHS England RTT full CSV extract and reshape it.

Grain of the raw file: provider x commissioner x treatment function x RTT part,
with 105 weekly wait bands as columns. Every provider x commissioner x part also
has a C_999 "Total" row equal to the sum of its specialty rows, so specialty rows
and C_999 rows are kept in separate tables and must never be summed together.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import yaml

TOTAL_CODE = "C_999"
WAITING_LIST_PART = "Part_2"          # incomplete pathways = the waiting list
COMPLETED_PARTS = ("Part_1A", "Part_1B")

ID_COLS = {
    "Period": "period",
    "Provider Parent Org Code": "provider_parent_code",
    "Provider Parent Name": "provider_parent_name",
    "Provider Org Code": "provider_code",
    "Provider Org Name": "provider_name",
    "Commissioner Parent Org Code": "commissioner_parent_code",
    "Commissioner Parent Name": "commissioner_parent_name",
    "Commissioner Org Code": "commissioner_code",
    "Commissioner Org Name": "commissioner_name",
    "RTT Part Type": "part",
    "RTT Part Description": "part_description",
    "Treatment Function Code": "tf_code",
    "Treatment Function Name": "tf_name",
}
TOTAL_COLS = {
    "Total": "total",
    "Patients with unknown clock start date": "unknown_clock_start",
    "Total All": "total_all",
}

_BAND_RE = re.compile(r"Gt (\d+)(?: To (\d+))? Weeks SUM 1")


def band_columns(columns) -> list[str]:
    return [c for c in columns if _BAND_RE.fullmatch(c)]


def band_lower_week(col: str) -> int:
    """'Gt 12 To 13 Weeks SUM 1' -> 12; 'Gt 104 Weeks SUM 1' -> 104 (open-ended)."""
    return int(_BAND_RE.fullmatch(col).group(1))


def load_config(path: str | Path = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def read_raw(path: str | Path) -> pd.DataFrame:
    """Read the raw CSV into a wide frame with snake_case id columns and int week bands."""
    df = pd.read_csv(path, low_memory=False)
    bands = band_columns(df.columns)
    assert len(bands) == 105, f"expected 105 week bands, found {len(bands)}"
    df = df.rename(columns={**ID_COLS, **TOTAL_COLS})
    rename_bands = {c: f"w{band_lower_week(c):03d}" for c in bands}
    df = df.rename(columns=rename_bands)
    wcols = list(rename_bands.values())
    df[wcols] = df[wcols].fillna(0).astype("int64")
    df["unknown_clock_start"] = df["unknown_clock_start"].fillna(0).astype("int64")
    df["total_all"] = df["total_all"].fillna(0).astype("int64")
    # "total" is blank for incomplete parts; keep as nullable
    df["total"] = df["total"].astype("Int64")
    df = df.copy()
    df["sector"] = provider_sector(df["provider_name"], df["provider_code"])
    return df


def week_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if re.fullmatch(r"w\d{3}", c)]


def provider_sector(name: pd.Series, code: pd.Series) -> pd.Series:
    """Classify providers: NHS trusts vs independent sector / other providers.

    NHS trusts have 'NHS' and 'TRUST' in their name (e.g. '... NHS FOUNDATION TRUST').
    Everything else (LTD, LIMITED, PLC, private hospitals, community interest
    companies, etc.) is grouped as 'Independent sector / other'.
    """
    n = name.str.upper()
    is_trust = n.str.contains("NHS") & n.str.contains("TRUST")
    return pd.Series(
        ["NHS trust" if t else "Independent sector / other" for t in is_trust], index=name.index
    )


def split_totals(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (specialty_rows, c999_rows). Never concatenate these back together."""
    is_total = df["tf_code"] == TOTAL_CODE
    return df[~is_total].copy(), df[is_total].copy()


def to_long(df: pd.DataFrame) -> pd.DataFrame:
    """One row per provider x commissioner x specialty x part x week band (zero rows dropped)."""
    ids = [
        "period", "provider_code", "provider_name", "sector", "commissioner_code",
        "part", "tf_code", "tf_name",
    ]
    long = df.melt(id_vars=ids, value_vars=week_cols(df), var_name="band", value_name="pathways")
    long = long[long["pathways"] > 0]
    long["week_lower"] = long["band"].str[1:].astype("int16")
    return long.drop(columns="band").reset_index(drop=True)


def build(config_path: str | Path = "config.yaml") -> dict[str, Path]:
    """Read raw CSV, write wide specialty / C_999 tables and the long table as Parquet."""
    cfg = load_config(config_path)
    out = Path(cfg["processed_dir"])
    out.mkdir(parents=True, exist_ok=True)
    df = read_raw(cfg["raw_csv"])
    spec, tot = split_totals(df)
    paths = {
        "specialty_wide": out / "specialty_wide.parquet",
        "c999_wide": out / "c999_wide.parquet",
        "specialty_long": out / "specialty_long.parquet",
    }
    spec.to_parquet(paths["specialty_wide"], index=False)
    tot.to_parquet(paths["c999_wide"], index=False)
    to_long(spec).to_parquet(paths["specialty_long"], index=False)
    return paths


if __name__ == "__main__":
    for k, v in build().items():
        print(k, v)
