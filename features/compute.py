from __future__ import annotations
from typing import Dict, Tuple, List
import numpy as np
from ingestion.market_state import CoinState

def _sigmoid01(x: float) -> float:
    # stable squashing into [0,1]
    return float(1.0 / (1.0 + np.exp(-x)))

def summarize_features(cs: CoinState) -> Dict[str, float]:
    # Simple, explainable feature summaries over rolling windows
    mids = cs.mid_returns.as_list()
    volimb = cs.vol_imbalance.as_list()
    spr = cs.spread_norm.as_list()
    trimb = cs.trade_imbalance.as_list()

    def mean(xs): 
        return float(np.mean(xs)) if xs else 0.0
    def std(xs): 
        return float(np.std(xs)) if xs else 0.0

    feat = {}
    feat["ret_mean"] = mean(mids)
    feat["ret_std"] = std(mids)
    feat["ob_imb_mean"] = mean(volimb)
    feat["ob_imb_std"] = std(volimb)
    feat["spread_mean"] = mean(spr)
    feat["trade_imb_mean"] = mean(trimb)
    feat["trade_imb_std"] = std(trimb)

    # Derived “signal-like” normalized scalars (still features)
    # momentum proxy: mean return scaled by volatility
    mom_raw = feat["ret_mean"] / (feat["ret_std"] + 1e-9)
    feat["mom_raw"] = mom_raw
    feat["mom_01"] = _sigmoid01(2.0 * mom_raw)

    # liquidity proxy: inverse spread and stability
    liq_raw = -10.0 * feat["spread_mean"] - 2.0 * feat["ob_imb_std"]
    feat["liq_raw"] = liq_raw
    feat["liq_01"] = _sigmoid01(liq_raw)

    # risk proxy: volatility + depth imbalance variability
    risk_raw = 8.0 * feat["ret_std"] + 1.5 * feat["trade_imb_std"] + 1.5 * feat["ob_imb_std"]
    feat["risk_raw"] = risk_raw
    feat["risk_01"] = _sigmoid01(2.0 * (risk_raw - 0.01))  # shift baseline

    return feat
