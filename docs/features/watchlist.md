# MTE — архитектурный контекст Watchlist

## 1. Назначение и границы

Подсистема Watchlist управляет пользовательскими списками торговых инструментов: созданием, переименованием, удалением, составом, порядком элементов, цветовыми метками и отображением котировок. Списки общие для всего приложения, а выбранный список сохраняется отдельно для каждого Chart Workspace.

Документ фиксирует согласованное поведение подсистемы. Общие соглашения о слоях, именовании, ошибках и тестировании находятся в [project.md](../project.md). Каталог инструментов, рыночные потоки и рабочее пространство графиков описаны в [instrument-catalog.md](./instrument-catalog.md), [market-stream.md](./market-stream.md) и [chart-workspace.md](./chart-workspace.md).

## 2. Модели и идентификаторы

```ts
interface Watchlist {
  id: WatchlistId;
  name: string;
  sortableWatchlistInstrumentIds: WatchlistInstrumentId[];
  createdAt: string;
}

interface WatchlistInstrument {
  id: WatchlistInstrumentId;
  watchlistId: WatchlistId;
  instrumentId: InstrumentId;
  colorTag: ColorTag;
}

type ColorTag = 'default' | 'info' | 'success' | 'warning' | 'danger';
```

- В Rust идентификаторы — отдельные типы-обёртки над UUID; на границе Tauri — строки.
- `sortableWatchlistInstrumentIds` содержит **ID элементов списка**, а не ID инструментов.
- Один инструмент может присутствовать в нескольких Watchlist, но не более одного раза в каждом.
- `colorTag` принадлежит элементу Watchlist, а не инструменту глобально. `default` означает отсутствие выделения. В БД сохраняется семантическое значение, не RGB.
- Списки Watchlist упорядочены по `createdAt` (при равенстве — по `id`); пользовательская сортировка самих списков отсутствует.

## 3. SQLite и целостность

Используются таблицы:

- `watchlist`: `id` (PK), `name`, `sortable_watchlist_instrument_ids` (JSON-массив ID), `created_at`.
- `watchlist_instrument`: `id` (PK), `watchlist_id` (FK с `ON DELETE CASCADE`), `instrument_id` (FK к `instrument`), `color_tag`.

Ограничение `UNIQUE(watchlist_id, instrument_id)` исключает дубли. Удаление Watchlist удаляет его элементы, но не инструменты из каталога. Изменение состава списка и массива порядка выполняется **одной SQLite-транзакцией**. Массив порядка должен содержать в точности все ID элементов, без повторов. Нарушение целостности — ошибка, без автоматического исправления.

Для операций используется SQLx и общий пул SQLite; бизнес-инварианты проверяются в Case, ограничения целостности дополнительно защищаются БД. Отдельная таблица сортировки элементов не требуется.

## 4. Cases и Storages

Cases оркестрируют операции, обращаясь напрямую к Storages и, когда нужно, к другим согласованным зависимостям. Отдельный `WatchlistService` без самостоятельной повторно используемой логики не вводится.

| Case | Ответственность |
|---|---|
| `WatchlistCreateCase` | Создать список |
| `WatchlistUpdateCase` | Переименовать список |
| `WatchlistDeleteCase` | Удалить список и связанные элементы |
| `WatchlistListGetCase` | Получить списки в стабильном порядке |
| `WatchlistGetCase` | Получить один список |
| `WatchlistInstrumentListGetCase` | Получить элементы выбранного списка |
| `WatchlistInstrumentAddCase` | Добавить инструмент идемпотентно |
| `WatchlistInstrumentRemoveCase` | Удалить элемент |
| `WatchlistInstrumentOrderSetCase` | Сохранить полный новый порядок |
| `WatchlistInstrumentColorSetCase` | Изменить цветовую метку элемента |

