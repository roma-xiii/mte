# Documentation

Точка входа для агента: сначала этот индекс, затем [Project Context](./project.md)
и только документы функций, которые затрагивает задача.

## Где искать

| Тема | Раздел |
|---|---|
| Именование сущностей | [project.md §3](./project.md#3-именование) |
| Слои Rust: commands / cases / storages / providers | [project.md §4](./project.md#4-архитектура-rust) |
| ID, Payload, `ApiError`, генерируемые типы | [project.md §5](./project.md#5-идентификаторы-и-публичные-контракты) |
| SQLite, миграции, транзакции | [project.md §6](./project.md#6-sqlite-и-сохраняемое-состояние) |
| Слои React, Context, события | [project.md §7](./project.md#7-архитектура-react) |
| Tauri Events и доставка | [project.md §9](./project.md#9-commands-events-и-жизненный-цикл), [market-stream.md §7.1](./features/market-stream.md#71-контракты-tauri-events) |
| Логирование и диагностика | [project.md §10](./project.md#10-логирование-и-диагностика) |
| Тесты, порядок работы над задачей | [project.md §11](./project.md#11-работа-над-задачами-и-проверки) |

## General
- [Project Context](./project.md) — общие правила: архитектура Rust и React, именование, ошибки, SQLite, тестирование. Обязателен перед любой задачей.

## Features
- [Window](./features/window.md) — жизненный цикл окон Home/Chart: создание, геометрия, закрытие, сохранение и восстановление.
- [Instrument Catalog](./features/instrument-catalog.md) — справочник инструментов Binance/Bybit: синхронизация, хранение в SQLite, поиск.
- [Market History](./features/market-history.md) — исторические OHLCV-свечи: RAM-кеш, очередь REST-запросов, догрузка и дедупликация.
- [Market Stream](./features/market-stream.md) — realtime-данные: WebSocket-подписки, доставка событий, переподключение.
- [Chart Workspace](./features/chart-workspace.md) — графики внутри окна Chart: layout, выбор инструмента и таймфрейма, состояние Workspace.
- [Watchlist](./features/watchlist.md) — списки наблюдения: состав, порядок, метки, котировки, выбранный список для Workspace.
