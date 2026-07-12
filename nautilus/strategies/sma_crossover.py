from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators import SimpleMovingAverage
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy


class SMACrossConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal
    fast_sma_period: int = 10
    slow_sma_period: int = 20
    order_type: str = "market"
    limit_offset_ticks: int = 5

    @classmethod
    def config_schema(cls) -> dict:
        return {
            "name": "sma_crossover",
            "label": "SMA Crossover",
            "params": {
                "fast_sma_period": {
                    "type": "int", "label": "Fast SMA Period",
                    "default": 10, "min": 2, "max": 200,
                },
                "slow_sma_period": {
                    "type": "int", "label": "Slow SMA Period",
                    "default": 20, "min": 5, "max": 500,
                },
                "trade_size": {
                    "type": "float", "label": "Trade Size (USD)",
                    "default": 100000.0, "min": 1.0,
                },
                "order_type": {
                    "type": "select", "label": "Order Type",
                    "options": ["market", "limit"], "default": "market",
                },
                "limit_offset_ticks": {
                    "type": "int", "label": "Limit Offset Ticks",
                    "default": 5, "min": 1, "max": 100,
                },
            },
        }


class SMACross(Strategy):
    def __init__(self, config: SMACrossConfig):
        super().__init__(config)
        self.fast_sma = SimpleMovingAverage(config.fast_sma_period)
        self.slow_sma = SimpleMovingAverage(config.slow_sma_period)

    def on_start(self):
        self.register_indicator_for_bars(self.config.bar_type, self.fast_sma)
        self.register_indicator_for_bars(self.config.bar_type, self.slow_sma)
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar):
        if not self.indicators_initialized():
            return

        if self.fast_sma.value >= self.slow_sma.value:
            if self.portfolio.is_flat(self.config.instrument_id):
                self.enter_long(bar)
            elif self.portfolio.is_net_short(self.config.instrument_id):
                self.close_all_positions(self.config.instrument_id)
                self.enter_long(bar)
        else:
            if self.portfolio.is_flat(self.config.instrument_id):
                self.enter_short(bar)
            elif self.portfolio.is_net_long(self.config.instrument_id):
                self.close_all_positions(self.config.instrument_id)
                self.enter_short(bar)

    def enter_long(self, bar: Bar):
        instrument = self.cache.instrument(self.config.instrument_id)
        if self.config.order_type == "limit":
            tick_size = instrument.price_increment
            limit_price = bar.close - tick_size * self.config.limit_offset_ticks
            if limit_price.as_double() <= 0:
                limit_price = tick_size
            order = self.order_factory.limit(
                self.config.instrument_id,
                OrderSide.BUY,
                instrument.make_qty(self.config.trade_size),
                limit_price,
                time_in_force=TimeInForce.GTC,
            )
        else:
            order = self.order_factory.market(
                self.config.instrument_id,
                OrderSide.BUY,
                instrument.make_qty(self.config.trade_size),
            )
        self.submit_order(order)

    def enter_short(self, bar: Bar):
        instrument = self.cache.instrument(self.config.instrument_id)
        if self.config.order_type == "limit":
            tick_size = instrument.price_increment
            limit_price = bar.close + tick_size * self.config.limit_offset_ticks
            order = self.order_factory.limit(
                self.config.instrument_id,
                OrderSide.SELL,
                instrument.make_qty(self.config.trade_size),
                limit_price,
                time_in_force=TimeInForce.GTC,
            )
        else:
            order = self.order_factory.market(
                self.config.instrument_id,
                OrderSide.SELL,
                instrument.make_qty(self.config.trade_size),
            )
        self.submit_order(order)

    def on_stop(self):
        self.close_all_positions(self.config.instrument_id)