`WatchlistStorage` отвечает за операции с Watchlist и его элементами. Для проверки существования инструмента Case использует `InstrumentStorage`. `ChartWorkspaceStateStorage` хранит выбранный Watchlist каждого окна. Tauri Commands остаются тонкими; TypeScript обращается к ним через API-классы, включая `WatchlistApi` и `WatchlistInstrumentApi`. Модели и Payload генерируются через specta; Rust `snake_case`, TypeScript `camelCase`.

## 5. Первоначальная инициализация

При первом запуске MTE один раз создаётся пустой Watchlist с именем **«Избранное»**. Факт инициализации фиксируется типизированной настройкой `watchlist.initialized` в `AppSettingsStorage`. Инициализация атомарна: список и признак успешной инициализации сохраняются согласованно.

Если пользователь удалил все Watchlist, приложение **не** создаёт «Избранное» заново. Отображается пустое состояние с возможностью создания списка. Инструменты в первоначальный список автоматически не добавляются.

## 6. Операции со списками

### Создание

Создаётся новый Watchlist с UUID, именем, временем создания и пустым массивом порядка. Окно-инициатор выбирает новый список и сохраняет выбор в своём `ChartWorkspaceState`; другие окна лишь обновляют перечень списков, не меняя выбор.

### Переименование

Имя обрезается по краям (`trim`); пустое имя запрещено. Одинаковые названия разных списков допустимы. Если нормализованное имя не изменилось, запись и событие не выполняются.

### Удаление

Перед удалением целого Watchlist интерфейс запрашивает подтверждение. Удаление каскадно удаляет элементы списка. Выбор удалённого Watchlist в сохранённых состояниях окон сбрасывается; каждое затронутое окно выбирает первый оставшийся список по `createdAt` (или `null`, если списков нет) и сохраняет этот выбор.

**Выбранный инструмент графиков при удалении Watchlist не меняется**, даже если его нет в новом списке. Окна с другим выбранным Watchlist сохраняют свой выбор.

## 7. Операции с элементами

### Добавление инструмента

Case проверяет существование Watchlist и Instrument. Если инструмент уже присутствует в списке, возвращает существующий `WatchlistInstrument` без изменения данных и без события. Иначе создаёт элемент с `colorTag='default'` и добавляет его ID в конец массива порядка в одной транзакции. Добавление не переключает инструмент графиков. В UI действие добавления уже присутствующего инструмента отключено.

### Удаление элемента

Удаление не требует подтверждения. Запись элемента и его ID в массиве порядка удаляются атомарно. Повторное удаление отсутствующего элемента — успешная операция без изменений. Выбранный инструмент графика не переключается; каталог инструментов не меняется.

### Перестановка элементов

Frontend передаёт **полный** массив `sortableWatchlistInstrumentIds`. Backend проверяет точное совпадение набора ID с текущими элементами, отсутствие дублей и чужих ID. Неизменившийся порядок не записывается и не создаёт событие. Перетаскивание в UI оптимистичное: при ошибке откат и уведомление; пока сохранение не завершилось, повторное перетаскивание блокируется.

### Цветовые метки

Метка устанавливается по `WatchlistInstrumentId`; сброс — значение `default`. Повторная установка того же значения не записывается и не создаёт событие. UI обновляется оптимистично; при ошибке — откат и уведомление.

## 8. Загрузка и представление данных

Watchlist и его элементы загружаются отдельными запросами. Модели `Instrument` запрашиваются по `InstrumentId` через каталог (в том числе пакетным `InstrumentListGetCase`), без встраивания полных инструментов в DTO Watchlist.

Порядок первоначальной загрузки: список Watchlist → выбранный Watchlist текущего окна → элементы списка → нужные модели Instrument. UI отображает доступные сохранённые инструменты независимо от текущей доступности биржи. Статусы Instrument приходят из каталога; текущая цена и изменение за 24 часа — из realtime ticker.

