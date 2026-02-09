from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

RegimeLabel = Literal["TRENDING", "MEAN_REVERTING", "LIQUIDATION_RISK", "CHAOTIC", "UNKNOWN"]

class Regime(BaseModel):
    label: RegimeLabel = "UNKNOWN"
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)

class Signals(BaseModel):
    momentum: float = Field(ge=0.0, le=1.0, default=0.0)
    liquidity: float = Field(ge=0.0, le=1.0, default=0.0)
    risk: float = Field(ge=0.0, le=1.0, default=0.0)

class Edge(BaseModel):
    score: float = Field(ge=0.0, le=1.0, default=0.0)
    actionable: bool = False
    explain: List[str] = Field(default_factory=list)

class SignalEnvelope(BaseModel):
    timestamp_ms: int
    coin: str
    regime: Regime
    signals: Signals
    edge: Edge

class Health(BaseModel):
    ok: bool
    ws_connected: bool
    coins: List[str]
    uptime_sec: float

class SystemState(BaseModel):
    timestamp_ms: int
    coins: List[str]
    last_trade_ms: dict
    last_book_ms: dict
