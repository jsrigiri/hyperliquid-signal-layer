# DESIGN: Hyperliquid Agent‑Readable Signal Layer

This repo implements a minimal but interview‑grade **signal infrastructure** for Hyperliquid perpetual markets. It ingests real‑time market data (order book, trades, candles, mids), computes explainable microstructure features, and serves **agent‑readable** outputs (regime + signals + confidence/edge) through a schema‑validated FastAPI.

## 1. Goals

- **Agent readability:** The API returns semantically meaningful fields (regime, risk, confidence) so agents do not need to infer context from raw microstructure.
- **Always‑on reliability:** WS reconnect/backoff, heartbeat handling, and “latest state” snapshots are first‑class.
- **Explainability first:** The baseline regime classifier is a transparent heuristic (easy to debug and tune). It can be swapped with an ML model later.
- **Deterministic demos:** A recorder/replay pipeline supports reproducible evaluation and interview walkthroughs.

## 2. Data sources (Hyperliquid)

The ingestion layer subscribes to Hyperliquid WebSocket feeds (e.g., trades and L2 book) and maintains a rolling in‑memory market state per coin. This is deliberately “thin”: it preserves the minimum information needed to compute stable features at low latency.

## 3. Feature choices

Features are chosen to capture the smallest set of “market reality” signals that matter in perps:

- **Volatility proxy (ret_std):** short‑horizon return variability; spikes often precede liquidation cascades.
- **Spread proxy (spread_mean):** widening spreads indicate liquidity stress and adverse selection.
- **Flow chaos proxy (trade_imb_std):** variance of buy/sell imbalance; high variance indicates unstable flow.
- **Momentum proxy (mom_raw):** normalized directional pressure.

These are intentionally compact so the downstream agent has clear semantics and limited degrees of freedom.

## 4. Regime classifier

`models/regime.py` implements an explainable regime classifier with four regimes:

- **LIQUIDATION_RISK:** high volatility with either spread widening or chaotic flow.
- **TRENDING:** strong momentum and non‑chaotic flow.
- **MEAN_REVERTING:** low momentum, tight spreads, low volatility.
- **CHAOTIC:** flow is noisy or spreads are wide but conditions do not meet liquidation criteria.
- **UNKNOWN:** default “low confidence” bucket.

Why this approach: it is robust, interpretable, and easy to tune during iteration. In production, the same interface can be driven by an HMM/particle filter, gradient boosted model, or a small neural classifier.

## 5. Signal normalization + schemas

The API returns a single envelope:

- `regime`: label + confidence
- `signals`: momentum/liquidity/risk normalized to [0,1]
- `edge`: composite edge score + “actionable” boolean + short explanation list

Pydantic models enforce constraints (ranges, required fields) at the boundary, preventing silent schema drift.

## 6. Confidence and edge scoring

The edge score is designed to be a **decision‑quality scalar** that reduces downstream complexity. It rewards:
- regime stability,
- signal agreement (momentum aligned with flow),
- sufficient liquidity (tight spreads / healthy book).

It penalizes:
- volatility expansion,
- spread widening,
- chaotic flow (higher execution risk / lower predictability).

The `edge.explain` list is a lightweight form of interpretability for agents and operators.

## 7. Testing philosophy

Unit tests target **regime classification** because it is the first upstream abstraction. If regime is wrong, downstream logic becomes brittle. Tests cover each branch and validate confidence bounds.

## 8. Extensions (what to add next)

- Trader/flow taxonomy (aggressive vs passive dominance, impact per trade).
- Cross‑asset regime/correlation (BTC/ETH lead‑lag, sector moves).
- Funding/mark‑based features and liquidation heatmaps.
- Pluggable model interface for replacing heuristics with learned classifiers.
