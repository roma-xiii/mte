# План реализации бэктестера стратегий для алготрейдинга

## Архитектурное решение

**WebSocket (Litestar) как основной протокол. Tauri управляет процессом Python + проксирует WebSocket.**

```
Frontend (React)
    ↕ invoke() + Tauri events
Tauri (Rust) — проксирует WS, управляет lifecycle Python-сервера
    ↕ WebSocket (localhost:8765)
Python (Litestar + NautilusTrader) — standalone WS-сервер
```

Tauri выступает как bridge: фронтенд общается с ним через invoke/events, а Tauri перенаправляет сообщения на Python WebSocket. Это даёт:
- Tauri контролирует процесс Python (старт/стоп/kill)
- Tauri может убить процесс, если тест завис
- WS-соединение не зависит от окна браузера
- При переоткрытии окна Tauri пересылает всю историю из Python

---

## Phase 0: Cleanup

| # | Задача | Описание |
|---|--------|----------|
| 0.1 | Удалить `backtest_runner.py` | Не нужен, заменяется WS-сервером |
| 0.2 | Удалить `nautilus/sma_crossover.py` (корневой) | Дублирует `strategies/sma_crossover.py` |
| 0.3 | Удалить `backtest_results.html` | Сгенерированный артефакт |
| 0.4 | Сбросить `backtest.app.tsx` | Убрать старый hardcoded UI, оставить пустой каркас |
| 0.5 | Почистить `backtest_commands.rs` | Убрать stdin/stdout логику, оставить структуру для WS |

---

## Phase 1: Python — WebSocket Server (Litestar + NautilusTrader)

### 1.1 WebSocket-сервер (`websocket_server.py`)

- Один WS-endpoint `/ws` на порту 8765
- При подключении клиента:
  - Отправляет `{type:"strategies_list"}` — список доступных стратегий с описанием параметров
  - Отправляет `{type:"data_list"}` — список CSV-файлов в `data/`
  - Если есть активный/завершённый тест — отправляет весь буфер (снапшот: все бары, логи, сделки, прогресс)
- Команды от клиента:
  - `{cmd:"start", config:{...}}` — запуск теста
  - `{cmd:"pause"}`, `{cmd:"resume"}`, `{cmd:"speed", value:N}`
  - `{cmd:"stop"}` — штатная остановка
  - `{cmd:"list_data"}`, `{cmd:"delete_data", filename:"..."}`
  - `{cmd:"list_strategies"}`
- События клиенту:
  - `{type:"bar", data:{...}}`
  - `{type:"entry", data:{...}}` / `{type:"exit", data:{...}}`
  - `{type:"trade", data:{...}}` — завершённая сделка
  - `{type:"log", level, message, timestamp}`
  - `{type:"progress", current, total, pct}`
  - `{type:"complete", stats:{pnl, sharpe, max_dd, win_rate, total_trades}}`
  - `{type:"error", message}`
  - `{type:"data_list", data:[...]}`
  - `{type:"strategies_list", data:[...]}`

### 1.2 Session Buffer

- Хранит историю в памяти Python: все бары, логи (N последних), сделки, текущий прогресс
- При реконнекте клиента отправляется `{type:"snapshot", bars:[...], trades:[...], logs:[...], progress:{...}}` целиком
- Буфер хранится до старта нового теста

### 1.3 Strategy Registry

- Автоматический поиск стратегий в `strategies/` (по наследованию от `Strategy`)
- Каждая стратегия экспортирует `get_config_schema()` → JSON-схема параметров:
  ```json
  {"name": "sma_crossover", "params": {
    "fast": {"type": "int", "default": 10, "min": 2, "max": 200},
    "slow": {"type": "int", "default": 20, "min": 5, "max": 500},
    "trade_size": {"type": "float", "default": 1000, "min": 1},
    "order_type": {"type": "select", "options": ["market", "limit"], "default": "market"}
  }}
  ```
- На старте фронтенд получает этот список и рендерит параметры динамически

### 1.4 Data Downloader

- Загрузка истории с Bybit / Binance по параметрам (exchange, symbol, timeframe, date_from, date_to)
- Сохранение в `data/{symbol}-{timeframe}.csv`
- Автоматическое добавление в список доступных для теста котировок

### 1.5 Data Manager Commands

- `{cmd:"list_data"}` → список CSV с метаданными (биржа, символ, тф, количество баров, дата-диапазон)
- `{cmd:"delete_data", filename:"..."}` → удалить CSV
- `{cmd:"refresh_data"}` → пересканировать `data/` директорию

