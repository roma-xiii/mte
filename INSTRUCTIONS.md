## 1. Nautilus Server — WebSocket бэкенд для бэктестов

```bash
cd /nautilus

# Установка зависимостей (первый раз)
make install

# Запуск сервера
make run

# Или с hot-reload для разработки
make run-dev
```

Сервер запускается на `ws://127.0.0.1:8765/ws`.

### Доступные Make команды

| Команда | Описание |
|---------|----------|
| `make install` | Создать venv и установить зависимости |
| `make run` | Запустить сервер |
| `make run-dev` | Запустить с hot-reload |
| `make clean` | Удалить venv и кеши |

### Кастомный хост/порт

```bash
# По умолчанию 127.0.0.1:8765
source .venv/bin/activate
python websocket_server.py --host 0.0.0.0 --port 9000
```

---

## 2. Tauri Client — десктопное приложение

```bash
cd /client-tauri

# Установка зависимостей (первый раз)
npm install

# Запуск в режиме разработки
npm run tauri dev
```
