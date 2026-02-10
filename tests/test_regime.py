import pytest

from models.regime import classify_regime


def test_liquidation_risk_high_vol_and_wide_spread():
    r = classify_regime(ret_std=0.0030, spread_mean=0.0010, trade_imb_std=0.20, mom_raw=0.0)
    assert r.label == "LIQUIDATION_RISK"
    assert 0.0 <= r.confidence <= 1.0
    assert r.confidence >= 0.6


def test_liquidation_risk_high_vol_and_chaotic_flow():
    r = classify_regime(ret_std=0.0040, spread_mean=0.0002, trade_imb_std=0.70, mom_raw=0.10)
    assert r.label == "LIQUIDATION_RISK"
    assert 0.0 <= r.confidence <= 1.0


def test_trending_strong_momentum_not_chaotic():
    r = classify_regime(ret_std=0.0015, spread_mean=0.0003, trade_imb_std=0.10, mom_raw=0.60)
    assert r.label == "TRENDING"
    assert r.confidence >= 0.55


def test_mean_reverting_low_momentum_good_liquidity_low_vol():
    r = classify_regime(ret_std=0.0010, spread_mean=0.0002, trade_imb_std=0.10, mom_raw=0.05)
    assert r.label == "MEAN_REVERTING"
    assert r.confidence == pytest.approx(0.65)


def test_chaotic_flow_or_wide_spread_fallback():
    r = classify_regime(ret_std=0.0019, spread_mean=0.0007, trade_imb_std=0.20, mom_raw=0.20)
    assert r.label == "CHAOTIC"
    assert r.confidence == pytest.approx(0.6)


def test_unknown_default_case():
    r = classify_regime(ret_std=0.0020, spread_mean=0.0004, trade_imb_std=0.20, mom_raw=0.20)
    assert r.label == "UNKNOWN"
    assert r.confidence == pytest.approx(0.25)