### 1.6 Nautilus Engine Wrapper

- Настройка `BacktestEngine` с переданными параметрами
- Режим "walk-forward" / bar-by-bar: итерирование по барам, пауза между отправкой
- Управление скоростью через `asyncio.sleep()` (1 bar в `1/speed` секунд)
- Pause/Resume через `asyncio.Event()`
- Stop — прерывание цикла `asyncio.Task.cancel()` + force kill если завис
- Обработка стратегии: вызов `on_bar()` на каждый бар, трекинг позиций

---

## Phase 2: Tauri — Process Manager & WS Proxy

### 2.1 Удалить старый stdin/stdout код

- Из `backtest_commands.rs`: убрать `BacktestProcess`, `backtest_start` (старый), `backtest_send_command`

### 2.2 Process Manager

- `BacktestServer` struct:
  - `process: Option<Child>` — запущенный Python процесс
  - `ws_connected: bool` — состояние WS
  - `running: bool`
- `backtest_start_server()` → spawn `websocket_server.py` как child process
- `backtest_stop_server()` → graceful stop через WS, если не отвечает → `kill()`
- `backtest_kill()` → force kill (SIGKILL)

### 2.3 WebSocket Client in Rust

- Использовать `tokio-tungstenite` (или `tungstenite`) для WS-соединения с Python
- Подключается при старте сервера, автоматически реконнектится
- Принимает команды от фронтенда через Tauri invoke, отправляет их в WS:
  - `backtest_start(config)` → `{cmd:"start", config}`
  - `backtest_pause()` / `backtest_resume()` → `{cmd:"pause/resume"}`
  - `backtest_speed(n)` → `{cmd:"speed", value:n}`
  - `backtest_stop()` → сначала `{cmd:"stop"}`, если таймаут → `backtest_kill()`
  - `backtest_list_data()` → `{cmd:"list_data"}`
  - `backtest_delete_data(filename)` → `{cmd:"delete_data", filename}`
  - `backtest_list_strategies()` → `{cmd:"list_strategies"}`
- Получает события от Python, эмитит их как Tauri events: `backtest:event`
- Буферизация: если фронтенд-окно закрыто, Tauri продолжает получать и буферизировать события; при открытии окна отправляет буфер

### 2.4 Window Management

- `backtest_open()` (уже есть) — создать/показать окно; при открытии отправить буферизированные события
- `backtest_close()` — скрыть окно, НЕ останавливать тест

### 2.5 Capabilities

- Обновить `capabilities/default.json` для нового окна backtest

---

## Phase 3: Frontend — Setup Screen

### 3.1 Exchange Selector

- `Select` из Mantine: Bybit, Binance (+ будущие)
- При выборе биржи — запрос к Python через Tauri на список символов (или использовать закешированный)

### 3.2 Symbol Selector

- `Select` с `searchable` и `data` из загруженного списка инструментов
- Для Bybit/Binance: получать через API Python (или кэш)
- При выборе pre-loaded data — скрыть exchange/symbol/tf/date поля

### 3.3 Timeframe Selector

- `Select`: 1m, 5m, 15m, 30m, 1h, 4h, 1d

### 3.4 Date Range

- `DatePickerInput` (range mode) из Mantine + числовой ввод "количество баров"
- Радио-переключатель: "По датам" / "По количеству баров"
- Если выбраны pre-loaded данные — берётся полный диапазон файла

### 3.5 Pre-loaded Data Selector

- `Select` с `searchable`, данные приходят с `{cmd:"list_data"}`
- При выборе — блокирует exchange/symbol/tf/date (или авто-заполняет их)
- Отображает метаданные файла (бары, даты)

### 3.6 Strategy Selector

- `Select` из списка стратегий (от Python)
- При выборе — динамическая генерация полей параметров:
  - `int` → `NumberInput` с min/max
  - `float` → `NumberInput` с decimal шагом
  - `select` → `Select` с options
  - `bool` → `Switch`

### 3.7 Data Manager UI

- Отдельный раздел в setup screen или модальное окно
- Таблица: имя файла, биржа, символ, тф, бары, дата-диапазон, действия (удалить)
- Кнопка "Refresh" — пересканировать data/

### 3.8 Start Button

- Валидация всех полей
- Вызов `invoke('backtest_start', config)`
- Переход в режим running (показывать панель управления)

---

## Phase 4: Frontend — Real-time Control

### 4.1 WebSocket Client

