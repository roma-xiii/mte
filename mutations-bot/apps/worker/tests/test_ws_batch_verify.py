"""WS: collect 5 candles, then batch-compare against REST history."""

import asyncio
import json
import logging
from datetime import datetime, timezone

import requests

from exchanges import KlineStream

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logging.getLogger("websockets").setLevel(logging.WARNING)

BASE_URL = "https://open-api.bingx.com"


def get_klines_rest(symbol: str, interval: str, limit: int):
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
    ws_candles: list[dict] = []

    def on_candle(candle: dict):
        ws_candles.append(candle)
        got = len(ws_candles)
        ws_t = candle["open_time"].strftime("%H:%M:%S")
        print(f"  [{got}/5] WS  T={ws_t}  O={candle['open']:.3f} C={candle['close']:.3f}")

    stream = KlineStream(
        symbol="SOL-USDT",
        interval="1m",
        on_candle=on_candle,
    )

    print("Collecting 5 candles from WS...")
    print()

    task = asyncio.create_task(stream.run())

    while len(ws_candles) < 5:
        await asyncio.sleep(0.5)

    await stream.stop()
    await task

    print("\nFetching REST history (limit=6)...")
    rest_raw = get_klines_rest("SOL-USDT", "1m", limit=6)
    if not rest_raw:
        print("REST returned nothing")
        return

    # REST chronological: [0]=oldest, first 5 are completed
    rest_to_compare = rest_raw[:5]

    print(f"\n{'='*70}")
    print(f"{'#':<4} {'source':<5} {'time':<10} {'O':<10} {'H':<10} {'L':<10} {'C':<10} {'result':<10}")
    print(f"{'='*70}")

    mismatches = 0
    eps = 0.001

    for i in range(5):
        w = ws_candles[i]
        r = rest_to_compare[i]

        # REST uses long names, time in ms
        r_time = datetime.fromtimestamp(int(r["time"]) / 1000, tz=timezone.utc)
        r_o = float(r["open"])
        r_h = float(r["high"])
        r_l = float(r["low"])
        r_c = float(r["close"])
        r_v = float(r.get("volume", 0))

        w_t = w["open_time"]
        w_o = w["open"]
        w_h = w["high"]
        w_l = w["low"]
        w_c = w["close"]
        w_v = w.get("volume", 0)

        match = (
            abs(w_o - r_o) < eps
            and abs(w_h - r_h) < eps
            and abs(w_l - r_l) < eps
            and abs(w_c - r_c) < eps
            and w_t == r_time
        )
        if not match:
            mismatches += 1

        tag = "✅" if match else "❌"

        print(f"{i:<4} {'WS':<5} {w_t.strftime('%H:%M:%S'):<10} {w_o:<10.3f} {w_h:<10.3f} {w_l:<10.3f} {w_c:<10.3f} {tag:<10}")
        print(f"{'':<4} {'REST':<5} {r_time.strftime('%H:%M:%S'):<10} {r_o:<10.3f} {r_h:<10.3f} {r_l:<10.3f} {r_c:<10.3f} {'':<10}")
        if not match:
            # show diffs
            diffs = []
            if abs(w_o - r_o) >= eps:
                diffs.append(f"open diff={abs(w_o-r_o):.4f}")
            if abs(w_h - r_h) >= eps:
                diffs.append(f"high diff={abs(w_h-r_h):.4f}")
            if abs(w_l - r_l) >= eps:
                diffs.append(f"low diff={abs(w_l-r_l):.4f}")
            if abs(w_c - r_c) >= eps:
                diffs.append(f"close diff={abs(w_c-r_c):.4f}")
            if w_t != r_time:
                diffs.append(f"time diff={w_t.timestamp()-r_time.timestamp():.0f}s")
            print(f"{'':<4} {'':<5} {'':<10} {'  MISMATCH: ' + ', '.join(diffs):<50}")
        print()

    print(f"{'='*70}")
    print(f"Result: {5 - mismatches}/5 matched, {mismatches} mismatches")


if __name__ == "__main__":
    asyncio.run(main())
