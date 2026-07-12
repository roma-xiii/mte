from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators import SimpleMovingAverage
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.orders.list import OrderList
from nautilus_trader.trading.strategy import Strategy


class SMACrossConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal
    fast_sma_period: int = 10
    slow_sma_period: int = 20
    order_type: str = "market"
    limit_offset_ticks: int = 5
    tp_percent: float = 0.0
    sl_percent: float = 0.0

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
                "tp_percent": {
                    "type": "float", "label": "Take Profit (%)",
                    "default": 0.0, "min": 0.0, "max": 100.0,
                },
                "sl_percent": {
                    "type": "float", "label": "Stop Loss (%)",
                    "default": 0.0, "min": 0.0, "max": 100.0,
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

    def _send_order(self, side: OrderSide, entry_price: Decimal | None, bar: Bar):
        instrument = self.cache.instrument(self.config.instrument_id)
        qty = instrument.make_qty(self.config.trade_size)
        has_tp_sl = self.config.tp_percent > 0 or self.config.sl_percent > 0

        if has_tp_sl:
            entry = entry_price or bar.close
            tp_offset = entry * Decimal(str(self.config.tp_percent / 100))
            sl_offset = entry * Decimal(str(self.config.sl_percent / 100))

            if side == OrderSide.BUY:
                tp_price = instrument.make_price(entry + tp_offset) if self.config.tp_percent > 0 else None
                sl_trigger = instrument.make_price(entry - sl_offset) if self.config.sl_percent > 0 else None
            else:
                tp_price = instrument.make_price(entry - tp_offset) if self.config.tp_percent > 0 else None
                sl_trigger = instrument.make_price(entry + sl_offset) if self.config.sl_percent > 0 else None

            order_list: OrderList = self.order_factory.bracket(
                instrument_id=self.config.instrument_id,
                order_side=side,
                quantity=qty,
                time_in_force=TimeInForce.GTC,
                entry_order_type=OrderType.MARKET if self.config.order_type == "market" else OrderType.LIMIT,
                entry_price=entry_price,
                sl_trigger_price=sl_trigger,
                tp_price=tp_price,
            )
            self.submit_order_list(order_list)
        elif self.config.order_type == "limit" and entry_price is not None:
            order = self.order_factory.limit(
                self.config.instrument_id, side, qty, entry_price,
                time_in_force=TimeInForce.GTC,
            )
            self.submit_order(order)
        else:
            order = self.order_factory.market(
                self.config.instrument_id, side, qty,
            )
            self.submit_order(order)

    def enter_long(self, bar: Bar):
        instrument = self.cache.instrument(self.config.instrument_id)
        if self.config.order_type == "limit":
            tick_size = instrument.price_increment
            limit_price = bar.close - tick_size * self.config.limit_offset_ticks
            if limit_price.as_double() <= 0:
                limit_price = tick_size
            self._send_order(OrderSide.BUY, limit_price, bar)
        else:
            self._send_order(OrderSide.BUY, None, bar)

    def enter_short(self, bar: Bar):
        instrument = self.cache.instrument(self.config.instrument_id)
        if self.config.order_type == "limit":
            tick_size = instrument.price_increment
            limit_price = bar.close + tick_size * self.config.limit_offset_ticks
            self._send_order(OrderSide.SELL, limit_price, bar)
        else:
            self._send_order(OrderSide.SELL, None, bar)

    def on_stop(self):
        self.close_all_positions(self.config.instrument_id)
