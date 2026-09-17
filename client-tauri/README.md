# MTE desktop-клиент (Tauri + React + TypeScript)

Десктопные окна тестера: Home, Backtest, Chart, Positions, ApiKeys. Многостраничная сборка Vite; Python-бэкенд запускается отдельно.

Установка и запуск — см. [INSTRUCTIONS.md](../INSTRUCTIONS.md) в корне репозитория. Кратко: `npm ci`, затем `npm run tauri dev`.

`npm run dev` (только Vite в браузере) не заменяет desktop: браузер не предоставляет Tauri API, поэтому соединение с Python и команды работают только в окне `npm run tauri dev`.

Проверки: `npm run build` (tsc + vite build) и `cargo check --offline` из `src-tauri/` (требует уже скачанных Rust-зависимостей).