Выбор Watchlist относится к `ChartWorkspaceState` и **не меняет** выбранный инструмент графиков. Клавиша пробела переключает выбранный инструмент на следующий элемент текущего Watchlist циклически; при пустом списке переключения нет.

## 9. Frontend: автономная WatchlistFeature

`WatchlistFeature` — автономная React Feature, включающая собственные компоненты, контексты, провайдеры и хуки. Компоненты получают данные и действия через контексты Feature; прямой доступ компонентов к Zustand запрещён. Zustand — пассивное хранилище состояния в пределах React-приложения конкретного окна; вызовы API, подписки, обработка ошибок и бизнес-логика остаются в хуках/провайдерах Feature.

`WatchlistFeature` при монтировании сначала регистрирует слушателей событий, затем загружает данные. При размонтировании освобождает подписки и прочие ресурсы. Несмонтированная Feature не обязана поддерживать актуальный локальный снимок: при новом монтировании загружает его заново. Отдельный глобальный WatchlistController не создаётся.

`WatchlistEventService` существует отдельно от React/Zustand: один экземпляр на окно, одна физическая подписка Tauri на тип события, распределение по локальным слушателям. Сервис **не изменяет Zustand**; обновление состояния выполняют подписавшиеся хуки Feature.

## 10. Синхронизация между окнами

После успешной мутации Rust публикует Watchlist-событие для заинтересованных окон. События изменения перечня Watchlist и содержимого конкретного списка инициируют перечитывание соответствующих данных через API, а не передачу полного состояния в event payload.

Изменения имени, состава, порядка и цвета становятся видимы в других окнах. Локально выбранный Watchlist каждого окна независим. События отправляются **после успешного коммита** SQLite. Отсутствие изменения данных не создаёт события.

Отдельный механизм ревизий Watchlist для разрешения редких одновременных изменений в MVP не вводится. Инварианты защищены транзакциями и проверками, UI перечитывает актуальные данные после событий.

## 11. Realtime-котировки

Строки развёрнутого Watchlist получают ticker через `DataMarketStreamApi` / `SubscriptionManager`. Подписки дедуплицируются глобально по рыночному каналу и инструменту. При переключении списка выполняется разница между требуемыми подписками; при сворачивании Watchlist ticker-подписки освобождаются, при разворачивании создаются заново. Подписки графиков при этом не затрагиваются.

Компоненты строк получают данные через внутренний хук `useTicker(instrumentId)` и контексты Feature, без прямого обращения к Zustand. Высокочастотные обновления не должны приводить к ненужной перерисовке всего списка; оптимизация реализуется внутри Feature при необходимости.

## 12. Ошибки и инварианты

- Отсутствующий Watchlist/элемент — стандартный `StorageError.NotFound`, за исключением согласованной идемпотентности повторного удаления элемента.
- Дубли инструментов защищены бизнес-проверкой и уникальным SQL-ограничением.
- Недопустимый порядок или пустое нормализованное имя отклоняются на уровне Case.
- При ошибке записи не публикуется событие и не остаётся частично изменённого массива порядка.
- Ошибки Tauri API передаются через общий `ApiError` / `ApiException`.
- Для оптимистичных действий UI откатывает изменение и показывает уведомление.

## 13. Проверки и тестирование

Интеграционные Rust-тесты используют временную SQLite с реальными миграциями. Проверяются: первоначальная инициализация только один раз; повторное создание после удаления всех списков отсутствует; порядок списков; создание/переименование/удаление; допустимость одинаковых имён; каскадное удаление элементов; идемпотентное добавление и повторное удаление; уникальность `(watchlist_id, instrument_id)`; атомарность массива порядка; отклонение неверных перестановок; цветовые метки; отсутствие событий при no-op и ошибке.

