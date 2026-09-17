"""Stream all raw WS messages for debugging."""

import asyncio
import logging
from datetime import datetime, timezone

from exchanges import KlineStream

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logging.getLogger("websockets").setLevel(logging.WARNING)


async def on_candle(data: dict):
    # Candle that got emitted (completed candle)
    print(
        f"\n  ═══ EMIT CANDLE #{data['id']} ═══\n"
        f"  T={data['open_time'].strftime('%H:%M:%S')} (utc)\n"
        f"  O={data['open']:.2f} H={data['high']:.2f} "
        f"L={data['low']:.2f} C={data['close']:.2f}\n"
    )


async def main():
    print("Ws debug - SOLUSDT 1m")
    print(f"Local time now: {datetime.now().strftime('%H:%M:%S')}")
    print()

    stream = KlineStream(
        symbol="SOL-USDT",
        interval="1m",
        on_candle=on_candle,
    )

    task = asyncio.create_task(stream.run())

    # capture for ~2.5 minutes to see a few candle closes
    await asyncio.sleep(150)
    await stream.stop()
    await task


if __name__ == "__main__":
    asyncio.run(main())
