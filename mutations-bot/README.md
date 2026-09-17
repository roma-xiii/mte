# mutations-bot

Монорепозиторий (uv workspace): общие пакеты `mutations-core`, `mutations-exchanges`, `mutations-strategies` и два Litestar-приложения — **tester** и **worker**.

## Требования

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

## Установка

```bash
uv sync --all-groups
```

## Запуск приложений

Tester (по умолчанию порт 8000):

```bash
uv run --directory apps/tester python -m tester
```

Worker (по умолчанию порт 8001):

```bash
uv run --directory apps/worker python -m worker
```

Проверка: `GET /health` → `{"status":"ok"}`.
