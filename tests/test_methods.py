"""Unit tests of the methods on synthetic data (no download needed)."""
import numpy as np
import pandas as pd
import pytest

from rtt import benchmark as bm, metrics


def test_percentile_linear_interpolation():
    counts = np.zeros(105)
    counts[0] = 50
    counts[1] = 50
    # median target = 50 -> end of band 0 -> 1.0 week
    assert metrics.percentile_weeks(counts, 0.5) == pytest.approx(1.0)
    # 75th -> halfway through band 1
    assert metrics.percentile_weeks(counts, 0.75) == pytest.approx(1.5)


def test_pct_within_18_and_over():
    counts = np.zeros(105)
    counts[17] = 3   # 17-18 weeks: within
    counts[18] = 1   # 18-19 weeks: over
    counts[104] = 1  # 104+
    assert metrics.pct_within_18(counts) == pytest.approx(60.0)
    assert metrics.over_weeks(counts, 104) == 1
    assert metrics.over_weeks(counts, 52) == 1


def _cells():
    return pd.DataFrame({
        "provider_code": ["A", "A", "B", "B", "C"],
        "provider_name": ["A", "A", "B", "B", "C"],
        "sector": ["NHS trust"] * 5,
        "tf_code": ["s1", "s2", "s1", "s2", "s1"],
        "tf_name": ["s1", "s2", "s1", "s2", "s1"],
        "n": [100, 300, 400, 100, 200],
        "obs18": [80, 120, 300, 50, 150],
    })


def test_indirect_standardisation_england_is_one():
    p = bm.indirect_standardisation(_cells())
    assert p["obs18"].sum() / p["exp18"].sum() == pytest.approx(1.0)


def test_indirect_standardisation_mix_only_provider_has_oe_one():
    # a provider performing exactly at national specialty rates has O/E == 1
    c = _cells()
    rates = bm.national_specialty_rates(c).set_index("tf_code")["p_s"]
    extra = pd.DataFrame({"provider_code": ["D", "D"], "provider_name": ["D", "D"], "sector": ["x", "x"],
                          "tf_code": ["s1", "s2"], "tf_name": ["s1", "s2"], "n": [1e6, 1e6],
                          "obs18": [1e6 * rates["s1"], 1e6 * rates["s2"]]})
    p = bm.indirect_standardisation(pd.concat([c, extra])).set_index("provider_code")
    assert p.loc["D", "oe"] == pytest.approx(1.0, abs=1e-3)


def test_control_limits_formula():
    lo, hi = bm.control_limits(0.5, 100, 1.96)
    assert hi - 0.5 == pytest.approx(1.96 * 0.05)
    assert 0.5 - lo == pytest.approx(1.96 * 0.05)


def test_overdispersion_zero_when_binomial():
    rng = np.random.default_rng(0)
    n = rng.integers(1000, 100000, 400)
    y = rng.binomial(n, 0.6) / n
    assert bm.overdispersion_tau2(pd.Series(y), pd.Series(n), 0.6) < 1e-5
