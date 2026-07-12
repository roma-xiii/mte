import warnings
from decimal import Decimal
from pathlib import Path
import re
import os

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=pd.errors.ChainedAssignmentError)

from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.identifiers import InstrumentId, Venue
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


def load_bars(
    data_dir: str,
    instrument: str,
    timeframe: str,
) -> tuple:
    path = Path(data_dir) / f"{instrument}-{timeframe}.csv"
    df = pd.read_csv(path, parse_dates=["timestamp"], index_col="timestamp")
    df = df.sort_index()
    if df.tz is None:
        df.index = df.index.tz_localize("UTC")

    instrument_id = InstrumentId(f"{instrument}.SIM")
    venue = Venue("SIM")
    nautilus_instrument = TestInstrumentProvider.default_fx_ccy(
        f"{instrument[:3]}/{instrument[3:]}"
    )
    bar_type_str = f"{instrument}.SIM-{timeframe.upper()}-LAST-EXTERNAL"
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
    price = 1.10 + np.cumsum(rng.normal(0, 0.0002, n))
    spread = np.abs(rng.normal(0, 0.0003, n))

    num = timeframe[:-1]
    unit = timeframe[-1]
    pandas_freq = f"{num}{_TF_PANDAS[unit]}"

    bars_df = pd.DataFrame(
        {
            "open": price,
            "high": price + spread,
            "low": price - spread,
            "close": price + rng.normal(0, 0.00005, n),
        },
        index=pd.date_range(
            end=pd.Timestamp.now(tz="UTC"), periods=n, freq=pandas_freq, tz="UTC",
        ),
    )
    bars_df.loc[:, "high"] = bars_df[["open", "high", "close"]].max(axis=1)
    bars_df.loc[:, "low"] = bars_df[["open", "low", "close"]].min(axis=1)

    nautilus_instrument = TestInstrumentProvider.default_fx_ccy(instrument_id_str)
    inst_id = str(nautilus_instrument.id)
    bar_type_str = f"{inst_id}-{num}-{_TF_NAUTILUS[unit]}-LAST-EXTERNAL"
    bar_type = BarType.from_str(bar_type_str)

    bars = BarDataWrangler(bar_type, nautilus_instrument).process(bars_df)
    return nautilus_instrument, bar_type, bars
