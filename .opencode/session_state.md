# Session State — Backtester

## Сделано (Phase 0–1)

### Phase 0 — Cleanup
- Удалены: `backtest_runner.py`, корневой `sma_crossover.py`, `backtest_results.html`
- `backtest.app.tsx` — заглушка
- `backtest_commands.rs` — очищен от stdin/stdout
- `main.rs` — убраны старые команды

### Phase 1.1 — WebSocket протокол
- Конфиг через WS-сообщение `{"cmd":"start","config":{}}`, не в query params
- Роутинг команд: start, pause, resume, speed, stop, list_data, delete_data, list_strategies
- События: bar, entry, exit, trade, log (с float вместо str), progress, complete, error, snapshot

### Phase 1.2 — Session Buffer
- `SessionBuffer` + `SessionState` + `_current_session` (module-level)
- Snapshot при реконнекте: все бары, трейды, логи, финальный статус

### Phase 1.3 — Strategy Registry
- `strategies/__init__.py`: `discover_strategies()`, `get_strategy_cls(name)`
- `SMACrossConfig.config_schema()` — JSON-схема параметров

### Phase 1.4 — Data Downloader
- `data_downloader.py` — ccxt OHLCV download, пагинация, `data/{symbol}-{tf}.csv`

### Phase 1.5 — Data Manager
- `get_csv_metadata()` — bars count + date range из CSV
- `list_available_instruments()` — обогащена метаданными
- `delete_data` command в WS

### Phase 1.6 — BacktestRunner
- `run_nautilus` → class `BacktestRunner` (load_data, setup_engine, setup_strategy, run)
- Dynamic strategy loading: `get_strategy_cls(strategy_name)` + `strategy_params`
- `RunnerConfig`: `strategy_name`, `strategy_params`, `account_type`, `leverage`
- `account.balance(USD)` → `account.balance(instrument.quote_currency)`

## Сделано (Phase 2)

### Phase 2 — Tauri WS Proxy Bridge
- Cargo.toml: `tokio-tungstenite`, `futures-util`, `tokio` (sync, time, macros)
- `backtest_commands.rs`:
  - `BacktestBridge` struct: `ws_tx` (mpsc sender) + `snapshot` cache
  - `init(app_handle)` — spawn WS connect loop с auto-reconnect (5s)
  - WS read-loop → `app_handle.emit("backtest:event", payload)`
  - snapshot кешируется при получении
  - Команды: start, pause, resume, speed, stop, list_data, list_strategies, delete_data, get_snapshot
- `main.rs`: `.manage(BacktestBridge::new())`, init в setup, все команды зарегистрированы

## Впереди

### Phase 3–7 — Frontend (React + Mantine)
- Setup screen: exchange, symbol, tf, dates, pre-loaded data, strategy params, start
- Real-time: speed slider, pause/resume/stop, progress
- TradingView Lightweight Chart
- Log + Trade History (tabs)
- Session reconnection

## Архитектурные решения
- WS порт: 127.0.0.1:8765 (захардкожен)
- Tauri управляет WS-соединением, не процессом Python
- Python-сервер запускается отдельно пользователем
- Баланс: `quote_currency` инструмента (BTCUSDT → USDT)