- `@tauri-apps/api/event` — слушаем события `backtest:event`
- Диспатчим по `type`:
  - `bar` → в chart
  - `log` → в log panel
  - `trade` → в trade history
  - `progress` → progress bar
  - `complete` → финальная статистика
  - `snapshot` → при реконнекте, заполняем все панели
  - `data_list` → обновляем список данных
  - `strategies_list` → обновляем список стратегий

### 4.2 Speed Control

- `Slider` из Mantine: 1–100, дискретный шаг 1
- При изменении: `invoke('backtest_speed', value)`

### 4.3 Pause/Resume/Stop

- Кнопки: Pause, Resume (активна только одна), Stop
- `invoke('backtest_pause')` / `invoke('backtest_resume')` / `invoke('backtest_stop')`
- Stop: подтверждение → если WS не отвечает, Tauri force kill

### 4.4 Progress Bar

- `Progress` из Mantine
- Текст: "150 / 2000 bars (7.5%)"

---

## Phase 5: Frontend — TradingView Lightweight Chart

### 5.1 Chart Component

- `lightweight-charts` npm package
- `createChart` в `useEffect` с ref на div
- Темная тема (согласовано с Mantine dark theme)

### 5.2 Candlestick Series

- Серия `candlestick` (или `ohlc`)
- При каждом `bar` событии: `series.update({time, open, high, low, close})`

### 5.3 Entry/Exit Markers

- `series.createMarker({'shape, 'position, 'price, 'text, 'color})`
- При `entry` → зелёный треугольник вверх (long) или красный вниз (short)
- При `exit` → кружок

### 5.4 TP/SL Lines

- `chart.addLineSeries()` для TP (зелёная линия) и SL (красная линия)
- При открытии позиции рисуем линии на уровне TP/SL
- Удаляем/обновляем при закрытии

### 5.5 Time Axis

- Используем временные метки из баров
- Автомасштабирование: `chart.timeScale().fitContent()`

---

## Phase 6: Frontend — Log & Trade History

### 6.1 Tab Panel

- `Tabs` из Mantine: "Лог" | "Сделки"
- На весь нижний блок под графиком

### 6.2 Log Panel

- `<ScrollArea>` с `autoscroll`
- Каждая запись: `[timestamp] [LEVEL] message`
- Цветовое кодирование по level (info, warn, error)
- Ограничение на N последних записей (например, 1000)

### 6.3 Trade History Table

- `Table` из Mantine
- Колонки: # | Side | Entry Price | Exit Price | PnL | Entry Time | Exit Time | SL | TP
- Сортировка по времени
- Подсветка: зелёный/+ для профитных, красный/минус для убыточных

---

## Phase 7: Session Persistence & Reconnection

### 7.1 Window Close/Open Flow

- Закрытие окна → frontend уничтожается, но Tauri и Python продолжают работать
- Буферизация в Tauri Rust: последние N событий хранятся
- Открытие окна → Tauri отдаёт буфер + Python отдаёт snapshot через WS

### 7.2 Python-side Buffer

- In-memory: все бары (`list[dict]`), все сделки (`list[dict]`), логи (`deque(maxlen=1000)`)
- При подключении WebSocket клиента → `{type:"snapshot", ...}`

---

## Файлы для изменения/создания

| Файл | Действие |
|------|----------|
| `nautilus/websocket_server.py` | Переписать — добавить strategy registry, data manager, session buffer, snapshot, speed/pause/resume/stop |
| `nautilus/data_loader.py` | Доработать — list/delete CSV, metadata reader |
| `nautilus/strategies/__init__.py` | Обновить — auto-discover strategies |
| `nautilus/strategies/sma_crossover.py` | Доработать — добавить `get_config_schema()` |
| `nautilus/backtest_runner.py` | Удалить |
| `nautilus/backtest.py` | Удалить |
| `client-tauri/src-tauri/src/commands/backtest_commands.rs` | Переписать — process manager + WS proxy |
| `client-tauri/src-tauri/Cargo.toml` | Обновить — добавить `tokio-tungstenite` |
| `client-tauri/src-tauri/capabilities/default.json` | Обновить — разрешения для backtest window |
| `client-tauri/src/apps/backtest/backtest.app.tsx` | Переписать — setup UI + real-time control + chart + log + trades |
| `client-tauri/src/apps/backtest/main.tsx` | Обновить — routing if needed |
| `client-tauri/src/components/` | Создать — BacktestSetup, BacktestChart, BacktestLog, BacktestTrades, DataManager, StrategyParamsForm |
