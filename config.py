from dataclasses import dataclass

@dataclass(frozen=True)
class HLConfig:
    # Mainnet websocket per official docs
    ws_url: str = "wss://api.hyperliquid.xyz/ws"
    info_url: str = "https://api.hyperliquid.xyz/info"
    heartbeat_sec: int = 20
    reconnect_backoff_sec: float = 1.5
    max_backoff_sec: float = 30.0
