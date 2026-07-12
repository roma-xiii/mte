import argparse
import asyncio
import json
import queue
import threading
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

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
    exchange: str = "sim"
    instrument: str = "EURUSD"
    timeframe: str = "1m"
    data_dir: str = "data"
    fast_sma_period: int = 10
    slow_sma_period: int = 20
    trade_size: int = 100000
    order_type: str = "market"
    limit_offset_ticks: int = 5
    synthetic: bool = False
    synthetic_bars: int = 10000
    speed: float = 0.0
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    csv_file: Optional[str] = None


class SessionBuffer:
    def __init__(self):
        self.bars: list[dict] = []
        self.trades: list[dict] = []
        self.entries: list[dict] = []
        self.exits: list[dict] = []
        self.logs: list[dict] = []
        self.ready: Optional[dict] = None
        self.complete: Optional[dict] = None
        self.error: Optional[dict] = None

    def add(self, event: dict):
        t = event.get("type")
        if t == "bar":
            self.bars.append(event)
        elif t == "trade":
            self.trades.append(event)
        elif t == "entry":
            self.entries.append(event)
        elif t == "exit":
            self.exits.append(event)
        elif t == "log":
            self.logs.append(event)
        elif t == "ready":
            self.ready = event
        elif t == "complete":
            self.complete = event
        elif t == "error":
            self.error = event

    def snapshot(self) -> dict:
        return {
            "type": "snapshot",
            "bars": self.bars,
            "trades": self.trades,
            "entries": self.entries,
            "exits": self.exits,
            "logs": self.logs[-1000:],
            "ready": self.ready,
            "complete": self.complete,
            "error": self.error,
        }


@dataclass
class SessionState:
    buffer: SessionBuffer
    cmd_queue: queue.Queue
    event_queue: queue.Queue
    stop_flag: threading.Event
    engine_thread: Optional[threading.Thread] = None


_current_session: Optional[SessionState] = None
_session_lock = threading.Lock()


def _to_float(value: Any) -> float:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Money):
        return float(value.as_double())
    return float(value)


def _emit(event: dict, event_queue: queue.Queue, buffer: Optional[SessionBuffer] = None):
    event_queue.put(event)
    if buffer is not None:
        buffer.add(event)


