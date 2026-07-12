from pathlib import Path

import ccxt
import pandas as pd


_TIMEFRAMES = {
    "1m": "1m", "5m": "5m", "15m": "15m",
    "30m": "30m", "1h": "1h", "4h": "4h", "1d": "1d",
}

_QUOTES = ["USDT", "USDC", "BUSD", "USD", "BTC", "ETH", "BNB"]


def _to_ccxt_symbol(symbol: str) -> str:
    for quote in _QUOTES:
        if symbol.endswith(quote) and len(symbol) > len(quote):
            return f"{symbol[:-len(quote)]}/{quote}"
    return symbol


def download_ohlcv(
    exchange_name: str,
    symbol: str,
    timeframe: str,
    date_from: str | None,
    date_to: str | None,
    data_dir: str | Path,
) -> str:
    exchange_class = getattr(ccxt, exchange_name.lower().replace(" ", ""))
    exchange = exchange_class()
    exchange.enableRateLimit = True

    ccxt_symbol = _to_ccxt_symbol(symbol)
    ccxt_tf = _TIMEFRAMES.get(timeframe, "1m")

    since = exchange.parse8601(f"{date_from}T00:00:00Z") if date_from else None
    until = exchange.parse8601(f"{date_to}T00:00:00Z") if date_to else exchange.milliseconds()

    all_ohlcv = []
    limit = 1000

    while True:
        ohlcv = exchange.fetch_ohlcv(ccxt_symbol, ccxt_tf, since=since, limit=limit)
        if not ohlcv:
            break

        all_ohlcv.extend(ohlcv)
        since = ohlcv[-1][0] + 1

        if ohlcv[-1][0] >= until:
            break

        if len(ohlcv) < limit:
            break

    df = pd.DataFrame(all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)

    if date_to:
        end_ts = pd.Timestamp(f"{date_to}T23:59:59", tz="UTC")
        df = df[df["timestamp"] <= end_ts]

    path = Path(data_dir) / f"{symbol}-{timeframe}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)

    return str(path)
