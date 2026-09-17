from abc import ABC, abstractmethod
from typing import List, Optional

from core import CandleList, Side, Position, PointPosition

class TradingControl(ABC):
    def __init__(
        self,
        candle_list: CandleList,
        balance_initial: float = 100.0,
        risk_per_position_pct: float = 1.0,
        leverage_max: float = 5.0,
        risk_from_peak_balance: bool = False,
        commission_rate: float = 0.00025,
        symbol: str = "BTCUSDT",
    ):
        self.balance: float = balance_initial
        self.balance_peak: float = balance_initial
        self.position_list: List[PointPosition] = []
        self.candle_list: CandleList = candle_list
        self.risk_per_position_pct: float = risk_per_position_pct
        self.leverage_max: float = leverage_max
        self.position: Optional[Position] = None
        self.risk_from_peak_balance: bool = risk_from_peak_balance
        self.commission_rate: float = commission_rate
        self.symbol: str = symbol

    @abstractmethod
    def position_open(
        self,
        side: Side,
        stop_loss_price: float,
    ) -> Position | None:
        pass
    
    @abstractmethod
    def position_close(self, stop_loss: bool = False) -> Position | None:
        pass
    
    @abstractmethod
    def stop_loss_set(self, stop_loss_price: float) -> Position | None:
        pass

    @abstractmethod
    def candle_check(self):
        pass