def run_nautilus(
    config: RunnerConfig,
    cmd_queue: queue.Queue,
    event_queue: queue.Queue,
    stop_flag: threading.Event,
    buffer: Optional[SessionBuffer] = None,
):
    available = list_available_instruments(config.data_dir)

    if config.csv_file:
        match = [x for x in available if x["file"] == config.csv_file]
        if not match:
            _emit({"type": "error", "message": f"File {config.csv_file} not found"}, event_queue, buffer)
            _emit({"type": "log", "level": "error", "message": f"File {config.csv_file} not found", "timestamp": time.time()}, event_queue, buffer)
            return
        _emit({"type": "log", "level": "info", "message": f"Loading data from {config.csv_file}", "timestamp": time.time()}, event_queue, buffer)
        instrument, bar_type, bars = load_bars(config.data_dir, match[0]["instrument"], match[0]["timeframe"])
    elif available and not config.synthetic:
        match = [x for x in available if x["instrument"] == config.instrument]
        if not match:
            _emit({"type": "error", "message": f"Instrument {config.instrument} not found"}, event_queue, buffer)
            return
        _emit({"type": "log", "level": "info", "message": f"Loading data for {config.instrument} ({config.timeframe})", "timestamp": time.time()}, event_queue, buffer)
        instrument, bar_type, bars = load_bars(config.data_dir, config.instrument, config.timeframe)
    else:
        _emit({"type": "log", "level": "info", "message": f"Generating {config.synthetic_bars} synthetic bars", "timestamp": time.time()}, event_queue, buffer)
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
            fast_sma_period=config.fast_sma_period,
            slow_sma_period=config.slow_sma_period,
            order_type=config.order_type,
            limit_offset_ticks=config.limit_offset_ticks,
        ),
    )
    engine.add_strategy(strategy)

    _emit({
        "type": "ready",
        "total_bars": total_bars,
        "instrument": str(instrument.id),
        "timeframe": config.timeframe,
    }, event_queue, buffer)

    _emit({
        "type": "log",
        "level": "info",
        "message": f"Starting backtest: {instrument.id} @ {config.timeframe}, {total_bars} bars",
        "timestamp": time.time(),
    }, event_queue, buffer)

    bar_index = 0
    closed_positions = set()
    current_speed = config.speed

    def process_one_bar():
        nonlocal bar_index
        engine.add_data([bars[bar_index]])
        engine.run(streaming=True)

        account = engine.cache.account_for_venue(venue)
        bar = bars[bar_index]

        _emit({
            "type": "bar",
            "index": bar_index,
            "total": total_bars,
            "open": _to_float(bar.open),
            "high": _to_float(bar.high),
            "low": _to_float(bar.low),
            "close": _to_float(bar.close),
            "volume": _to_float(bar.volume.as_double()) if hasattr(bar, 'volume') and bar.volume else 0,
            "timestamp": str(bar.ts_event),
            "balance": _to_float(account.balance(USD).total),
        }, event_queue, buffer)

        if strategy.indicators_initialized():
            _emit({
                "type": "sma",
                "fast": _to_float(strategy.fast_sma.value),
                "slow": _to_float(strategy.slow_sma.value),
            }, event_queue, buffer)

        for pos in engine.cache.positions():
            if not pos.is_closed:
                _emit({
                    "type": "position",
                    "id": str(pos.id),
                    "side": str(pos.side),
                    "instrument_id": str(pos.instrument_id),
                    "quantity": _to_float(pos.quantity),
                    "entry": _to_float(pos.avg_px_open),
                    "unrealized_pnl": _to_float(pos.unrealized_pnl(bar.close)),
                }, event_queue, buffer)
            elif str(pos.id) not in closed_positions:
                closed_positions.add(str(pos.id))
                pnl = _to_float(pos.realized_pnl)
                entry_px = _to_float(pos.avg_px_open)
                exit_px = _to_float(pos.avg_px_close)

                _emit({
                    "type": "entry",
                    "side": str(pos.side),
                    "price": entry_px,
                    "size": _to_float(pos.quantity),
                    "timestamp": str(pos.ts_opened),
                }, event_queue, buffer)

                _emit({
                    "type": "exit",
                    "side": str(pos.side),
                    "price": exit_px,
                    "pnl": pnl,
                    "timestamp": str(pos.ts_closed),
                }, event_queue, buffer)

                _emit({
                    "type": "trade",
                    "id": str(pos.id),
                    "side": str(pos.side),
                    "instrument_id": str(pos.instrument_id),
                    "quantity": _to_float(pos.quantity),
                    "entry_price": entry_px,
                    "exit_price": exit_px,
                    "pnl": pnl,
                    "entry_time": str(pos.ts_opened),
                    "exit_time": str(pos.ts_closed),
                }, event_queue, buffer)

    try:
        while bar_index < total_bars and not stop_flag.is_set():
            count = 1

            for _ in range(count):
                if bar_index >= total_bars or stop_flag.is_set():
                    break
                process_one_bar()
                bar_index += 1

                if current_speed > 0 and bar_index < total_bars and not stop_flag.is_set():
                    time.sleep(1.0 / current_speed)

            if bar_index >= total_bars or stop_flag.is_set():
                break

            try:
                cmd = cmd_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            action = cmd.get("cmd")
            if action == "stop":
                _emit({"type": "log", "level": "info", "message": "Backtest stopped by user", "timestamp": time.time()}, event_queue, buffer)
                break
            elif action == "next":
                pass
            elif action == "pause":
                _emit({"type": "paused"}, event_queue, buffer)
                _emit({"type": "log", "level": "info", "message": "Backtest paused", "timestamp": time.time()}, event_queue, buffer)
                while not stop_flag.is_set():
                    try:
                        cmd2 = cmd_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    a2 = cmd2.get("cmd")
                    if a2 == "resume":
                        _emit({"type": "log", "level": "info", "message": "Backtest resumed", "timestamp": time.time()}, event_queue, buffer)
                        break
                    elif a2 == "stop":
                        _emit({"type": "log", "level": "info", "message": "Backtest stopped by user", "timestamp": time.time()}, event_queue, buffer)
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
                "total_trades": len(closed_positions),
                "sharpe": str(s_ret.get("Sharpe Ratio (252 days)", 0)),
                "max_drawdown": str(s_ret.get("Max Drawdown", 0)),
                "win_rate": str(pnl_usd.get("Win Rate", 0)),
            }

            _emit({
                "type": "log",
                "level": "info",
                "message": f"Backtest complete: PnL={stats['pnl']}, Trades={stats['total_trades']}, Sharpe={stats['sharpe']}",
                "timestamp": time.time(),
            }, event_queue, buffer)

        _emit({"type": "complete", "stats": stats}, event_queue, buffer)
        engine.dispose()

    except Exception as e:
        _emit({"type": "error", "message": str(e)}, event_queue, buffer)
        _emit({"type": "log", "level": "error", "message": f"Backtest error: {e}", "timestamp": time.time()}, event_queue, buffer)
        engine.dispose()


