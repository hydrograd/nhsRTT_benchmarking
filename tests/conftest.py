import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rtt import load  # noqa: E402

CFG = load.load_config(ROOT / "config.yaml")
RAW = ROOT / CFG["raw_csv"]


@pytest.fixture(scope="session")
def cfg():
    return CFG


@pytest.fixture(scope="session")
def raw():
    if not RAW.exists():
        pytest.skip("raw extract not downloaded; run scripts/download.py")
    return load.read_raw(RAW)


@pytest.fixture(scope="session")
def split(raw):
    return load.split_totals(raw)


@pytest.fixture(scope="session")
def spec(split):
    return split[0]


@pytest.fixture(scope="session")
def c999(split):
    return split[1]
