from __future__ import annotations
import argparse, asyncio, json, time, os
from typing import List
import websockets

WS_URL = "wss://api.hyperliquid.xyz/ws"

async def record(coins: List[str], out: str, seconds: int) -> None:
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    end = time.time() + seconds
    async with websockets.connect(WS_URL, ping_interval=None) as ws:
        subs = [{"type":"trades","coin":c} for c in coins] + [{"type":"l2Book","coin":c} for c in coins]
        for s in subs:
            await ws.send(json.dumps({"method":"subscribe","subscription":s}))
        with open(out, "w", encoding="utf-8") as f:
            while time.time() < end:
                msg = await ws.recv()
                f.write(msg.strip() + "\n")
    print(f"Wrote {out}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coins", default="BTC", help="Comma-separated, e.g. BTC,ETH")
    ap.add_argument("--out", default="data/capture.ndjson")
    ap.add_argument("--seconds", type=int, default=60)
    args = ap.parse_args()
    coins = [c.strip() for c in args.coins.split(",") if c.strip()]
    asyncio.run(record(coins, args.out, args.seconds))

if __name__ == "__main__":
    main()
