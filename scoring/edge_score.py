from __future__ import annotations
from typing import List, Tuple
from api.schemas import Edge, Signals, Regime

def score_edge(regime: Regime, signals: Signals) -> Edge:
    # Composite score that prefers:
    # - trend with momentum
    # - stable liquidity
    # - low risk
    explain: List[str] = []

    base = 0.0
    if regime.label == "TRENDING":
        base += 0.25
        explain.append("trend_regime")
    elif regime.label == "MEAN_REVERTING":
        base += 0.15
        explain.append("mr_regime")
    elif regime.label == "LIQUIDATION_RISK":
        base -= 0.25
        explain.append("liq_risk_regime")
    elif regime.label == "CHAOTIC":
        base -= 0.15
        explain.append("chaotic_regime")

    # agreement: momentum + liquidity - risk
    score = base + 0.55 * signals.momentum + 0.45 * signals.liquidity - 0.65 * signals.risk

    # actionable if score clears threshold AND not liquidation risk
    actionable = (score > 0.55) and (regime.label not in ("LIQUIDATION_RISK", "CHAOTIC"))

    if signals.momentum > 0.6: explain.append("momentum_high")
    if signals.liquidity > 0.6: explain.append("liquidity_good")
    if signals.risk > 0.55: explain.append("risk_elevated")
    if actionable: explain.append("actionable")

    # clamp
    score = float(max(0.0, min(1.0, score)))
    return Edge(score=score, actionable=bool(actionable), explain=explain)
