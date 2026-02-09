# Hyperliquid Signal Layer

Agent-readable signal infrastructure for Hyperliquid perpetual markets.

This project converts raw on-chain perpetual market data into structured,
validated signals designed to minimize downstream decision complexity for
autonomous trading agents.

---

## Motivation

Autonomous agents fail when ambiguity is pushed downstream. This project
moves complexity upstream by encoding market structure, regime context,
and confidence directly into the signal layer.

---

## Architecture

Hyperliquid WebSocket Data
→ Feature Engineering
→ Regime Detection
→ Risk & Momentum Signals
→ Confidence / Edge Scoring
→ Agent-Readable API

---

## Signals Produced

- Market regime classification (trend / mean-revert / liquidation-risk)
- Momentum and flow-based indicators
- Liquidity and volatility stress metrics
- Composite confidence and edge scores

---

## API Example

```json
{
  "symbol": "BTC",
  "regime": { "label": "TRENDING", "confidence": 0.86 },
  "signals": { "momentum": 0.62, "liquidity": 0.71, "risk": 0.19 },
  "edge": { "score": 0.68, "actionable": true }
}
