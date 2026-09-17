from typing import List
from binance.client import Client
import time
import pandas as pd
from core import PriceCandle

def klines_binance_fetch(
    symbol,
    interval,
    total_bars=20000,
    client=None,
) -> List[PriceCandle]:
    if client is None:
        client = Client()
    
    limit = 1000
    data = []
    end_time = int(time.time() * 1000)

    while len(data) < total_bars:
        bars_to_fetch = min(limit, total_bars - len(data))
        klines = client.futures_klines(
            symbol=symbol,
            interval=interval,
            limit=bars_to_fetch,
            endTime=end_time
        )
        if not klines:
            break
        data = klines + data
        end_time = klines[0][0] - 1

    df = pd.DataFrame(data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    df[['open','high','low','close']] = df[['open','high','low','close']].astype(float)
    df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
    df.set_index('timestamp', inplace=True)  # удобно для plotting
    
    klines: List[PriceCandle] = []
    
    for open_time, row in df.iterrows():
        candle = PriceCandle(
            id=df.index.get_loc(open_time),
            open=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            open_time=open_time
        )

        klines.append(candle)

    print(f"Fetched {len(klines)} candles")

    return klines
