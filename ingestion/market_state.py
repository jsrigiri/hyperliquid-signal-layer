from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Deque, Optional, Tuple, List
from collections import deque
import time

@dataclass
class BookTop:
    bid_px: float = 0.0
    bid_sz: float = 0.0
    ask_px: float = 0.0
    ask_sz: float = 0.0
    spread: float = 0.0
    mid: float = 0.0

@dataclass
class RollingWindow:
    maxlen: int
    values: Deque[float] = field(default_factory=deque)

    def push(self, x: float) -> None:
        self.values.append(float(x))
        while len(self.values) > self.maxlen:
            self.values.popleft()

    def as_list(self) -> List[float]:
        return list(self.values)

@dataclass
class CoinState:
    coin: str
    last_trade_ms: int = 0
    last_book_ms: int = 0
    book_top: BookTop = field(default_factory=BookTop)
    # rolling windows for simple, explainable signals
    mid_returns: RollingWindow = field(default_factory=lambda: RollingWindow(maxlen=120))
    vol_imbalance: RollingWindow = field(default_factory=lambda: RollingWindow(maxlen=120))
    spread_norm: RollingWindow = field(default_factory=lambda: RollingWindow(maxlen=120))
    trade_imbalance: RollingWindow = field(default_factory=lambda: RollingWindow(maxlen=120))
    vol_z: RollingWindow = field(default_factory=lambda: RollingWindow(maxlen=120))

    _prev_mid: Optional[float] = None

    def update_book_top(self, bid_px: float, bid_sz: float, ask_px: float, ask_sz: float, ts_ms: int) -> None:
        self.last_book_ms = ts_ms
        spread = max(0.0, ask_px - bid_px) if bid_px and ask_px else 0.0
        mid = (ask_px + bid_px) / 2.0 if bid_px and ask_px else 0.0
        self.book_top = BookTop(bid_px, bid_sz, ask_px, ask_sz, spread, mid)
        if mid > 0 and self._prev_mid and self._prev_mid > 0:
            r = (mid / self._prev_mid) - 1.0
            self.mid_returns.push(r)
        if mid > 0:
            self._prev_mid = mid
        # order book imbalance: (bidSz - askSz) / (bidSz + askSz)
        denom = (bid_sz + ask_sz)
        imb = (bid_sz - ask_sz) / denom if denom > 0 else 0.0
        self.vol_imbalance.push(imb)
        # normalize spread by mid
        spr = (spread / mid) if mid > 0 else 0.0
        self.spread_norm.push(spr)

    def update_trades(self, trades: list, ts_ms: int) -> None:
        # trades: array of {side, px, sz, ...} from ws
        self.last_trade_ms = ts_ms
        buy = 0.0
        sell = 0.0
        for t in trades:
            sz = float(t.get("sz", 0.0))
            side = str(t.get("side", "")).lower()
            if side == "b" or side == "buy":
                buy += sz
            elif side == "s" or side == "sell":
                sell += sz
        denom = buy + sell
        imb = (buy - sell) / denom if denom > 0 else 0.0
        self.trade_imbalance.push(imb)

@dataclass
class MarketState:
    start_time: float = field(default_factory=time.time)
    coins: Dict[str, CoinState] = field(default_factory=dict)
    ws_connected: bool = False

    def ensure_coin(self, coin: str) -> CoinState:
        if coin not in self.coins:
            self.coins[coin] = CoinState(coin=coin)
        return self.coins[coin]

    def uptime_sec(self) -> float:
        return time.time() - self.start_time