Frontend-тесты проверяют: загрузку при монтировании; обновление по событиям между окнами; сохранение независимого выбора Watchlist; неизменность выбранного инструмента при смене/удалении списка; оптимистичный порядок и цвет с откатом; отключение добавления дубля; переключение пробелом; ticker-подписки при разворачивании, сворачивании и смене списка; освобождение ресурсов при размонтировании.

## 14. Границы MVP

В MVP нет пользовательской сортировки самих Watchlist, отдельной таблицы порядка элементов, автоматического повторного создания «Избранного», вложенных Instrument в Watchlist DTO, глобального WatchlistController, версионирования конфликтов списков и автоматического переключения графика при изменении состава Watchlist.

## 15. Типизированные контракты (второй проход)

Ниже приведены публичные контракты. Общие `WatchlistId`, `WatchlistInstrumentId`, `InstrumentId`, `WindowId` — типизированные UUID; `ColorTag` и доменные модели определены в разделе 2. Rust использует `snake_case`, сериализация через serde/specta предоставляет TypeScript `camelCase`. Поля `createdAt` — строка времени ISO 8601 UTC. Все Payload являются объектами; `()` означает отсутствие данных в ответе.

### 15.1. Payload и результаты Cases

```ts
interface WatchlistCreatePayload {
  windowId: WindowId;
  name: string;
}
interface WatchlistUpdatePayload {
  watchlistId: WatchlistId;
  name: string;
}
interface WatchlistDeletePayload {
  watchlistId: WatchlistId;
}
interface WatchlistGetPayload {
  watchlistId: WatchlistId;
}
interface WatchlistInstrumentListGetPayload {
  watchlistId: WatchlistId;
}
interface WatchlistInstrumentAddPayload {
  watchlistId: WatchlistId;
  instrumentId: InstrumentId;
}
interface WatchlistInstrumentRemovePayload {
  watchlistInstrumentId: WatchlistInstrumentId;
}
interface WatchlistInstrumentOrderSetPayload {
  watchlistId: WatchlistId;
  sortableWatchlistInstrumentIds: WatchlistInstrumentId[];
}
interface WatchlistInstrumentColorSetPayload {
  watchlistInstrumentId: WatchlistInstrumentId;
  colorTag: ColorTag;
}
```

| Case | Вход | Выход |
|---|---|---|
| `WatchlistCreateCase` | `WatchlistCreatePayload` | `Watchlist` |
| `WatchlistUpdateCase` | `WatchlistUpdatePayload` | `Watchlist` |
| `WatchlistDeleteCase` | `WatchlistDeletePayload` | `()` |
| `WatchlistListGetCase` | без Payload | `Watchlist[]` |
| `WatchlistGetCase` | `WatchlistGetPayload` | `Watchlist` |
| `WatchlistInstrumentListGetCase` | `WatchlistInstrumentListGetPayload` | `WatchlistInstrument[]` |
| `WatchlistInstrumentAddCase` | `WatchlistInstrumentAddPayload` | `WatchlistInstrument` |
| `WatchlistInstrumentRemoveCase` | `WatchlistInstrumentRemovePayload` | `()` |
| `WatchlistInstrumentOrderSetCase` | `WatchlistInstrumentOrderSetPayload` | `Watchlist` |
| `WatchlistInstrumentColorSetCase` | `WatchlistInstrumentColorSetPayload` | `WatchlistInstrument` |

Создание списка в контексте окна атомарно создаёт Watchlist и устанавливает `selectedWatchlistId` для инициирующего окна; остальные окна не переключаются. Удаление списка атомарно согласует выбранный Watchlist всех затронутых окон по правилу раздела 6. Отсутствие элемента при повторном удалении возвращает успех; отсутствие списка при удалении — `NotFound`. Переименование, установка порядка и цвета при неизменившемся значении возвращают актуальную модель без записи и события.

### 15.2. Публичные Tauri Commands

