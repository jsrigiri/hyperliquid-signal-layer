from __future__ import annotations
import asyncio
import json
import time
from typing import Callable, Dict, List, Optional

import websockets
from websockets import WebSocketClientProtocol

from config import HLConfig
from ingestion.market_state import MarketState

def _now_ms() -> int:
    return int(time.time() * 1000)

class HyperliquidWS:
    def __init__(self, state: MarketState, cfg: HLConfig):
        self.state = state
        self.cfg = cfg
        self._ws: Optional[WebSocketClientProtocol] = None
        self._stop = asyncio.Event()

    async def connect_and_run(self, coins: List[str]) -> None:
        backoff = self.cfg.reconnect_backoff_sec
        while not self._stop.is_set():
            try:
                async with websockets.connect(self.cfg.ws_url, ping_interval=None) as ws:
                    self._ws = ws
                    self.state.ws_connected = True
                    await self._subscribe_all(coins)
                    backoff = self.cfg.reconnect_backoff_sec
                    await self._run_loop()
            except Exception as e:
                self.state.ws_connected = False
                # reconnect with backoff
                await asyncio.sleep(backoff)
                backoff = min(self.cfg.max_backoff_sec, backoff * 1.6)

    async def stop(self) -> None:
        self._stop.set()
        try:
            if self._ws:
                await self._ws.close()
        except Exception:
            pass

    async def _subscribe_all(self, coins: List[str]) -> None:
        # Per docs: { "method":"subscribe", "subscription": { "type":"trades", "coin":"SOL"} } citeturn1view0turn2view0
        subs = []
        subs.append({"type": "allMids"})
        for c in coins:
            subs.extend([
                {"type": "trades", "coin": c},
                {"type": "l2Book", "coin": c},
                {"type": "candle", "coin": c, "interval": "1m"},
                {"type": "activeAssetCtx", "coin": c},
            ])
        for s in subs:
            await self._send({"method": "subscribe", "subscription": s})

    async def _run_loop(self) -> None:
        assert self._ws is not None
        # lightweight heartbeat
        hb_task = asyncio.create_task(self._heartbeat())
        try:
            async for msg in self._ws:
                data = json.loads(msg)
                await self._handle_msg(data)
        finally:
            hb_task.cancel()
            self.state.ws_connected = False

    async def _heartbeat(self) -> None:
        # Hyperliquid provides a heartbeats doc page; here we just send pings to keep connection alive
        while True:
            await asyncio.sleep(self.cfg.heartbeat_sec)
            try:
                if self._ws:
                    pong = await self._ws.ping()
                    await asyncio.wait_for(pong, timeout=10)
            except Exception:
                return

    async def _send(self, obj: dict) -> None:
        if not self._ws:
            return
        await self._ws.send(json.dumps(obj))

    async def _handle_msg(self, m: dict) -> None:
        ch = m.get("channel")
        d = m.get("data")
        if not ch:
            return
        # Ignore subscriptionResponse; it echoes your subscription and may include snapshots (isSnapshot flag on some streams) citeturn2view0
        if ch == "subscriptionResponse":
            return

        # trades stream: channel "trades" data: WsTrade[] citeturn2view0
        if ch == "trades" and isinstance(d, list) and d:
            coin = d[0].get("coin")
            if coin:
                cs = self.state.ensure_coin(coin)
                ts_ms = int(d[0].get("time", _now_ms()))
                cs.update_trades(d, ts_ms)
            return

        # order book stream: channel "l2Book" data: {coin, time, levels: [[bids],[asks]]} citeturn2view0
        if ch == "l2Book" and isinstance(d, dict):
            coin = d.get("coin")
            if coin:
                cs = self.state.ensure_coin(coin)
                ts_ms = int(d.get("time", _now_ms()))
                levels = d.get("levels", [[], []])
                bids = levels[0] if len(levels) > 0 else []
                asks = levels[1] if len(levels) > 1 else []
                # top of book
                if bids and asks:
                    bid = bids[0]
                    ask = asks[0]
                    bid_px, bid_sz = float(bid.get("px", 0.0)), float(bid.get("sz", 0.0))
                    ask_px, ask_sz = float(ask.get("px", 0.0)), float(ask.get("sz", 0.0))
                    cs.update_book_top(bid_px, bid_sz, ask_px, ask_sz, ts_ms)
            return

        # all mids stream: channel "allMids" data: {mids: {coin: px}} citeturn2view0
        if ch == "allMids" and isinstance(d, dict):
            mids = d.get("mids", {})
            # we don't push mids directly; book gives more structure
            return

        # candle / activeAssetCtx are optional enrichments; ignored for now but kept for extension
        return
