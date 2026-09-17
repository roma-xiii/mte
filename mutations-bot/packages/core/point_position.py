import msgspec
from datetime import datetime
from typing import Optional

from position import Position


class PointPosition(msgspec.Struct):
    position: Position
    balance_after: Optional[float] = None
    profit: Optional[float] = None
    commission: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    closed_by_stop_loss: bool = False