| Command | Case |
|---|---|
| `watchlist_create` | `WatchlistCreateCase` |
| `watchlist_update` | `WatchlistUpdateCase` |
| `watchlist_delete` | `WatchlistDeleteCase` |
| `watchlist_list_get` | `WatchlistListGetCase` |
| `watchlist_get` | `WatchlistGetCase` |
| `watchlist_instrument_list_get` | `WatchlistInstrumentListGetCase` |
| `watchlist_instrument_add` | `WatchlistInstrumentAddCase` |
| `watchlist_instrument_remove` | `WatchlistInstrumentRemoveCase` |
| `watchlist_instrument_order_set` | `WatchlistInstrumentOrderSetCase` |
| `watchlist_instrument_color_set` | `WatchlistInstrumentColorSetCase` |

`WatchlistApi` инкапсулирует команды для списков, `WatchlistInstrumentApi` — команды элементов. Выбор списка без его создания остаётся операцией `ChartWorkspaceWatchlistSelectedSetCase` из Chart Workspace, не дублируется здесь.

### 15.3. Контракт Storage

`WatchlistStorage` предоставляет операции над списками и элементами; SQL, маппинг строк и ограничения БД остаются внутри Storage. Транзакцией управляет Case и передаёт транзакционный executor в операции, участвующие в одной мутации.

```text
WatchlistStorage:
  create(watchlist) -> Watchlist
  get(watchlistId) -> Watchlist
  list_get() -> List<Watchlist>
  name_set(watchlistId, name) -> Watchlist
  delete(watchlistId) -> ()
  instrument_list_get(watchlistId) -> List<WatchlistInstrument>
  instrument_get(watchlistInstrumentId) -> WatchlistInstrument
  instrument_get_by_instrument_id(watchlistId, instrumentId) -> WatchlistInstrument | None
  instrument_create(watchlistInstrument) -> WatchlistInstrument
  instrument_delete(watchlistInstrumentId) -> ()
  instrument_order_set(watchlistId, sortableWatchlistInstrumentIds) -> Watchlist
  instrument_color_set(watchlistInstrumentId, colorTag) -> WatchlistInstrument
```

Методы `instrument_create`/`instrument_delete` сами по себе не заменяют атомарное обновление массива порядка: соответствующие Cases выполняют обе операции в одной транзакции. Case проверяет существование инструмента через `InstrumentStorage`. Список элементов возвращается в порядке `sortableWatchlistInstrumentIds`, а не в произвольном SQL-порядке. При чтении нарушенная согласованность порядка является ошибкой целостности.

### 15.4. События между окнами

События сигнализируют о необходимости перечитать данные; полный Watchlist и список элементов в payload не передаются.

```ts
interface WatchlistListChangedPayload {
  watchlistId: WatchlistId;
}
interface WatchlistInstrumentListChangedPayload {
  watchlistId: WatchlistId;
}
```

- `watchlist_list_changed` — создание, переименование или удаление Watchlist; все окна перечитывают список. При удалении затронутые окна также перечитывают собственный `ChartWorkspaceState`.
- `watchlist_instrument_list_changed` — добавление, удаление, перестановка или изменение цветовой метки элемента; окна, использующие этот Watchlist, перечитывают элементы и необходимые модели Instrument.
- Событие публикуется только после успешного коммита; no-op и ошибка не порождают событий. `WatchlistEventService` распределяет события в пределах окна, не изменяя Zustand самостоятельно.

### 15.5. Ошибки и границы ответственности

На границе Commands ошибки преобразуются в общий `ApiError { code, message, details? }`; frontend получает `ApiException`. `NotFound` используется для отсутствующего списка/элемента, кроме специально идемпотентного удаления элемента. Пустое имя после `trim`, дубли/чужие ID в массиве порядка и несогласованный состав списка — ошибки валидации или целостности; уникальность `(watchlist_id, instrument_id)` дополнительно защищена SQLite. Состояние подписок на котировки и их ошибки относятся к Market Stream; модели инструментов — к Instrument Catalog.
