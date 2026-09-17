"""Quick test for KlineStream WebSocket client."""

import asyncio
import logging

from exchanges import KlineStream

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def on_candle(data: dict):
    print(
        f"  >>> CANDLE #{data['id']}: "
        f"O={data['open']:.2f} "
        f"H={data['high']:.2f} "
        f"L={data['low']:.2f} "
        f"C={data['close']:.2f} "
        f"V={data['volume']:.1f} "
        f"T={data['open_time'].strftime('%H:%M:%S')}"
    )


async def main():
    stream = KlineStream(
        symbol="SOL-USDT",
        interval="1m",
        on_candle=on_candle,
    )

    print("Starting WS test (SOL-USDT 1m)...")
    print("Waiting for candle close (~60s)...")
    print()

    task = asyncio.create_task(stream.run())
    await asyncio.sleep(70)
    await stream.stop()
    await task

    print()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
