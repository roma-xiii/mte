# Documentation

Точка входа для агента: сначала этот индекс, затем [Project Context](./project.md)
и только документы функций, которые затрагивает задача.

## General
- [Project Context](./project.md) — общие правила: архитектура Rust и React, именование, ошибки, SQLite, тестирование. Обязателен перед любой задачей.

## Features
- [Window](./features/window.md) — жизненный цикл окон Home/Chart: создание, геометрия, закрытие, сохранение и восстановление.
- [Instrument Catalog](./features/instrument-catalog.md) — справочник инструментов Binance/Bybit: синхронизация, хранение в SQLite, поиск.
- [Market History](./features/market-history.md) — исторические OHLCV-свечи: RAM-кеш, очередь REST-запросов, догрузка и дедупликация.
- [Market Stream](./features/market-stream.md) — realtime-данные: WebSocket-подписки, доставка событий, переподключение.
- [Chart Workspace](./features/chart-workspace.md) — графики внутри окна Chart: layout, выбор инструмента и таймфрейма, состояние Workspace.
- [Watchlist](./features/watchlist.md) — списки наблюдения: состав, порядок, метки, котировки, выбранный список для Workspace.
