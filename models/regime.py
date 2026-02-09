from __future__ import annotations
from typing import Tuple, List
from api.schemas import Regime
import math

def classify_regime(
    ret_std: float,
    spread_mean: float,
    trade_imb_std: float,
    mom_raw: float,
) -> Regime:
    # Explainable heuristic classifier:
    # - liquidation-like risk: vol high AND spread widening OR flow chaotic
    # - trending: strong momentum AND not chaotic
    # - mean-reverting: low momentum AND good liquidity
    # - chaotic: very high trade imbalance variance
    conf = 0.0
    label = "UNKNOWN"

    # thresholds are intentionally simple & tunable
    high_vol = ret_std > 0.0025
    wide_spread = spread_mean > 0.0006
    chaotic_flow = trade_imb_std > 0.55

    if (high_vol and wide_spread) or (high_vol and chaotic_flow):
        label = "LIQUIDATION_RISK"
        conf = min(1.0, 0.6 + 80.0 * max(0.0, ret_std - 0.0025))
    elif abs(mom_raw) > 0.35 and not chaotic_flow:
        label = "TRENDING"
        conf = min(1.0, 0.55 + 0.8 * min(1.0, abs(mom_raw)))
    elif abs(mom_raw) < 0.15 and not wide_spread and ret_std < 0.0018:
        label = "MEAN_REVERTING"
        conf = 0.65
    elif chaotic_flow or wide_spread:
        label = "CHAOTIC"
        conf = 0.6
    else:
        label = "UNKNOWN"
        conf = 0.25

    return Regime(label=label, confidence=float(max(0.0, min(1.0, conf))))
