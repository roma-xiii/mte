import argparse
import asyncio
import json
import queue
import threading
import time
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from litestar import Litestar, WebSocket, websocket

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig, LoggingConfig
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money

from data_loader import list_available_instruments, load_bars, generate_synthetic_bars
from data_downloader import download_ohlcv
from strategies import discover_strategies, get_strategy_cls


@dataclass
class RunnerConfig:
    exchange: str = "sim"
    instrument: str = "EURUSD"
    timeframe: str = "1m"
    data_dir: str = "data"
    strategy_name: str = "sma_crossover"
    strategy_params: dict = field(default_factory=dict)
    synthetic: bool = False
    synthetic_bars: int = 10000
    speed: float = 0.0
    starting_balance: float = 1_000_000
    account_type: str = "margin"
    leverage: int = 1
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


class BacktestRunner:
    def __init__(
        self,
        config: RunnerConfig,
        cmd_queue: queue.Queue,
        event_queue: queue.Queue,
        stop_flag: threading.Event,
        buffer: Optional[SessionBuffer] = None,
    ):
        self.config = config
        self.cmd_queue = cmd_queue
        self.event_queue = event_queue
        self.stop_flag = stop_flag
        self.buffer = buffer
        self.engine: Optional[BacktestEngine] = None
        self.strategy = None
        self.instrument = None
        self.bar_type = None
        self.bars = []
        self.venue = Venue("SIM")
        self.bar_index = 0
        self.total_bars = 0
        self.closed_positions: set = set()
        self.current_speed = config.speed

    def emit(self, event: dict):
        _emit(event, self.event_queue, self.buffer)

    def log(self, level: str, message: str):
        self.emit({"type": "log", "level": level, "message": message, "timestamp": time.time()})

    def load_data(self) -> bool:
        available = list_available_instruments(self.config.data_dir)

        csv_path = Path(self.config.data_dir) / f"{self.config.instrument}-{self.config.timeframe}.csv"
        if not self.config.synthetic and self.config.csv_file is None and not csv_path.exists():
            self.log("info", f"Downloading {self.config.instrument} ({self.config.timeframe}) from {self.config.exchange}...")
            try:
                download_ohlcv(
                    exchange_name=self.config.exchange,
                    symbol=self.config.instrument,
                    timeframe=self.config.timeframe,
                    date_from=self.config.date_from,
                    date_to=self.config.date_to,
                    data_dir=self.config.data_dir,
                )
                self.log("info", f"Saved to {self.config.instrument}-{self.config.timeframe}.csv")
                available = list_available_instruments(self.config.data_dir)
            except Exception as e:
                self.emit({"type": "error", "message": f"Download failed: {e}"})
                self.log("error", f"Download failed: {e}")
                return False

        if self.config.csv_file:
            match = [x for x in available if x["file"] == self.config.csv_file]
            if not match:
                self.emit({"type": "error", "message": f"File {self.config.csv_file} not found"})
                self.log("error", f"File {self.config.csv_file} not found")
                return False
            self.log("info", f"Loading data from {self.config.csv_file}")
            self.instrument, self.bar_type, self.bars = load_bars(
                self.config.data_dir, match[0]["instrument"], match[0]["timeframe"],
            )
        elif available and not self.config.synthetic:
            match = [x for x in available if x["instrument"] == self.config.instrument]
            if not match:
                self.emit({"type": "error", "message": f"Instrument {self.config.instrument} not found"})
                return False
            self.log("info", f"Loading data for {self.config.instrument} ({self.config.timeframe})")
            self.instrument, self.bar_type, self.bars = load_bars(
                self.config.data_dir, self.config.instrument, self.config.timeframe,
            )
        else:
            self.log("info", f"Generating {self.config.synthetic_bars} synthetic bars")
            self.instrument, self.bar_type, self.bars = generate_synthetic_bars(
                n=self.config.synthetic_bars,
                instrument_id_str=f"{self.config.instrument[:3]}/{self.config.instrument[3:]}",
            )

        self.total_bars = len(self.bars)
        return True

    def setup_engine(self):
        self.engine = BacktestEngine(
            config=BacktestEngineConfig(logging=LoggingConfig(log_level="ERROR")),
        )

        acc_type = AccountType.MARGIN if self.config.account_type == "margin" else AccountType.CASH
        self.engine.add_venue(
            venue=self.venue,
            oms_type=OmsType.NETTING,
            account_type=acc_type,
            starting_balances=[Money(Decimal(self.config.starting_balance), self.instrument.quote_currency)],
            base_currency=self.instrument.quote_currency,
            default_leverage=Decimal(self.config.leverage),
        )

        self.engine.add_instrument(self.instrument)

    def setup_strategy(self):
        config_cls, strategy_cls = get_strategy_cls(self.config.strategy_name)
        strategy_config = config_cls(
            instrument_id=self.instrument.id,
            bar_type=self.bar_type,
            **self.config.strategy_params,
        )
        self.strategy = strategy_cls(strategy_config)
        self.engine.add_strategy(self.strategy)

    def process_one_bar(self):
        self.engine.add_data([self.bars[self.bar_index]])
        self.engine.run(streaming=True)

        account = self.engine.cache.account_for_venue(self.venue)
        bar = self.bars[self.bar_index]
        quote_ccy = self.instrument.quote_currency

        self.emit({
            "type": "bar",
            "index": self.bar_index,
            "total": self.total_bars,
            "open": _to_float(bar.open),
            "high": _to_float(bar.high),
            "low": _to_float(bar.low),
            "close": _to_float(bar.close),
            "volume": _to_float(bar.volume.as_double()) if hasattr(bar, 'volume') and bar.volume else 0,
            "timestamp": str(bar.ts_event),
            "balance": _to_float(account.balance(quote_ccy).total),
        })

        for indicator_key in ["sma", "ema", "rsi"]:
            try:
                indicator = getattr(self.strategy, indicator_key)
                if hasattr(indicator, "value"):
                    self.emit({"type": indicator_key, "value": _to_float(indicator.value)})
            except AttributeError:
                pass

        for pos in self.engine.cache.positions():
            if not pos.is_closed:
                self.emit({
                    "type": "position",
                    "id": str(pos.id),
                    "side": str(pos.side),
                    "instrument_id": str(pos.instrument_id),
                    "quantity": _to_float(pos.quantity),
                    "entry": _to_float(pos.avg_px_open),
                    "unrealized_pnl": _to_float(pos.unrealized_pnl(bar.close)),
                })
            elif str(pos.id) not in self.closed_positions:
                self.closed_positions.add(str(pos.id))
                pnl = _to_float(pos.realized_pnl)
                entry_px = _to_float(pos.avg_px_open)
                exit_px = _to_float(pos.avg_px_close)

                self.emit({"type": "entry", "side": str(pos.side), "price": entry_px,
                           "size": _to_float(pos.quantity), "timestamp": str(pos.ts_opened)})
                self.emit({"type": "exit", "side": str(pos.side), "price": exit_px,
                           "pnl": pnl, "timestamp": str(pos.ts_closed)})
                self.emit({"type": "trade", "id": str(pos.id), "side": str(pos.side),
                           "instrument_id": str(pos.instrument_id), "quantity": _to_float(pos.quantity),
                           "entry_price": entry_px, "exit_price": exit_px, "pnl": pnl,
                           "entry_time": str(pos.ts_opened), "exit_time": str(pos.ts_closed)})

    def run(self):
        if not self.load_data():
            return
        self.setup_engine()
        self.setup_strategy()

        self.emit({
            "type": "ready",
            "total_bars": self.total_bars,
            "instrument": str(self.instrument.id),
            "timeframe": self.config.timeframe,
        })
        self.log("info", f"Starting backtest: {self.instrument.id} @ {self.config.timeframe}, {self.total_bars} bars")

        try:
            while self.bar_index < self.total_bars and not self.stop_flag.is_set():
                self.process_one_bar()
                self.bar_index += 1

                if self.current_speed > 0 and self.bar_index < self.total_bars and not self.stop_flag.is_set():
                    time.sleep(1.0 / self.current_speed)

                if self.bar_index >= self.total_bars or self.stop_flag.is_set():
                    break

                try:
                    cmd = self.cmd_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                action = cmd.get("cmd")
                if action == "stop":
                    self.log("info", "Backtest stopped by user")
                    break
                elif action == "pause":
                    self.emit({"type": "paused"})
                    self.log("info", "Backtest paused")
                    while not self.stop_flag.is_set():
                        try:
                            cmd2 = self.cmd_queue.get(timeout=0.1)
                        except queue.Empty:
                            continue
                        a2 = cmd2.get("cmd")
                        if a2 == "resume":
                            self.log("info", "Backtest resumed")
                            break
                        elif a2 == "stop":
                            self.log("info", "Backtest stopped by user")
                            return
                elif action == "speed":
                    self.current_speed = float(cmd.get("value", 0))

            self.engine.end()
            result = self.engine.get_result()
            stats = {}
            if result:
                pnl_usd = (result.stats_pnls or {}).get("USD", {}) if hasattr(result, 'stats_pnls') else {}
                s_ret = result.stats_returns or {} if hasattr(result, 'stats_returns') else {}
                stats = {
                    "pnl": str(pnl_usd.get("PnL (total)", 0)),
                    "total_trades": len(self.closed_positions),
                    "sharpe": str(s_ret.get("Sharpe Ratio (252 days)", 0)),
                    "max_drawdown": str(s_ret.get("Max Drawdown", 0)),
                    "win_rate": str(pnl_usd.get("Win Rate", 0)),
                }
                self.log("info", f"Backtest complete: PnL={stats['pnl']}, Trades={stats['total_trades']}, Sharpe={stats['sharpe']}")

            self.emit({"type": "complete", "stats": stats})
            self.engine.dispose()

        except Exception as e:
            self.emit({"type": "error", "message": str(e)})
            self.log("error", f"Backtest error: {e}")
            self.engine.dispose()


async def send_strategies_list(socket: WebSocket):
    strategies = discover_strategies()
    await socket.send_text(json.dumps({"type": "strategies_list", "data": strategies}))


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
                target=BacktestRunner(config, cmd_q, event_q, stop_f, buffer).run,
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

    elif action == "delete_data":
        filename = cmd.get("filename")
        if not filename:
            await socket.send_text(json.dumps({"type": "error", "message": "Missing filename"}))
        else:
            path = Path("data") / filename
            if path.exists():
                path.unlink()
                await send_data_list(socket)
            else:
                await socket.send_text(json.dumps({"type": "error", "message": f"File not found: {filename}"}))

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
