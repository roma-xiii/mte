import argparse
import json
import sys
import time
from decimal import Decimal
from dataclasses import dataclass
from typing import Optional

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.common.component import set_backtest_force_stop
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


def send(event: dict):
    sys.stdout.write(json.dumps(event, default=str) + "\n")
    sys.stdout.flush()


def read_command() -> Optional[dict]:
    line = sys.stdin.readline()
    if not line:
        return None
    return json.loads(line.strip())


def process_one_bar(engine, bar, bar_index, total_bars, strategy, venue, closed_positions):
    engine.add_data([bar])
    engine.run(streaming=True)

    account = engine.cache.account_for_venue(venue)

    send({
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
        send({
            "type": "sma",
            "fast": str(strategy.fast_sma.value),
            "slow": str(strategy.slow_sma.value),
        })

    for pos in engine.cache.positions():
        if not pos.is_closed:
            send({
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
            send({
                "type": "trade",
                "id": str(pos.id),
                "side": str(pos.side),
                "instrument_id": str(pos.instrument_id),
                "quantity": str(pos.quantity),
                "entry": str(pos.avg_px_open),
                "exit": str(pos.avg_px_close),
                "pnl": str(pos.realized_pnl),
            })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    args = parser.parse_args()

    raw = json.loads(args.config)
    cfg = RunnerConfig(**raw)

    available = list_available_instruments(cfg.data_dir)

    if available and not cfg.synthetic:
        match = [x for x in available if x["instrument"] == cfg.instrument]
        if not match:
            send({"type": "error", "message": f"Instrument {cfg.instrument} not found"})
            sys.exit(1)
        instrument, bar_type, bars = load_bars(cfg.data_dir, cfg.instrument, cfg.timeframe)
    else:
        instrument, bar_type, bars = generate_synthetic_bars(
            n=cfg.synthetic_bars,
            instrument_id_str=f"{cfg.instrument[:3]}/{cfg.instrument[3:]}",
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
            trade_size=Decimal(cfg.trade_size),
            fast_sma_period=cfg.fast_sma,
            slow_sma_period=cfg.slow_sma,
            order_type=cfg.order_type,
            limit_offset_ticks=cfg.limit_offset_ticks,
        ),
    )
    engine.add_strategy(strategy)

    send({
        "type": "ready",
        "total_bars": total_bars,
        "instrument": str(instrument.id),
        "timeframe": cfg.timeframe,
    })

    current_speed = cfg.speed
    bar_index = 0
    closed_positions = set()
    remaining = 0

    while bar_index < total_bars:
        count = max(remaining, 1)

        for _ in range(count):
            if bar_index >= total_bars:
                break
            process_one_bar(engine, bars[bar_index], bar_index, total_bars, strategy, venue, closed_positions)
            bar_index += 1

            if current_speed > 0 and bar_index < total_bars:
                time.sleep(1.0 / current_speed)

        remaining = 0

        if bar_index >= total_bars:
            break

        cmd = read_command()
        if cmd is None:
            break

        action = cmd.get("cmd")
        if action == "stop":
            break
        elif action == "next":
            remaining = int(cmd.get("n", 1)) - 1
        elif action == "pause":
            send({"type": "paused"})
            while True:
                cmd2 = read_command()
                if cmd2 is None:
                    return
                a = cmd2.get("cmd")
                if a == "resume" or a == "next":
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

    send({"type": "complete", "stats": stats})
    engine.dispose()


if __name__ == "__main__":
    main()
