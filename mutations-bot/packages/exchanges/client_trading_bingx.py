import requests
import time
import hmac
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from core import Side, Position


BINGX_MAIN_URL = "https://open-api.bingx.com"
BINGX_TEST_URL = "https://open-api-vst.bingx.com"

class ClientTradingBingx:
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        mode_demo: bool = True,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = BINGX_TEST_URL if mode_demo else BINGX_MAIN_URL
        self.time_offset = 0

    def _to_bingx_symbol(self, symbol: str) -> str:
        return symbol.replace("USDT", "-USDT")
    
    def _sign(self, query: str) -> str:
        return hmac.new(self.api_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()

    def _parseParam(self, paramsMap: dict) -> str:
        sortedKeys = sorted(paramsMap)
        paramsStr = "&".join(f"{k}={paramsMap[k]}" for k in sortedKeys)
        timestamp = str(int(time.time() * 1000) + self.time_offset)
        if paramsStr:
            return f"{paramsStr}&timestamp={timestamp}"
        return f"timestamp={timestamp}"
    
    def _send_request(self, method: str, path: str, params: dict):
        query = self._parseParam(params)
        sign = self._sign(query)
        url = f"{self.base_url}{path}?{query}&signature={sign}"
        headers = {'X-BX-APIKEY': self.api_key}
        response = requests.request(method, url, headers=headers)
        try:
            return response.json()
        except Exception as e:
            print(f"JSON parse error: {e}, response: {response.text}")
            return None
    
    def _side_to_bingx(self, side: Side) -> str:
        return "BUY" if side == "long" else "SELL"
    
    def _position_side_to_bingx(self, side: Side) -> str:
        return "LONG" if side == "long" else "SHORT"
    
    def position_open(
        self,
        symbol: str,
        side: Side,
        size: float,
        stop_loss_price: float,
        take_profit_price: Optional[float] = None,
    ) -> Position | None:
        params = {
            "symbol": self._to_bingx_symbol(symbol),
            "side": self._side_to_bingx(side),
            "positionSide": self._position_side_to_bingx(side),
            "type": "MARKET",
            "quantity": size,
            "recvWindow": 5000,
        }
        if stop_loss_price is not None:
            params["stopLoss"] = json.dumps({
                "type": "STOP_MARKET",
                "stopPrice": stop_loss_price,
                "workingType": "MARK_PRICE"
            })
        if take_profit_price is not None:
            params["takeProfit"] = json.dumps({
                "type": "TAKE_PROFIT_MARKET",
                "stopPrice": take_profit_price,
                "workingType": "MARK_PRICE"
            })

        response = self._send_request("POST", "/openApi/swap/v2/trade/order", params)
        if not response or response.get("code") != 0:
            return None

        order = response.get("data", {}).get("order", {})
        executed_qty = float(order.get("executedQty") or size)

        orders_resp = self.positions_list(symbol)
        orders = (orders_resp.get("data") or {}).get("orders") or []
        stop_order = next(
            (
                o for o in orders
                if o.get("positionSide") == self._position_side_to_bingx(side)
                and o.get("reduceOnly") is True
            ),
            {},
        )

        position_id = stop_order.get("positionID", 0)

        print(
            "OPEN",
            symbol,
            side,
            "size: " + str(executed_qty),
            "entry_price: " + str(float(order.get("avgPrice") or 0)),
            "stop_loss_price: " + str(stop_loss_price),
        )

        return Position(
            side=side,
            id=position_id,
            symbol=symbol,
            entry_price=float(order.get("avgPrice") or 0),
            size=executed_qty,
            stop_loss_price=stop_loss_price,
            entry_time=datetime.now(),
            stop_loss_order_id=stop_order.get("orderId", 0),
        )

    def positions_list(self, symbol: str) -> Any | None:
        params = {}
        if symbol:
            params["symbol"] = self._to_bingx_symbol(symbol)
        return self._send_request("GET", "/openApi/swap/v2/trade/openOrders", params)

    def stop_loss_update(
        self,
        position: Position,
        new_stop_loss_price: float,
    ) -> Position | None:
        # Сначала создаём новый SL — если не получится, старый останется
        close_side = "SELL" if position.side == "long" else "BUY"
        response = self._send_request(
            "POST",
            "/openApi/swap/v2/trade/order",
            {
                "symbol": self._to_bingx_symbol(position.symbol),
                "side": close_side,
                "positionSide": self._position_side_to_bingx(position.side),
                "type": "STOP_MARKET",
                "stopPrice": new_stop_loss_price,
                "quantity": position.size,
                "workingType": "MARK_PRICE",
                "recvWindow": 5000,
            },
        )

        if not response or response.get("code") != 0:
            print("SL UPDATE FAILED:", response)
            return None

        order = response.get("data", {}).get("order", {})
        new_stop_loss_order_id = order.get("orderId", 0)

        # Удаляем старый SL
        self._send_request(
            "DELETE",
            "/openApi/swap/v2/trade/order",
            {"orderId": position.stop_loss_order_id, "symbol": self._to_bingx_symbol(position.symbol)},
        )

        print(
            "SL UPDATE",
            position.symbol,
            position.side,
            "size: " + str(position.size),
            "entry_price: " + str(position.entry_price),
            "stop_loss_price: " + str(new_stop_loss_price),
        )

        return Position(
            side=position.side,
            id=position.id,
            symbol=position.symbol,
            entry_price=position.entry_price,
            size=position.size,
            stop_loss_price=new_stop_loss_price,
            entry_time=position.entry_time,
            stop_loss_order_id=new_stop_loss_order_id,
        )


    def position_close(self, position: Position) -> Optional[Position]:
        close_side = "SELL" if position.side == "long" else "BUY"
        response = self._send_request(
            "POST",
            "/openApi/swap/v2/trade/order",
            {
                "symbol": self._to_bingx_symbol(position.symbol),
                "side": close_side,
                "positionSide": self._position_side_to_bingx(position.side),
                "type": "MARKET",
                "quantity": position.size,
                "recvWindow": 5000,
            },
        )

        if not response or response.get("code") != 0:
            return None

        order = response.get("data", {}).get("order", {})
        exit_price = float(order.get("avgPrice") or 0)

        print(
            "CLOSE",
            position.symbol,
            position.side,
            "size: " + str(position.size),
            "entry_price: " + str(position.entry_price),
            "exit_price: " + str(exit_price),
        )

        return Position(
            side=position.side,
            id=position.id,
            symbol=position.symbol,
            entry_price=position.entry_price,
            size=position.size,
            stop_loss_price=position.stop_loss_price,
            entry_time=position.entry_time,
            stop_loss_order_id=position.stop_loss_order_id,
            exit_time=datetime.now(),
            exit_price=exit_price,
        )