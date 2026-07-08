from decimal import Decimal

import numpy as np
import pandas as pd

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig, LoggingConfig
from nautilus_trader.model.data import BarType
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money
from nautilus_trader.persistence.wranglers import BarDataWrangler
from nautilus_trader.test_kit.providers import TestInstrumentProvider

from sma_crossover import SMACross, SMACrossConfig


EURUSD = TestInstrumentProvider.default_fx_ccy("EUR/USD")

rng = np.random.default_rng(42)
n = 10_000
price = 1.10 + np.cumsum(rng.normal(0, 0.0002, n))
spread = np.abs(rng.normal(0, 0.0003, n))

bars_df = pd.DataFrame(
    {
        "open": price,
        "high": price + spread,
        "low": price - spread,
        "close": price + rng.normal(0, 0.00005, n),
    },
    index=pd.date_range("2024-01-01", periods=n, freq="1min", tz="UTC"),
)
bars_df["high"] = bars_df[["open", "high", "close"]].max(axis=1)
bars_df["low"] = bars_df[["open", "low", "close"]].min(axis=1)

bar_type = BarType.from_str("EUR/USD.SIM-1-MINUTE-LAST-EXTERNAL")
bars = BarDataWrangler(bar_type, EURUSD).process(bars_df)

engine = BacktestEngine(
    config=BacktestEngineConfig(
        logging=LoggingConfig(log_level="ERROR"),
    ),
)

SIM = Venue("SIM")
engine.add_venue(
    venue=SIM,
    oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN,
    starting_balances=[Money(1_000_000, USD)],
    base_currency=USD,
    default_leverage=Decimal(1),
)

engine.add_instrument(EURUSD)
engine.add_data(bars)

strategy = SMACross(
    SMACrossConfig(
        instrument_id=EURUSD.id,
        bar_type=bar_type,
        trade_size=Decimal(100000),
        fast_sma_period=10,
        slow_sma_period=20,
    ),
)
engine.add_strategy(strategy)

engine.run()

from nautilus_trader.analysis import create_tearsheet, TearsheetConfig

create_tearsheet(
    engine=engine,
    output_path="backtest_results.html",
    config=TearsheetConfig(theme="nautilus_dark"),
)

report = engine.trader.generate_account_report(SIM)
print("\n=== ACCOUNT REPORT ===")
print(report.to_string(index=True))

positions = engine.trader.generate_positions_report()
print("\n=== POSITIONS REPORT ===")
print(positions.to_string(index=True))

fills = engine.trader.generate_order_fills_report()
print("\n=== ORDER FILLS REPORT ===")
print(fills.to_string(index=True))

print(f"\n{'='*50}")
print(f"Start balance: ${report.iloc[0]['total']}")
print(f"End balance:   ${report.iloc[-1]['total']}")
print(f"Total trades: {len(positions)}")
print(f"{'='*50}\n")

engine.dispose()
