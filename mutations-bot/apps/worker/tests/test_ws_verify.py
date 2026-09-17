"""Verify WS candle data against REST API after each close."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import requests

from exchanges import KlineStream

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logging.getLogger("websockets").setLevel(logging.WARNING)

BASE_URL = "https://open-api.bingx.com"


def get_klines_rest(symbol: str, interval: str, limit: int = 2):
    url = f"{BASE_URL}/openApi/swap/v2/quote/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data.get("code") == 0:
        return data.get("data", [])
    print(f"REST error: {data}")
    return []


async def main():
    mismatches = 0
    total = 0

    def on_candle(ws_candle: dict):
        nonlocal mismatches, total
        total += 1

        ws_open_time = ws_candle["open_time"]
        ws_o = ws_candle["open"]
        ws_h = ws_candle["high"]
        ws_l = ws_candle["low"]
        ws_c = ws_candle["close"]

        # Fetch REST data immediately
        rest_raw = get_klines_rest("SOL-USDT", "1m", limit=2)
        if not rest_raw:
            print("  ⚠ No REST data")
            return

        # REST returns: open, close, high, low, time (long names)
        rest = rest_raw[0]  # most recent completed candle
        rest_time_ms = int(rest["time"])
        rest_dt = datetime.fromtimestamp(rest_time_ms / 1000, tz=timezone.utc)
        rest_o = float(rest["open"])
        rest_h = float(rest["high"])
        rest_l = float(rest["low"])
        rest_c = float(rest["close"])

        # Compare timestamps
        ws_ms = int(ws_open_time.timestamp() * 1000)
        time_ok = ws_ms == rest_time_ms

        # Compare prices
        diff_o = abs(ws_o - rest_o)
        diff_h = abs(ws_h - rest_h)
        diff_l = abs(ws_l - rest_l)
        diff_c = abs(ws_c - rest_c)
        eps = 0.001
        match = (
            diff_o < eps
            and diff_h < eps
            and diff_l < eps
            and diff_c < eps
            and time_ok
        )

        status = "✅ MATCH" if match else "❌ MISMATCH"
        print(f"\n  {status}  candle #{total}")
        print(
            f"     WS:   T={ws_open_time.strftime('%H:%M:%S')} "
            f"O={ws_o:.3f} H={ws_h:.3f} L={ws_l:.3f} C={ws_c:.3f}"
        )
        print(
            f"     REST: T={rest_dt.strftime('%H:%M:%S')} "
            f"O={rest_o:.3f} H={rest_h:.3f} L={rest_l:.3f} C={rest_c:.3f}"
        )
        if not time_ok:
            print(f"     ⏰ Time mismatch! WS={ws_ms} REST={rest_time_ms} diff={ws_ms - rest_time_ms}ms")
        if diff_o >= eps:
            print(f"     open: {ws_o:.4f} vs {rest_o:.4f} diff={diff_o:.4f}")
            mismatches += 1
        if diff_h >= eps:
            print(f"     high: {ws_h:.4f} vs {rest_h:.4f} diff={diff_h:.4f}")
            mismatches += 1
        if diff_l >= eps:
            print(f"     low:  {ws_l:.4f} vs {rest_l:.4f} diff={diff_l:.4f}")
            mismatches += 1
        if diff_c >= eps:
            print(f"     close:{ws_c:.4f} vs {rest_c:.4f} diff={diff_c:.4f}")
            mismatches += 1

    stream = KlineStream(
        symbol="SOL-USDT",
        interval="1m",
        on_candle=on_candle,
    )

    print("WS vs REST verification. SOL-USDT 1m.")
    print("Waiting for candle closes... (will stop after 5 comparisons)")
    print()

    task = asyncio.create_task(stream.run())

    # run until we have 5 matches or 300 seconds
    for _ in range(300):
        if total >= 5:
            break
        await asyncio.sleep(1)

    await stream.stop()
    await task

    print(f"\n{'='*50}")
    print(f"Total candles: {total}, mismatches: {mismatches}")


if __name__ == "__main__":
    asyncio.run(main())
