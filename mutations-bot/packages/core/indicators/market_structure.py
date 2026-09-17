import msgspec
from typing import Literal, Optional, List
from core import CandleList
from side import Side


class Impulse(msgspec.Struct):
    type: Side
    low_price: Optional[float] = None
    low_id: Optional[int] = None
    high_price: Optional[float] = None
    high_id: Optional[int] = None

    def update_low(self, price: float, id: int):
        self.low_price = price
        self.low_id = id

    def update_high(self, price: float, id: int):
        self.high_price = price
        self.high_id = id


class PriceStructureElement(msgspec.Struct):
    id: int
    type: Literal['high', 'low']
    price: float
    label: Literal['HH', 'HL', 'LH', 'LL', 'CHoCH']


class PriceLevel(msgspec.Struct):
    price: float
    id: int


class MarketStructureIndicator(msgspec.Struct):
    candle_list: CandleList
    trend: Optional[str] = None
    last_hh: Optional[PriceLevel] = None
    last_hl: Optional[PriceLevel] = None
    last_lh: Optional[PriceLevel] = None
    last_ll: Optional[PriceLevel] = None
    structure_list: List[PriceStructureElement] = [] 
    impulse: Optional[Impulse] = None

    def check_pivot(self):
        # Проверяем, можно ли подтвердить pivot на предыдущей свече
        if len(self.candle_list.list) < 3:
            return

        # Свечи: -3 (left), -2 (potential pivot), -1 (right = current)
        candle_left = self.candle_list.list[-3]
        candle_pivot = self.candle_list.list[-2]
        candle_right = self.candle_list.list[-1]

        is_swing_high = candle_pivot.high > candle_left.high and candle_pivot.high > candle_right.high
        is_swing_low = candle_pivot.low < candle_left.low and candle_pivot.low < candle_right.low

        if is_swing_high:
            candle_pivot.swing_type_set('high')
            self._process_swing(candle_pivot.id, 'high', candle_pivot.high)
        
        elif is_swing_low:
            candle_pivot.swing_type_set('low')  
            self._process_swing(candle_pivot.id, 'low', candle_pivot.low)

    def _process_swing(self, candle_id, swing_type, price):
        label = None

        if swing_type == 'low':
            if self.trend in [None, 'long']:
                hl_needs_update = self.last_hl is None or price > self.last_hl.price
                if hl_needs_update:
                    label = 'HL'
                    self.last_hl = PriceLevel(id=candle_id, price=price)
                    
                    if self.trend is None:
                        self.trend = 'long'
                    
                    impulse_exists = self.impulse and self.impulse.type == 'long'
                    if impulse_exists:
                        self.impulse.update_low(price, candle_id)
                    else:
                        self.impulse = Impulse(
                            type='long',
                            low_price=price,
                            low_id=candle_id,
                        )
                else:
                    label = 'CHoCH'
                    self.trend = 'short'
                    self.last_ll = PriceLevel(id=candle_id, price=price)
                    self.last_hl = self.last_hh = None
                    self.impulse = Impulse(
                        type='short',
                        low_price=price,
                        low_id=candle_id,
                        high_price=self.last_lh.price if self.last_lh else price,
                        high_id=self.last_lh.id if self.last_lh else candle_id,
                    )

            elif self.trend == 'short':
                if self.last_ll is None or price < self.last_ll.price:
                    label = 'LL'
                    self.last_ll = PriceLevel(id=candle_id, price=price)
                    if self.impulse and self.impulse.type == 'short':
                        self.impulse.update_low(price, candle_id)
                else:
                    label = 'HL'  # weakening

        elif swing_type == 'high':
            if self.trend in [None, 'short']:
                lh_needs_update = self.last_lh is None or price < self.last_lh.price
                if lh_needs_update:
                    label = 'LH'
                    self.last_lh = PriceLevel(id=candle_id, price=price)
                    if self.trend is None:
                        self.trend = 'short'
                    if self.impulse and self.impulse.type == 'short':
                        self.impulse.update_high(price, candle_id)
                    else:
                        self.impulse = Impulse(
                            type='short',
                            high_price=price,
                            high_id=candle_id,
                        )
                else:
                    label = 'CHoCH'
                    self.trend = 'long'
                    self.last_hh = PriceLevel(id=candle_id, price=price)
                    self.last_ll = self.last_lh = None
                    self.impulse = Impulse(
                        type='long',
                        high_price=price,
                        high_id=candle_id,
                        low_price=self.last_hl.price if self.last_hl else price,
                        low_id=self.last_hl.id if self.last_hl else candle_id,
                    )
            elif self.trend == 'long':
                if self.last_hh is None or price > self.last_hh.price:
                    label = 'HH'
                    self.last_hh = PriceLevel(id=candle_id, price=price)
                    if self.impulse and self.impulse.type == 'long':
                        self.impulse.update_high(price, candle_id)
                else:
                    label = 'LH'  # weakening

        if label:
            self.structure_list.append(
                PriceStructureElement(
                    id=candle_id,
                    type=swing_type,
                    price=price,
                    label=label,
                ),
            )
