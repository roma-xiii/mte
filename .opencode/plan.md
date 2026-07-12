# План: Бэктестер в Tauri

## Архитектура

```
React (backtest window) ← Tauri events → Rust Backend ← stdin/stdout JSON → Python Process (Nautilus)
```

## Стек

| Слой | Технология |
|---|---|
| График | `lightweight-charts` (TradingView) |
| UI | Mantine v8 (уже есть в проекте) |
| Бридж | Tauri Rust commands — spawn процесс, stdin/stdout |
| Бэктест | Python — Nautilus streaming mode, шаг за шагом |
| Данные | CSV → Nautilus bars, выбор пары и ТФ в UI |

## Протокол Python ↔ Rust

**stdout (Python → Rust):** события построчно JSON
```json
{"type":"bar","index":42,"total":10000,"price":1.1005}
{"type":"sma","fast":1.1010,"slow":1.1002}
{"type":"trade","side":"BUY","price":1.1005,"size":100000}
{"type":"position","side":"LONG","entry":1.1005,"pnl":0}
{"type":"account","balance":1000000,"equity":1000500}
{"type":"complete","stats":{...}}
{"type":"error","message":"..."}
```

**stdin (Rust → Python):** команды
```json
{"cmd":"next"}           // обработать 1 бар
{"cmd":"next","n":10}    // обработать N баров
{"cmd":"pause"}          // пауза
{"cmd":"resume"}         // продолжить (эквивалент next)
{"cmd":"speed","value":2} // скорость (1=реалтайм, 2=вдвое быстрее...)
{"cmd":"stop"}           // остановить тест
```

## Процесс работы

1. UI → `backtest_start(config)` → Rust spawns Python процесс с `--config JSON`
2. Python в цикле: `run(streaming=True)` на 1 бар → вывод JSON в stdout → ждёт команду из stdin
3. Rust читает stdout по строкам → `app.emit("backtest:event", payload)` → React обновляет UI
4. Rust пишет команды в stdin Python процесса
5. При `stop` или завершении данных Python выводит `{"type":"complete"}` и завершается

## Файловая структура

### Python (nautilus/)
```
nautilus/
├── backtest_runner.py       # Основной скрипт: streaming loop + stdin/stdout
├── data_loader.py           # Парсинг CSV, список доступных инструментов
├── strategies/
│   ├── __init__.py
│   └── sma_crossover.py     # Стратегия SMA с market/limit ордерами
├── data/                    # CSV файлы с историческими данными
│   └── .gitkeep
├── .venv/                   # Уже существует
└── Makefile                 # Уже существует
```

### Rust (client-tauri/src-tauri/)
```
src-tauri/src/commands/
├── mod.rs
├── windows_commands.rs      # Уже существует
└── backtest_commands.rs     # Новый: управление Python процессом
src-tauri/src/main.rs         # Регистрация новых команд
```

### Frontend (client-tauri/src/apps/backtest/)
```
src/apps/backtest/
├── main.tsx                  # Точка входа
├── pages/
│   ├── index.ts
│   └── backtest-main/
│       └── backtest-main.page.tsx
├── features/
│   ├── backtest-config/      # Выбор пары, ТФ, периоды SMA, тип ордера
│   ├── backtest-controls/    # Start / Pause / Resume / Stop + Speed slider
│   ├── backtest-chart/       # Lightweight Charts: свечи + SMA + маркеры
│   ├── backtest-trade-list/  # Таблица сделок
│   └── backtest-summary/     # Сводка PnL, Sharpe, Win Rate, Drawdown
├── components/               # Общие компоненты для тестера
└── types.ts                  # Типы событий, конфига и т.д.
```

## Этапы реализации

### Этап 1: Python runner
- `backtest_runner.py` — запуск из консоли, streaming mode, stdin/stdout протокол
- `data_loader.py` — загрузка CSV
- `strategies/sma_crossover.py` — стратегия с market + limit ордерами
- Поддержка команд: next, pause, resume, speed, stop
- **Тест:** запуск в консоли, поток JSON, проверка команд

### Этап 2: Rust bridge
- `backtest_commands.rs` — spawn, stdin/stdout менеджмент, relay событий
- Регистрация окна `backtest`, команды, Tauri events
- HTML entry point + базовый React скелетон
- **Тест:** Start → Python стартует, Pause/Resume/Stop работают

### Этап 3: Frontend — конфиг + controls
- Панель настроек (инструмент, ТФ, периоды SMA, тип ордера, размер)
- Кнопки Start / Pause / Resume / Stop
- Speed slider
- **Тест:** полный цикл запуска и управления из UI

### Этап 4: Frontend — график
- Lightweight Charts: свечи OHLC, линии SMA, маркеры сделок
- Обновление в реальном времени
- **Тест:** визуальная проверка графика

### Этап 5: Frontend — список сделок + сводка
- Таблица сделок: время, сторона, цена входа/выхода, PnL
- Сводный отчёт: PnL, Sharpe, Win Rate, Max Drawdown
- **Тест:** цифры сходятся с данными из консоли

# Новый план
Шаг 1: Python WebSocket сервер
Файл: websocket_server.py (новый)
- Litestar с WS-endpoint /ws
- При подключении: парсит config из query, запускает Nautilus в asyncio.to_thread()
- Команды: next, pause, resume, stop, speed — через asyncio.Queue
- События: бары, SMA, позиции, сделки — шлёт в WS
- backtest_runner.py больше не нужен (удалим позже)
Тест: открываю терминал, запускаю python websocket_server.py, подключаюсь через websocat или пишу тестовый скрипт на Python — шлю {"cmd":"next","n":50}, вижу поток JSON.
Шаг 2: Rust — spawn/kill процесса
Файл: backtest_commands.rs (переписать)
- backtest_start(config) → spawn python3 websocket_server.py --port 8765, возвращает URL
- backtest_stop() → kill процесса
- Всё остальное (данные, команды) — через WS напрямую из React
Тест: запускаю Tauri, нажимаю Start, проверяю что процесс жив (ps aux | grep websocket), нажимаю Stop — процесс убит.
Шаг 3: React — прямой WebSocket
Файл: backtest.app.tsx (переписать)
- Start → invoke('backtest_start', config) → new WebSocket(url)
- Команды: ws.send(JSON.stringify({cmd:'next',n:10}))
- События: ws.onmessage → обновление лога
- Stop: ws.send('{"cmd":"stop"}') + invoke('backtest_stop')
Тест: полный цикл — Start → Next → Pause → Resume → Stop, всё в окне Tauri.
