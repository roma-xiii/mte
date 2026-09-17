import msgspec
from typing import Optional, List
from datetime import datetime
from side import Side


class PriceCandle(msgspec.Struct):
    id: int
    high: float
    low: float
    open: float
    close: float
    open_time: datetime
    swing_type: Optional[Side] = None

    def swing_type_set(self, swing_type: Side):
        self.swing_type = swing_type


class CandleList(msgspec.Struct):
    list: List[PriceCandle] = []
    def add(self, candle: PriceCandle):
        self.list.append(candle)
