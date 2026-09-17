"""Bot runner — state machine for strategy lifecycle."""

import logging
from datetime import datetime, timezone
from typing import Literal, Optional

import requests

from core import CandleList, PriceCandle
from strategies import StrategyYojic
from trading_controls import TradingControlPaper, TradingControlBingx

logger = logging.getLogger(__name__)

Mode = Literal["paper", "demo", "real"]
Status = Literal["idle", "running", "paused"]

BINGX_REST = "https://open-api.bingx.com"


def _fetch_klines(symbol: str, interval: str, limit: int = 1000):
    url = f"{BINGX_REST}/openApi/swap/v2/quote/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    if data.get("code") != 0:
        logger.warning("REST klines error: %s", data)
        return []
    return data.get("data", [])


class BotRunner:
    def __init__(self):
        self.status: Status = "idle"
        self.candle_list: Optional[CandleList] = None
        self.trading_control: Optional[TradingControlPaper | TradingControlBingx] = None
        self.strategy: Optional[StrategyYojic] = None
        self.symbol: str = ""
        self.interval: str = ""
        self.balance: float = 100.0
        self.mode: Mode = "paper"

    def start(self, symbol: str, interval: str, balance: float, mode: Mode = "paper"):
        if self.status != "idle":
            print("Already running. Stop first.")
            return

        self.symbol = symbol.upper()
        self.interval = interval
        self.balance = balance
        self.mode = mode

        api_symbol = self.symbol.replace("USDT", "-USDT")

        print(f"Fetching {interval} candles for {self.symbol}...")
        raw_klines = _fetch_klines(api_symbol, interval, 1000)
        if not raw_klines:
            print("No history data from BingX")
            return
        print(f"Loaded {len(raw_klines)} candles")

        candle_list = CandleList()
        for i, k in enumerate(raw_klines):
            candle_list.add(PriceCandle(
                id=i,
                open=float(k["open"]),
                high=float(k["high"]),
                low=float(k["low"]),
                close=float(k["close"]),
                open_time=datetime.fromtimestamp(
                    int(k["time"]) / 1000, tz=timezone.utc
                ),
            ))

        common = dict(
            candle_list=candle_list,
            balance_initial=balance,
            risk_per_position_pct=1.0,
            leverage_max=10.0,
            risk_from_peak_balance=True,
            commission_rate=0.00025,
            symbol=self.symbol,
        )

        if mode == "paper":
            tc = TradingControlPaper(**common)
        elif mode == "demo":
            print("Demo mode — will connect to BingX testnet")
            tc = TradingControlBingx(**common, mode_demo=True)
        else:
            print("Real mode — will connect to BingX mainnet")
            tc = TradingControlBingx(**common, mode_demo=False)

        strategy = StrategyYojic(
            candle_list=candle_list,
            trading_control=tc,
        )

        print("Feeding history to strategy...")
        for candle in list(candle_list.list):
            strategy.candle_new(candle)

        strategy.start()
        print("Strategy started — waiting for live candles")

        self.candle_list = candle_list
        self.trading_control = tc
        self.strategy = strategy
        self.status = "running"

        self._print_trades(tc)
        self._print_summary(tc)

    def stop(self):
        if self.strategy:
            self.strategy.stop_and_close()
        self.status = "idle"
        self.candle_list = None
        self.trading_control = None
        self.strategy = None
        print("Stopped")

    def pause(self):
        if self.status == "running" and self.strategy:
            self.strategy.stop()
            self.status = "paused"
            print("Paused — no new entries")

    def resume(self):
        if self.status == "paused" and self.strategy:
            self.strategy.start()
            self.status = "running"
            print("Resumed")

    def status_info(self) -> dict:
        tc = self.trading_control
        info = {
            "status": self.status,
            "symbol": self.symbol,
            "interval": self.interval,
            "mode": self.mode,
        }
        if tc:
            info["balance"] = round(tc.balance, 2)
            info["balance_peak"] = round(tc.balance_peak, 2)
            info["trades"] = len(tc.position_list)
            if tc.position:
                p = tc.position
                info["position"] = {
                    "side": p.side,
                    "entry": round(p.entry_price, 2),
                    "sl": round(p.stop_loss_price, 2),
                    "size": round(p.size, 4),
                }
        return info

    def _print_trades(self, tc):
        if not tc.position_list:
            return
        print(f"\nTrades ({len(tc.position_list)}):")
        print(f"  {'#':<4} {'Side':<6} {'Entry':<10} {'Exit':<10} {'PnL':<10} {'Result':<8}")
        print(f"  {'─' * 48}")
        for i, pt in enumerate(tc.position_list):
            p = pt.position
            pnl = pt.profit or 0
            result = "W" if pnl > 0 else "L"
            print(
                f"  {i:<4} {p.side:<6} {p.entry_price:<10.2f} "
                f"{pt.exit_price or 0:<10.2f} {pnl:<10.2f} {result:<8}"
            )

    def _print_summary(self, tc):
        trades = len(tc.position_list)
        print(f"\n{'=' * 50}")
        print(f"  Symbol:   {self.symbol} ({self.interval})")
        print(f"  Mode:     {self.mode}")
        print(f"  Trades:   {trades}")
        print(f"  Balance:  ${tc.balance:.2f}  (peak: ${tc.balance_peak:.2f})")
        if trades > 0:
            wins = sum(1 for p in tc.position_list if p.profit and p.profit > 0)
            print(f"  Win rate: {wins}/{trades} ({wins / trades * 100:.1f}%)")
            total_pnl = sum(p.profit or 0 for p in tc.position_list)
            print(f"  Net PnL:  ${total_pnl:.2f}")
        print(f"{'=' * 50}")
