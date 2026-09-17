import os

from core import Side, Position
from trading_control import TradingControl
from exchanges import ClientTradingBingx


class TradingControlBingx(TradingControl):
    def __init__(
        self,
        candle_list,
        balance_initial: float = 100.0,
        risk_per_position_pct: float = 1.0,
        leverage_max: float = 5.0,
        risk_from_peak_balance: bool = False,
        commission_rate: float = 0.00025,
        symbol: str = "DOGEUSDT",
        mode_demo: bool = True,
    ):
        super().__init__(
            candle_list,
            balance_initial,
            risk_per_position_pct,
            leverage_max,
            risk_from_peak_balance,
            commission_rate,
            symbol,
        )

        api_key = os.getenv("BINGX_API_KEY")
        api_secret = os.getenv("BINGX_API_SECRET")
        if not api_key or not api_secret:
            raise ValueError(
                "BINGX_API_KEY and BINGX_API_SECRET must be set in environment"
            )
        self._client = ClientTradingBingx(api_key, api_secret, mode_demo=mode_demo)

    def position_open(
        self,
        side: Side,
        stop_loss_price: float,
    ) -> Position | None:
        if len(self.candle_list.list) == 0 or self.position != None:
            return None
        
        candle = self.candle_list.list[-1]
        entry_price = candle.close
        
        if side == 'long':
            stop_distance = entry_price - stop_loss_price
            if stop_distance <= 0:
                return None
            
            risk_basis_equity = self.balance_peak if self.risk_from_peak_balance else self.balance
            risk_usdt = risk_basis_equity * (self.risk_per_position_pct / 100.0)
            if risk_usdt <= 0:
                return None
            position_size_raw = risk_usdt / stop_distance
            # Ограничение по максимальному плечу через notional (от текущего equity)
            max_notional = self.balance * self.leverage_max
            notional_raw = position_size_raw * entry_price
            if notional_raw > max_notional:
                position_size = max_notional / entry_price
            else:
                position_size = position_size_raw
            # leverage_used = (position_size * entry_price) / self.balance if self.balance > 0 else 0.0

            position = self._client.position_open(
                symbol=self.symbol,
                side=side,
                size=position_size,
                stop_loss_price=stop_loss_price,
            )

            self.position = position

            return position
        
        elif side == 'short':
            stop_distance = stop_loss_price - entry_price
            if stop_distance <= 0:
                return None
            risk_basis_equity = self.balance_peak if self.risk_from_peak_balance else self.balance
            risk_usdt = risk_basis_equity * (self.risk_per_position_pct / 100.0)
            if risk_usdt <= 0:
                return None
            position_size_raw = risk_usdt / stop_distance
            max_notional = self.balance * self.leverage_max
            notional_raw = position_size_raw * entry_price
            if notional_raw > max_notional:
                position_size = max_notional / entry_price
            else:
                position_size = position_size_raw
            # leverage_used = (position_size * entry_price) / self.balance if self.balance > 0 else 0.0
            
            position = self._client.position_open(
                symbol=self.symbol,
                side=side,
                size=position_size,
                stop_loss_price=stop_loss_price,
            )

            self.position = position

            return position

    def position_close(self, stop_loss: bool = False) -> Position | None:
        if len(self.candle_list.list) == 0 or self.position is None:
            return None
        
        candle = self.candle_list.list[-1]

        direction = 1 if self.position.side == 'long' else -1
        exit_price = self.position.stop_loss_price if stop_loss else candle.close
        commission = self.commission_rate * (self.position.entry_price + exit_price) * self.position.size
        profit_gross = (exit_price - self.position.entry_price) * direction * self.position.size
        profit = profit_gross - commission
        self.balance += profit
        self.balance_peak = max(self.balance_peak, self.balance)

        position = self._client.position_close(self.position)
        self.position = None

        return position
    
    def stop_loss_set(self, stop_loss_price: float) -> Position | None:
        if self.position is None:
            return None

        position = self._client.stop_loss_update(self.position, stop_loss_price)

        if position is None:
            return None

        self.position = position
        return position

    def candle_check(self):
        if self.position is None or len(self.candle_list.list) == 0:
            return

        candle = self.candle_list.list[-1]

        needs_close_long = self.position.side == 'long' and candle.low <= self.position.stop_loss_price
        needs_close_short = self.position.side == 'short' and candle.high >= self.position.stop_loss_price

        if needs_close_long or needs_close_short:
            self.position_close(stop_loss=True)
