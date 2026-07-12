import argparse
import asyncio
import json
import queue
import threading
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from litestar import Litestar, WebSocket, websocket

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig, LoggingConfig
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money

from data_loader import list_available_instruments, load_bars, generate_synthetic_bars
from strategies.sma_crossover import SMACross, SMACrossConfig


@dataclass
class RunnerConfig:
    instrument: str = "EURUSD"
    timeframe: str = "1m"
    data_dir: str = "data"
    fast_sma: int = 10
    slow_sma: int = 20
    trade_size: int = 100000
    order_type: str = "market"
    limit_offset_ticks: int = 5
    synthetic: bool = False
    synthetic_bars: int = 10000
    speed: float = 0.0


def run_nautilus(
    config: RunnerConfig,
    cmd_queue: queue.Queue,
    event_queue: queue.Queue,
    stop_flag: threading.Event,
):
    available = list_available_instruments(config.data_dir)

    if available and not config.synthetic:
        match = [x for x in available if x["instrument"] == config.instrument]
        if not match:
            event_queue.put({"type": "error", "message": f"Instrument {config.instrument} not found"})
            return
        instrument, bar_type, bars = load_bars(config.data_dir, config.instrument, config.timeframe)
    else:
        instrument, bar_type, bars = generate_synthetic_bars(
            n=config.synthetic_bars,
            instrument_id_str=f"{config.instrument[:3]}/{config.instrument[3:]}",
        )

    total_bars = len(bars)

    engine = BacktestEngine(
        config=BacktestEngineConfig(
            logging=LoggingConfig(log_level="ERROR"),
        ),
    )

    venue = Venue("SIM")
    engine.add_venue(
        venue=venue,
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        starting_balances=[Money(1_000_000, USD)],
        base_currency=USD,
        default_leverage=Decimal(1),
    )

    engine.add_instrument(instrument)

    strategy = SMACross(
        SMACrossConfig(
            instrument_id=instrument.id,
            bar_type=bar_type,
            trade_size=Decimal(config.trade_size),
            fast_sma_period=config.fast_sma,
            slow_sma_period=config.slow_sma,
            order_type=config.order_type,
            limit_offset_ticks=config.limit_offset_ticks,
        ),
    )
    engine.add_strategy(strategy)

    event_queue.put({
        "type": "ready",
        "total_bars": total_bars,
        "instrument": str(instrument.id),
        "timeframe": config.timeframe,
    })

    bar_index = 0
    closed_positions = set()
    current_speed = config.speed
    remaining = 0

    def process_one_bar():
        nonlocal bar_index
        engine.add_data([bars[bar_index]])
        engine.run(streaming=True)

        account = engine.cache.account_for_venue(venue)
        bar = bars[bar_index]

        event_queue.put({
            "type": "bar",
            "index": bar_index,
            "total": total_bars,
            "open": str(bar.open),
            "high": str(bar.high),
            "low": str(bar.low),
            "close": str(bar.close),
            "balance": str(account.balance(USD).total),
            "equity": str(account.balance(USD).total),
        })

        if strategy.indicators_initialized():
            event_queue.put({
                "type": "sma",
                "fast": str(strategy.fast_sma.value),
                "slow": str(strategy.slow_sma.value),
            })

        for pos in engine.cache.positions():
            if not pos.is_closed:
                event_queue.put({
                    "type": "position",
                    "id": str(pos.id),
                    "side": str(pos.side),
                    "instrument_id": str(pos.instrument_id),
                    "quantity": str(pos.quantity),
                    "entry": str(pos.avg_px_open),
                    "unrealized_pnl": str(pos.unrealized_pnl(bar.close)),
                })
            elif str(pos.id) not in closed_positions:
                closed_positions.add(str(pos.id))
                event_queue.put({
                    "type": "trade",
                    "id": str(pos.id),
                    "side": str(pos.side),
                    "instrument_id": str(pos.instrument_id),
                    "quantity": str(pos.quantity),
                    "entry": str(pos.avg_px_open),
                    "exit": str(pos.avg_px_close),
                    "pnl": str(pos.realized_pnl),
                })

    try:
        while bar_index < total_bars and not stop_flag.is_set():
            count = max(remaining, 1)

            for _ in range(count):
                if bar_index >= total_bars or stop_flag.is_set():
                    break
                process_one_bar()
                bar_index += 1

                if current_speed > 0 and bar_index < total_bars and not stop_flag.is_set():
                    time.sleep(1.0 / current_speed)

            remaining = 0

            if bar_index >= total_bars or stop_flag.is_set():
                break

            cmd = cmd_queue.get()
            if cmd is None:
                break

            action = cmd.get("cmd")
            if action == "stop":
                break
            elif action == "next":
                remaining = int(cmd.get("n", 1)) - 1
            elif action == "pause":
                event_queue.put({"type": "paused"})
                while not stop_flag.is_set():
                    cmd2 = cmd_queue.get()
                    if cmd2 is None:
                        return
                    a = cmd2.get("cmd")
                    if a in ("resume", "next"):
                        remaining = int(cmd2.get("n", 1)) - 1 if a == "next" else 0
                        break
                    elif a == "stop":
                        return
            elif action == "speed":
                current_speed = float(cmd.get("value", 0))

        engine.end()

        result = engine.get_result()
        stats = {}
        if result:
            pnl_usd = (result.stats_pnls or {}).get("USD", {}) if hasattr(result, 'stats_pnls') else {}
            s_ret = result.stats_returns or {} if hasattr(result, 'stats_returns') else {}
            stats = {
                "pnl": str(pnl_usd.get("PnL (total)", 0)),
                "total_trades": str(len(closed_positions)),
                "sharpe": str(s_ret.get("Sharpe Ratio (252 days)", 0)),
                "max_drawdown": str(s_ret.get("Max Drawdown", 0)),
                "win_rate": str(pnl_usd.get("Win Rate", 0)),
            }

        event_queue.put({"type": "complete", "stats": stats})
        engine.dispose()

    except Exception as e:
        event_queue.put({"type": "error", "message": str(e)})
        engine.dispose()


