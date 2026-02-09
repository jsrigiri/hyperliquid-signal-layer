from __future__ import annotations
import argparse
import asyncio
import time
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
import uvicorn

from config import HLConfig
from ingestion.market_state import MarketState
from ingestion.hyperliquid_ws import HyperliquidWS
from features.compute import summarize_features
from models.regime import classify_regime
from scoring.edge_score import score_edge
from api.schemas import SignalEnvelope, Signals, Health, SystemState

from tools.replay import iter_ndjson

def _now_ms() -> int:
    return int(time.time() * 1000)

app = FastAPI(title="Hyperliquid Signal Layer", version="0.1.0")

STATE = MarketState()
CFG = HLConfig()
WS_CLIENT: Optional[HyperliquidWS] = None
COINS: List[str] = []
REPLAY_PATH: Optional[str] = None
_BG_TASK: Optional[asyncio.Task] = None

@app.get("/health", response_model=Health)
def health() -> Health:
    return Health(ok=True, ws_connected=STATE.ws_connected, coins=COINS, uptime_sec=STATE.uptime_sec())

@app.get("/v1/state", response_model=SystemState)
def system_state() -> SystemState:
    return SystemState(
        timestamp_ms=_now_ms(),
        coins=COINS,
        last_trade_ms={c: STATE.coins.get(c).last_trade_ms if c in STATE.coins else 0 for c in COINS},
        last_book_ms={c: STATE.coins.get(c).last_book_ms if c in STATE.coins else 0 for c in COINS},
    )

@app.get("/v1/signal/{coin}", response_model=SignalEnvelope)
def get_signal(coin: str) -> SignalEnvelope:
    coin = coin.upper()
    cs = STATE.coins.get(coin)
    if not cs:
        raise HTTPException(status_code=404, detail=f"Unknown coin {coin}. Available: {COINS}")

    feat = summarize_features(cs)
    regime = classify_regime(
        ret_std=feat["ret_std"],
        spread_mean=feat["spread_mean"],
        trade_imb_std=feat["trade_imb_std"],
        mom_raw=feat["mom_raw"],
    )
    signals = Signals(momentum=feat["mom_01"], liquidity=feat["liq_01"], risk=feat["risk_01"])
    edge = score_edge(regime, signals)

    return SignalEnvelope(
        timestamp_ms=_now_ms(),
        coin=coin,
        regime=regime,
        signals=signals,
        edge=edge,
    )

async def _run_ws(coins: List[str]) -> None:
    global WS_CLIENT
    WS_CLIENT = HyperliquidWS(state=STATE, cfg=CFG)
    await WS_CLIENT.connect_and_run(coins)

async def _run_replay(path: str) -> None:
    # Feeds recorded ws messages back into the normal handlers by directly importing the client handler.
    from ingestion.hyperliquid_ws import HyperliquidWS
    client = HyperliquidWS(state=STATE, cfg=CFG)
    for m in iter_ndjson(path):
        await client._handle_msg(m)  # intentionally internal for interview prep
        await asyncio.sleep(0)  # yield control

@app.on_event("startup")
async def startup_event():
    global _BG_TASK
    if REPLAY_PATH:
        _BG_TASK = asyncio.create_task(_run_replay(REPLAY_PATH))
    else:
        _BG_TASK = asyncio.create_task(_run_ws(COINS))

@app.on_event("shutdown")
async def shutdown_event():
    global WS_CLIENT, _BG_TASK
    if WS_CLIENT:
        await WS_CLIENT.stop()
    if _BG_TASK:
        _BG_TASK.cancel()

def main():
    global COINS, REPLAY_PATH
    ap = argparse.ArgumentParser()
    ap.add_argument("--coins", default="BTC,ETH,SOL", help="Comma-separated coin symbols")
    ap.add_argument("--replay", default=None, help="Path to NDJSON capture for deterministic replay")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    COINS = [c.strip().upper() for c in args.coins.split(",") if c.strip()]
    REPLAY_PATH = args.replay

    uvicorn.run("api.server:app", host=args.host, port=args.port, reload=False, log_level="info")

if __name__ == "__main__":
    main()
