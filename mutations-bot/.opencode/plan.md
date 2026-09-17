# Запуск стратегии Yojic в live worker

## Цель

Перенести стратегию `StrategyYojic` из тестера в реальный/демо-воркер на BingX.
Загрузка истории → WebSocket подписка на свечи → каждая свеча в стратегию → торговые решения.

---

## Три режима

| mode | TradingControl | Куда идёт |
|------|---------------|-----------|
| `paper` | `TradingControlPaper` | in-memory, без API |
| `demo` | `TradingControlBingx` + `mode_demo=True` | BingX testnet, виртуальный USDT |
| `real` | `TradingControlBingx` + `mode_demo=False` | BingX mainnet, реальные деньги |

---

## Статус выполнения

### ✅ Шаг 1 — WebSocket клиент
**Файлы:**
- `packages/exchanges/bingx_ws.py` — класс `KlineStream`
- `packages/exchanges/exchanges.py` — экспорт
- `packages/exchanges/pyproject.toml` — добавлен `websockets`
- `apps/worker/tests/test_ws*.py` — тесты

**Что сделано:**
- GZIP декомпрессия, Ping/Pong, авто-реконнект
- Детект закрытых свеч по смене `open_time`
- Подтверждено: WS-данные 100% совпадают с REST API BingX (5/5)

---

### ✅ Шаг 2 — .env + фикс trading_control_bingx
**Файлы:**
- `packages/trading_controls/trading_control_bingx.py` — рефакторинг
- `.env` — переменные окружения

**Что сделано:**
- API ключи вынесены в `os.getenv("BINGX_API_KEY")` / `BINGX_API_SECRET`
- Убран глобальный `client` → создаётся в `__init__` через `self._client`
- Добавлен параметр `mode_demo` (по умолчанию `True` — testnet)
- Раскомментирован `candle_check()` — SL проверяется по свечам
- Явные `return None` во всех методах (типизация)

---

### 🔲 Шаг 3 — BotRunner + CLI (режим paper)
**Файлы:**
- Создать `apps/worker/bot_runner.py`
- Переписать `apps/worker/worker.py`
- Дополнить `apps/worker/pyproject.toml` (добавить `trading_controls`)

**BotRunner — машина состояний:**
- Состояния: `idle`, `running`, `paused`
- `start(symbol, interval, balance, mode)` — загрузить 1000 свечей (BingX REST), создать `CandleList` + `TradingControl*` + `StrategyYojic`, скормить историю, печатать логи
- `stop()` — остановить стратегию + закрыть позицию
- `pause()` — пауза входов (без закрытия)
- `resume()` — продолжить
- `status()` — dict с позицией, балансом, PnL, последней свечой

**CLI (worker.py) — asyncio stdin loop:**
- `run_in_executor` читает команды из stdin, prompt `> `
- Параллельно работает бот (лог + стратегия)
- Логи с timestamp `[HH:MM:SS]`

**Команды:**
```
start   SOLUSDT 15m 100 paper    # запуск
stop                              # стоп + закрыть
pause                             # пауза
resume                            # продолжить
status                            # состояние
help                              # справка
exit / quit                       # выход
```

---

### 🔲 Шаг 4 — WebSocket интеграция + демо/реал режимы
**Файлы:**
- Править `apps/worker/bot_runner.py`

**Что делаем:**
- В `start()` после истории → WebSocket подключение
- Каждая новая свеча → `strategy.candle_new()`
- В `start()` третий аргумент `mode`: paper → Paper, demo → Bingx(demo=True), real → Bingx(demo=False)

**Команда после шага 4:**
```
start SOLUSDT 15m 100 paper    # только симуляция, без API
start SOLUSDT 15m 100 demo     # BingX testnet
start SOLUSDT 15m 100 real     # BingX mainnet
```
