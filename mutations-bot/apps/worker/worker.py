"""Console CLI for strategy bot."""

import asyncio
import logging
import os
import signal
from pathlib import Path
from typing import Optional

from bot_runner import BotRunner
from core import PriceCandle
from exchanges import KlineStream

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

bot = BotRunner()
_ws_task: Optional[asyncio.Task] = None


def _make_ws_handler(bot):
    next_id = len(bot.candle_list.list)

    def on_candle(raw: dict):
        nonlocal next_id
        candle = PriceCandle(
            id=next_id,
            open=raw["open"],
            high=raw["high"],
            low=raw["low"],
            close=raw["close"],
            open_time=raw["open_time"],
        )
        next_id += 1
        bot.strategy.candle_new(candle)
        ts = candle.open_time.strftime("%H:%M")
        print(f"  [{ts}] O={candle.open:.2f} H={candle.high:.2f} L={candle.low:.2f} C={candle.close:.2f}")

        info = bot.status_info()
        print(f"  bal=${info['balance']:.2f}  trades={info['trades']}", end="")
        if "position" in info:
            p = info["position"]
            print(f"  pos={p['side']} sz={p['size']} entry={p['entry']} sl={p['sl']}", end="")
        print()

        imp = bot.strategy.structure.impulse
        if imp and imp.low_price and imp.high_price:
            print(f"  impulse: {imp.type} low=${imp.low_price:.2f} high=${imp.high_price:.2f}")
        else:
            print(f"  impulse: —")

    return on_candle


def _start_bot(symbol: str, interval: str, balance: float, mode: str):
    bot.start(symbol, interval, balance, mode)
    if bot.status == "running":
        _stop_ws()
        ws_symbol = bot.symbol.replace("USDT", "-USDT")
        stream = KlineStream(
            symbol=ws_symbol,
            interval=interval,
            on_candle=_make_ws_handler(bot),
        )
        _ws_task = asyncio.create_task(stream.run())
        print(f"WS connected — listening for live {ws_symbol} {interval}")
        return True
    return False


async def _headless_run(loop):
    symbol = os.getenv("BOT_SYMBOL", "")
    interval = os.getenv("BOT_INTERVAL", "")
    balance = os.getenv("BOT_BALANCE", "")
    mode = os.getenv("BOT_MODE", "paper")

    if not (symbol and interval and balance):
        print("Set BOT_SYMBOL, BOT_INTERVAL, BOT_BALANCE env vars")
        return

    print(f"Auto-start: {symbol} {interval} {balance} {mode}")
    _start_bot(symbol, interval, float(balance), mode)

    stop = asyncio.Event()
    loop.add_signal_handler(signal.SIGTERM, stop.set)
    loop.add_signal_handler(signal.SIGINT, stop.set)
    await stop.wait()
    _stop_ws()
    bot.stop()


def _stop_ws():
    global _ws_task
    if _ws_task:
        _ws_task.cancel()
        _ws_task = None


def show_help():
    print("Commands:")
    print("  start SYMBOL INTERVAL BALANCE [paper|demo|real]")
    print("  stop")
    print("  pause")
    print("  resume")
    print("  status")
    print("  help")
    print("  exit")


async def input_loop():
    loop = asyncio.get_event_loop()

    while True:
        line = await loop.run_in_executor(None, lambda: input("> "))
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        cmd = parts[0].lower()

        if cmd == "start":
            if len(parts) < 4:
                print("Usage: start SYMBOL INTERVAL BALANCE [mode]")
                continue
            symbol = parts[1].upper()
            interval = parts[2]
            try:
                balance = float(parts[3])
            except ValueError:
                print("Invalid balance")
                continue
            mode = parts[4] if len(parts) > 4 else "paper"
            if mode not in ("paper", "demo", "real"):
                print("Mode must be: paper, demo, real")
                continue
            _start_bot(symbol, interval, balance, mode)

        elif cmd == "stop":
            _stop_ws()
            bot.stop()

        elif cmd == "pause":
            bot.pause()

        elif cmd == "resume":
            bot.resume()

        elif cmd == "status":
            info = bot.status_info()
            for k, v in info.items():
                if isinstance(v, dict):
                    print(f"  {k}:")
                    for sk, sv in v.items():
                        print(f"    {sk}: {sv}")
                else:
                    print(f"  {k}: {v}")

        elif cmd == "help":
            show_help()

        elif cmd in ("exit", "quit"):
            _stop_ws()
            bot.stop()
            print("Bye")
            break

        else:
            print(f"Unknown: {cmd}. Type help")


async def main():
    print("Mutations Bot Worker")
    print("─" * 40)
    show_help()
    print()

    if os.getenv("BOT_SYMBOL"):
        await _headless_run(asyncio.get_event_loop())
    else:
        await input_loop()


def main_entry() -> None:
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        _stop_ws()
        bot.stop()
        print("\nBye")


if __name__ == "__main__":
    main_entry()