@websocket("/ws")
async def backtest_ws(socket: WebSocket) -> None:
    config_raw = socket.query_params.get("config")
    if not config_raw:
        await socket.close(4000, "Missing config query param")
        return

    try:
        cfg = RunnerConfig(**json.loads(config_raw))
    except Exception as e:
        await socket.close(4001, f"Invalid config: {e}")
        return

    await socket.accept()

    cmd_queue: queue.Queue = queue.Queue()
    event_queue: queue.Queue = queue.Queue()
    stop_flag = threading.Event()

    thread = threading.Thread(
        target=run_nautilus,
        args=(cfg, cmd_queue, event_queue, stop_flag),
        daemon=True,
    )
    thread.start()

    loop = asyncio.get_event_loop()

    async def send_task():
        try:
            while not stop_flag.is_set():
                try:
                    event = await loop.run_in_executor(
                        None, lambda: event_queue.get(timeout=0.1),
                    )
                    await socket.send_text(json.dumps(event, default=str))
                    if event.get("type") in ("complete", "error"):
                        stop_flag.set()
                        break
                except queue.Empty:
                    continue
        except Exception:
            stop_flag.set()

    async def recv_task():
        try:
            while not stop_flag.is_set():
                try:
                    data = await asyncio.wait_for(socket.receive_text(), timeout=0.1)
                    cmd = json.loads(data)
                    cmd_queue.put_nowait(cmd)
                    if cmd.get("cmd") == "stop":
                        stop_flag.set()
                        break
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    stop_flag.set()
                    break
        except Exception:
            stop_flag.set()

    await asyncio.gather(send_task(), recv_task(), return_exceptions=True)

    thread.join(timeout=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    args = parser.parse_args()

    app = Litestar(route_handlers=[backtest_ws])

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