STRATEGIES_META = [
    {
        "name": "sma_crossover",
        "label": "SMA Crossover",
        "params": {
            "fast_sma_period": {"type": "int", "label": "Fast SMA Period", "default": 10, "min": 2, "max": 200},
            "slow_sma_period": {"type": "int", "label": "Slow SMA Period", "default": 20, "min": 5, "max": 500},
            "trade_size": {"type": "float", "label": "Trade Size (USD)", "default": 100000, "min": 1},
            "order_type": {"type": "select", "label": "Order Type", "options": ["market", "limit"], "default": "market"},
            "limit_offset_ticks": {"type": "int", "label": "Limit Offset Ticks", "default": 5, "min": 1, "max": 100},
        },
    },
]


async def send_strategies_list(socket: WebSocket):
    await socket.send_text(json.dumps({"type": "strategies_list", "data": STRATEGIES_META}))


async def send_data_list(socket: WebSocket):
    instruments = list_available_instruments("data")
    await socket.send_text(json.dumps({"type": "data_list", "data": instruments}))


async def handle_command(cmd: dict, socket: WebSocket) -> None:
    global _current_session
    action = cmd.get("cmd")

    if action == "start":
        with _session_lock:
            if _current_session is not None:
                _current_session.stop_flag.set()

            config = RunnerConfig(**cmd.get("config", {}))
            buffer = SessionBuffer()
            event_q = queue.Queue()
            cmd_q = queue.Queue()
            stop_f = threading.Event()

            session = SessionState(
                buffer=buffer,
                cmd_queue=cmd_q,
                event_queue=event_q,
                stop_flag=stop_f,
            )

            session.engine_thread = threading.Thread(
                target=run_nautilus,
                args=(config, cmd_q, event_q, stop_f, buffer),
                daemon=True,
            )
            session.engine_thread.start()

            _current_session = session

    elif action in ("pause", "resume", "next", "speed", "stop"):
        with _session_lock:
            if _current_session is not None:
                _current_session.cmd_queue.put_nowait(cmd)
                if action == "stop":
                    _current_session.stop_flag.set()

    elif action == "list_data":
        await send_data_list(socket)

    elif action == "list_strategies":
        await send_strategies_list(socket)

    else:
        await socket.send_text(json.dumps({
            "type": "error",
            "message": f"Unknown command: {action}",
        }))


@websocket("/ws")
async def backtest_ws(socket: WebSocket) -> None:
    await socket.accept()

    global _current_session

    with _session_lock:
        if _current_session is not None:
            await socket.send_text(json.dumps(
                _current_session.buffer.snapshot(), default=str,
            ))
            cmd_queue = _current_session.cmd_queue
            event_queue = _current_session.event_queue
            stop_flag = _current_session.stop_flag
        else:
            cmd_queue = queue.Queue()
            event_queue = queue.Queue()
            stop_flag = threading.Event()

    await send_strategies_list(socket)
    await send_data_list(socket)

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
                    await handle_command(cmd, socket)
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    stop_flag.set()
                    break
        except Exception:
            stop_flag.set()

    await asyncio.gather(send_task(), recv_task(), return_exceptions=True)

    with _session_lock:
        if _current_session is not None and _current_session.engine_thread:
            _current_session.engine_thread.join(timeout=2)


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
