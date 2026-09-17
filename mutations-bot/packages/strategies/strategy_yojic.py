from typing import Optional, Literal
from trading_controls import TradingControl
from core import CandleList, PriceCandle, MarketStructureIndicator

Status = Literal['running', 'stopped']

class StrategyYojic:
    def __init__(
        self,
        candle_list: CandleList,
        trading_control: TradingControl,
    ):
        self.status: Status = 'stopped'
        self.candle_list: CandleList = candle_list
        self.structure: MarketStructureIndicator = MarketStructureIndicator(self.candle_list)
        self.trading_control: TradingControl = trading_control
        self.trailing_active: bool = False
        self.trailing_distance: Optional[float] = None
        self.impulse_extremum: Optional[float] = None
        self.candle_extremum: Optional[float] = None

    def _process_choch(self):
        if len(self.candle_list.list) == 0:
            return
        
        candle = self.candle_list.list[-1]
        
        is_choch = (self.structure.structure_list 
            and self.structure.structure_list[-1].id == candle.id - 1 
            and self.structure.structure_list[-1].label == 'CHoCH')
        
        if is_choch:
            self.trading_control.position_close()

    def _process_trailing_stop(self):
        if len(self.candle_list.list) == 0:
            return
        
        candle = self.candle_list.list[-1]

        if self.trading_control.position:
            if self.candle_extremum is None or self.impulse_extremum is None or self.trailing_distance is None:
                return
            if self.trading_control.position.side == 'long':

                self.candle_extremum = (max(self.candle_extremum, candle.high))

                if not self.trailing_active and candle.close > self.impulse_extremum:
                    self.trailing_active = True

                current_stop = self.trading_control.position.stop_loss_price
                if self.trailing_active:
                    trail_stop = self.candle_extremum - self.trailing_distance
                    if trail_stop > current_stop:
                        self.trading_control.stop_loss_set(trail_stop)

            elif self.trading_control.position.side == 'short':
                self.candle_extremum = (min(self.candle_extremum, candle.low))

                if not self.trailing_active and candle.close < self.impulse_extremum:
                    self.trailing_active = True

                current_stop = self.trading_control.position.stop_loss_price
                if self.trailing_active:
                    trail_stop = self.candle_extremum + self.trailing_distance
                    if trail_stop < current_stop:
                        self.trading_control.stop_loss_set(trail_stop)

    def _process_entry(self):
        if len(self.candle_list.list) == 0 or self.status != 'running':
            return
        
        candle = self.candle_list.list[-1]

        if not self.trading_control.position and self.structure.impulse:
            impulse = self.structure.impulse
            if impulse.low_id is None or impulse.high_price is None or impulse.low_price is None:
                return
            # Только после формирования импульса (i > индексы экстремумов)
            if (impulse.high_id is not None and candle.id <= impulse.high_id) or candle.id <= impulse.low_id:
                return

            if impulse.type == 'long':
                fib_05 = impulse.high_price - 0.5 * (impulse.high_price - impulse.low_price)
                if candle.low <= fib_05 and candle.close > fib_05:
                    # entry_price = candle.close
                    sl = impulse.low_price
                    # trailing_distance = 0.5 * (impulse.high_price - entry_price)

                    self.impulse_extremum = impulse.high_price
                    self.candle_extremum = candle.high
                    self.trailing_active = False
                    self.trailing_distance = 0.5 * (impulse.high_price - candle.close)
                    
                    self.trading_control.position_open('long', sl)

            elif impulse.type == 'short':
                fib_05 = impulse.low_price + 0.5 * (impulse.high_price - impulse.low_price)
                if candle.high >= fib_05 and candle.close < fib_05:
                    # entry_price = candle.close
                    sl = impulse.high_price
                    self.trailing_distance = 0.5 * (candle.close - impulse.low_price)
                    self.impulse_extremum=impulse.low_price
                    self.candle_extremum=candle.low
                    self.trailing_active = False
                    
                    self.trading_control.position_open('short', sl)

    def start(self):
        self.status = 'running'

    def stop(self):
        self.status = 'stopped'

    def stop_and_close(self):
        self.status = 'stopped'
        self.trading_control.position_close()
        self.impulse_extremum = None
        self.candle_extremum = None
        self.trailing_active = False

    def candle_new(self, candle: PriceCandle):
        self.candle_list.add(candle)
        self.structure.check_pivot()
        self._process_choch()
        self._process_trailing_stop()
        self.trading_control.candle_check()
        self._process_entry()
