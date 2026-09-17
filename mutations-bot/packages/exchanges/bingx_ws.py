"""BingX WebSocket kline stream."""

import asyncio
import gzip
import json
import logging
from datetime import datetime, timezone
from typing import Callable, Optional, Union

import websockets

BINGX_WS_URL = "wss://open-api-swap.bingx.com/swap-market"

logger = logging.getLogger(__name__)


class KlineStream:
    def __init__(
        self,
        symbol: str = "SOL-USDT",
        interval: str = "15m",
        on_candle: Optional[Callable] = None,
        reconnect_delay: float = 5.0,
        max_reconnect_delay: float = 60.0,
    ):
        self.symbol = symbol
        self.interval = interval
        self.on_candle = on_candle
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay

        self.data_type = f"{symbol}@kline_{interval}"
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._candle_seq = 0

        # Tracking for forming candle
        self._current_open_time: Optional[int] = None
        self._current_raw: Optional[dict] = None

    async def run(self):
        self._running = True
        delay = self.reconnect_delay

        while self._running:
            try:
                async with websockets.connect(BINGX_WS_URL) as ws:
                    self._ws = ws
                    logger.info("Connected to BingX WS: %s", self.data_type)
                    delay = self.reconnect_delay

                    await self._subscribe(ws)
                    await self._listen(ws)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(
                    "WS error: %s. Reconnect in %.1fs...", e, delay
                )

            if self._running:
                await asyncio.sleep(delay)
                delay = min(delay * 2, self.max_reconnect_delay)

        self._ws = None

    async def stop(self):
        self._running = False
        if self._ws:
            await self._ws.close()

    async def _subscribe(self, ws):
        msg = json.dumps({
            "id": self.data_type,
            "reqType": "sub",
            "dataType": self.data_type,
        })
        await ws.send(msg)

    async def _listen(self, ws):
        async for message in ws:
            if not self._running:
                break
            try:
                decoded = await self._decode(message)
                if decoded is not None:
                    await self._process_message(decoded)
            except Exception as e:
                logger.error("Process error: %s", e)

    async def _decode(self, message: Union[str, bytes]) -> Optional[dict]:
        if isinstance(message, bytes):
            try:
                message = gzip.decompress(message)
            except Exception:
                pass

        if isinstance(message, bytes):
            text = message.decode("utf-8", errors="replace")
        else:
            text = message

        # BingX sends application-level "Ping" every ~5s
        if text.strip() == "Ping":
            await self._ws.send("Pong")
            return None

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    async def _process_message(self, data: dict):
        if data.get("dataType") != self.data_type:
            return

        raw_list = data.get("data")
        if not raw_list or not isinstance(raw_list, list):
            return

        raw = raw_list[0]
        open_time_ms = raw.get("T")
        if open_time_ms is None:
            return

        open_time_dt = datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc)
        logger.debug(
            "RECV T=%s (ms=%s) O=%s H=%s L=%s C=%s V=%s",
            open_time_dt.strftime("%H:%M:%S"),
            open_time_ms,
            raw.get("o"),
            raw.get("h"),
            raw.get("l"),
            raw.get("c"),
            raw.get("v"),
        )

        if self._current_open_time is not None and open_time_ms != self._current_open_time:
            prev_open_dt = datetime.fromtimestamp(
                self._current_open_time / 1000, tz=timezone.utc
            )
            logger.debug(
                ">>> NEW CANDLE DETECTED: prev_T=%s new_T=%s",
                prev_open_dt.strftime("%H:%M:%S"),
                open_time_dt.strftime("%H:%M:%S"),
            )
            await self._emit_candle(self._current_raw, self._current_open_time)

        self._current_open_time = open_time_ms
        self._current_raw = raw

    async def _emit_candle(self, raw: dict, open_time_ms: int):
        self._candle_seq += 1
        candle_data = {
            "id": self._candle_seq,
            "open": float(raw.get("o", 0)),
            "high": float(raw.get("h", 0)),
            "low": float(raw.get("l", 0)),
            "close": float(raw.get("c", 0)),
            "open_time": datetime.fromtimestamp(
                open_time_ms / 1000, tz=timezone.utc
            ),
            "volume": float(raw.get("v", 0)),
        }

        logger.debug(
            "Candle #%d %s: O=%.2f H=%.2f L=%.2f C=%.2f",
            candle_data["id"],
            self.data_type,
            candle_data["open"],
            candle_data["high"],
            candle_data["low"],
            candle_data["close"],
        )

        if self.on_candle:
            result = self.on_candle(candle_data)
            if asyncio.iscoroutine(result):
                await result
