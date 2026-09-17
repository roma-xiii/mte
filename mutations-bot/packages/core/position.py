import msgspec
from datetime import datetime
from typing import Optional

from side import Side


# class Position(msgspec.Struct):
#     side: Side
#     id: int
#     symbol: str
#     entry_price: float
#     position_size: float
#     stop_loss_price: float
#     entry_time: datetime
#     leverage: float
#     stop_loss_order_id: Optional[int] = None
#     commission: Optional[float] = None
#     exit_price: Optional[float] = None
#     exit_time: Optional[datetime] = None
#     exit_id: Optional[int] = None
#     profit: Optional[float] = None
#     balance_after: Optional[float] = None

#     def close(
#         self,
#         exit_id: int,
#         exit_time: datetime,
#         exit_price: float,
#         commission: float,
#         profit: float,
#         balance_after: float,
#     ):
#         self.exit_id = exit_id
#         self.exit_time = exit_time
#         self.exit_price = exit_price
#         self.commission = round(commission, 2)
#         self.profit = round(profit, 2)
#         self.balance_after = round(balance_after, 2)

class Position(msgspec.Struct):
    side: Side
    id: int
    symbol: str
    entry_time: datetime
    entry_price: float
    size: float
    stop_loss_price: float
    stop_loss_order_id: Optional[int] = None
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
