from core import Side, Position, PointPosition
from trading_control import TradingControl



class TradingControlPaper(TradingControl):
    def __init__(
        self,
        candle_list,
        balance_initial: float = 100.0,
        risk_per_position_pct: float = 1.0,
        leverage_max: float = 5.0,
        risk_from_peak_balance: bool = False,
        commission_rate: float = 0.00025,
        symbol: str = "DOGEUSDT",
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

    def position_open(
        self,
        side: Side,
        stop_loss_price: float,
    ):
        if len(self.candle_list.list) == 0 or self.position != None:
            return
        
        candle = self.candle_list.list[-1]
        entry_price = candle.close
        
        if side == 'long':
            stop_distance = entry_price - stop_loss_price
            if stop_distance <= 0:
                return
            
            risk_basis_equity = self.balance_peak if self.risk_from_peak_balance else self.balance
            risk_usdt = risk_basis_equity * (self.risk_per_position_pct / 100.0)
            if risk_usdt <= 0:
                return
            position_size_raw = risk_usdt / stop_distance
            # Ограничение по максимальному плечу через notional (от текущего equity)
            max_notional = self.balance * self.leverage_max
            notional_raw = position_size_raw * entry_price
            if notional_raw > max_notional:
                position_size = max_notional / entry_price
            else:
                position_size = position_size_raw
            self.position = Position(
                side='long',
                id=candle.id,
                symbol="PAPER",
                entry_price=entry_price,
                entry_time=candle.open_time,
                stop_loss_price=stop_loss_price,
                size=position_size,
            )
        
        elif side == 'short':
            stop_distance = stop_loss_price - entry_price
            if stop_distance <= 0:
                return
            risk_basis_equity = self.balance_peak if self.risk_from_peak_balance else self.balance
            risk_usdt = risk_basis_equity * (self.risk_per_position_pct / 100.0)
            if risk_usdt <= 0:
                return
            position_size_raw = risk_usdt / stop_distance
            max_notional = self.balance * self.leverage_max
            notional_raw = position_size_raw * entry_price
            if notional_raw > max_notional:
                position_size = max_notional / entry_price
            else:
                position_size = position_size_raw
            self.position = Position(
                side='short',
                id=candle.id,
                symbol="PAPER",
                entry_price=entry_price,
                entry_time=candle.open_time,
                stop_loss_price=stop_loss_price,
                size=position_size,
            )

    def position_close(self, stop_loss: bool = False):
        if len(self.candle_list.list) == 0 or self.position is None:
            return
        
        candle = self.candle_list.list[-1]

        direction = 1 if self.position.side == 'long' else -1
        exit_price = self.position.stop_loss_price if stop_loss else candle.close
        commission = self.commission_rate * (self.position.entry_price + exit_price) * self.position.size
        profit_gross = (exit_price - self.position.entry_price) * direction * self.position.size
        profit = profit_gross - commission
        self.balance += profit
        self.balance_peak = max(self.balance_peak, self.balance)

        point_position = PointPosition(
            position=self.position,
            balance_after=round(self.balance, 2),
            profit=round(profit, 2),
            commission=round(commission, 2),
            exit_time=candle.open_time,
            exit_price=exit_price,
            closed_by_stop_loss=stop_loss,
        )

        self.position_list.append(point_position)
        self.position = None
    
    def stop_loss_set(self, stop_loss_price: float):
        if self.position is None:
            return
        self.position.stop_loss_price = stop_loss_price

    def candle_check(self):
        if self.position is None or len(self.candle_list.list) == 0:
            return

        candle = self.candle_list.list[-1]

        needs_close_long = self.position.side == 'long' and candle.low <= self.position.stop_loss_price
        needs_close_short = self.position.side == 'short' and candle.high >= self.position.stop_loss_price

        if needs_close_long or needs_close_short:
            self.position_close(True)
