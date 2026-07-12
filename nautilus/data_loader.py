import warnings
from decimal import Decimal
from pathlib import Path
import re
import os

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=pd.errors.ChainedAssignmentError)

from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments import CurrencyPair
from nautilus_trader.model.objects import Currency, Price, Quantity
from nautilus_trader.persistence.wranglers import BarDataWrangler
from nautilus_trader.test_kit.providers import TestInstrumentProvider


FILE_PATTERN = re.compile(r"^(\w+)-(\d+[smhd])\.csv$")


def get_csv_metadata(filepath: Path) -> dict:
    df = pd.read_csv(filepath, usecols=["timestamp"], parse_dates=["timestamp"])
    return {
        "bars": len(df),
        "date_from": str(df["timestamp"].iloc[0]),
        "date_to": str(df["timestamp"].iloc[-1]),
    }


def list_available_instruments(data_dir: str) -> list[dict]:
    path = Path(data_dir)
    if not path.exists():
        return []
    result = []
    for f in sorted(path.iterdir()):
        m = FILE_PATTERN.match(f.name)
        if m:
            entry = {
                "instrument": m.group(1),
                "timeframe": m.group(2),
                "file": f.name,
            }
            try:
                meta = get_csv_metadata(path / f.name)
                entry.update(meta)
            except Exception:
                pass
            result.append(entry)
    return result


_CRYPTO_QUOTES = {"USDT", "USDC", "BUSD", "DAI"}

_FX_BASE_PRICES = {
    "EUR/USD": 1.10,
    "GBP/USD": 1.25,
    "AUD/USD": 0.65,
    "NZD/USD": 0.60,
    "USD/JPY": 150.0,
    "USD/CAD": 1.35,
    "USD/CHF": 0.90,
}


def _make_crypto_instrument(instrument_id_str: str) -> tuple[CurrencyPair, float]:
    base, quote = instrument_id_str.split("/")
    sym = instrument_id_str.replace("/", "")
    instrument_id = InstrumentId(Symbol(sym), Venue("SIM"))

    if base == "BTC":
        base_price = 50000.0
    elif base == "ETH":
        base_price = 3000.0
    else:
        base_price = 100.0

    return CurrencyPair(
        instrument_id=instrument_id,
        raw_symbol=Symbol(sym),
        base_currency=Currency.from_str(base),
        quote_currency=Currency.from_str(quote),
        price_precision=2,
        size_precision=6,
        price_increment=Price(0.01, precision=2),
        size_increment=Quantity(1e-06, precision=6),
        lot_size=None,
        max_quantity=Quantity(9000, precision=6),
        min_quantity=Quantity(1e-06, precision=6),
        max_notional=None,
        min_notional=None,
        max_price=Price(1000000, precision=2),
        min_price=Price(0.01, precision=2),
        margin_init=Decimal(0),
        margin_maint=Decimal(0),
        maker_fee=Decimal("0.001"),
        taker_fee=Decimal("0.001"),
        ts_event=0,
        ts_init=0,
    ), base_price


def _make_fx_instrument(instrument_id_str: str) -> tuple[CurrencyPair, float]:
    base_price = _FX_BASE_PRICES.get(instrument_id_str, 1.10)
    instrument = TestInstrumentProvider.default_fx_ccy(instrument_id_str)
    return instrument, base_price


def _create_instrument(instrument_id_str: str) -> tuple[CurrencyPair, float]:
    try:
        base, quote = instrument_id_str.split("/")
    except ValueError:
        return _make_fx_instrument("EUR/USD")

    if quote in _CRYPTO_QUOTES:
        return _make_crypto_instrument(instrument_id_str)

    return _make_fx_instrument(instrument_id_str)


def load_bars(
    data_dir: str,
    instrument: str,
    timeframe: str,
) -> tuple:
    path = Path(data_dir) / f"{instrument}-{timeframe}.csv"
    df = pd.read_csv(path, parse_dates=["timestamp"], index_col="timestamp")
    df = df.sort_index()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")

    instrument_id_str = f"{instrument[:3]}/{instrument[3:]}"
    nautilus_instrument, _ = _create_instrument(instrument_id_str)
    inst_id = str(nautilus_instrument.id)
    num = timeframe[:-1]
    unit = timeframe[-1]
    bar_type_str = f"{inst_id}-{num}-{_TF_NAUTILUS[unit]}-LAST-EXTERNAL"
    bar_type = BarType.from_str(bar_type_str)

    bars = BarDataWrangler(bar_type, nautilus_instrument).process(df)
    return nautilus_instrument, bar_type, bars


_TF_PANDAS = {"m": "min", "h": "h", "d": "D"}
_TF_NAUTILUS = {"m": "MINUTE", "h": "HOUR", "d": "DAY"}


def generate_synthetic_bars(
    n: int = 10_000,
    seed: int = 42,
    instrument_id_str: str = "EUR/USD",
    timeframe: str = "1m",
) -> tuple:
    rng = np.random.default_rng(seed)

    nautilus_instrument, base_price = _create_instrument(instrument_id_str)

    rel_trend = 0.03
    rel_noise_scale = 0.0005
    half = max(n // 2, 1)
    trend = np.concatenate([
        np.linspace(0, rel_trend * base_price, half),
        np.linspace(rel_trend * base_price, -rel_trend * base_price, n - half),
    ])
    noise = rng.normal(0, rel_noise_scale * base_price, n).cumsum() * 0.1
    price = base_price + trend + noise
    spread = np.abs(rng.normal(0, 0.0003 * base_price, n))

    num = timeframe[:-1]
    unit = timeframe[-1]
    pandas_freq = f"{num}{_TF_PANDAS[unit]}"

    bars_df = pd.DataFrame(
        {
            "open": price,
            "high": price + spread,
            "low": price - spread,
            "close": price + rng.normal(0, 0.00005 * base_price, n),
        },
        index=pd.date_range(
            end=pd.Timestamp.now(tz="UTC"), periods=n, freq=pandas_freq, tz="UTC",
        ),
    )
    bars_df.loc[:, "high"] = bars_df[["open", "high", "close"]].max(axis=1)
    bars_df.loc[:, "low"] = bars_df[["open", "low", "close"]].min(axis=1)

    inst_id = str(nautilus_instrument.id)
    bar_type_str = f"{inst_id}-{num}-{_TF_NAUTILUS[unit]}-LAST-EXTERNAL"
    bar_type = BarType.from_str(bar_type_str)

    bars = BarDataWrangler(bar_type, nautilus_instrument).process(bars_df)
    return nautilus_instrument, bar_type, bars
