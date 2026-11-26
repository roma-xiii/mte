# MTE — архитектурный контекст Chart Workspace

## 1. Назначение

Chart Workspace управляет набором графиков внутри одного Chart-окна, их расположением, выбранным инструментом и сохраняемыми настройками. Каждое Chart-окно имеет независимое рабочее пространство. Окно выступает контейнером; каждый `Chart` имеет собственные настройки масштаба и таймфрейма.

Документ описывает согласованную архитектуру подсистемы. Общие правила именования, структуры слоёв, ошибок и тестирования задаются [project.md](../project.md). Управление физическими окнами описано в [window.md](./window.md); получение исторических и потоковых рыночных данных — в соответствующих контекстах.

## 2. Границы ответственности

- `ChartWorkspaceFeature` управляет состоянием рабочего пространства, выбранным инструментом и компоновкой графиков.
- `ChartProvider` создаётся для каждого графика и управляет загрузкой истории, подпиской на realtime, объединением свечей и освобождением ресурсов.
- `ChartBlock` — тонкая обёртка над Lightweight Charts, отвечающая за отображение и взаимодействие с графиком.
- Rust Cases выполняют изменения сохраняемого состояния, а Storages работают с SQLite.
- `WindowChartCreateCase` создаёт исходное состояние рабочего пространства при создании Chart-окна. Жизненный цикл физического окна относится к подсистеме Window.

## 3. Доменные модели

### Chart

```ts
interface Chart {
  id: ChartId;
  windowId: WindowId;
  timeframe: Timeframe;
  visibleCandleCount: number;
}
```

`ChartId` и `WindowId` — типизированные UUID в Rust; при передаче в TypeScript представлены строками. Таймфрейм хранится в SQLite в стабильном строковом представлении (например, `1h`, `1d`).

Каждый `Chart` имеет собственные настройки: изменение масштаба или таймфрейма одного графика не меняет настройки других. `visibleCandleCount` сохраняется на уровне `Chart`, без глобальной таблицы масштаба по инструменту и таймфрейму.

### ChartLayout

```ts
interface ChartLayoutItem {
  chartId: ChartId;
  proportion: number;
}

interface ChartLayout {
  windowId: WindowId;
  orientation: 'horizontal' | 'vertical';
  itemList: ChartLayoutItem[];
}
```

`itemList` задаёт порядок и доли занимаемого пространства. Пропорции нормализованы и в сумме приблизительно равны 1. В рабочем пространстве допустимо от нуля до произвольного количества графиков.

### ChartWorkspaceState

```ts
interface ChartWorkspaceState {
  windowId: WindowId;
  selectedWatchlistId: WatchlistId | null;
  selectedInstrumentId: InstrumentId | null;
}
```

Выбранный инструмент общий для всех графиков **в пределах одного Chart-окна**. При этом таймфрейм и масштаб каждого графика независимы. Рабочие пространства разных окон независимы.

## 4. Хранение в SQLite

Используются таблицы `chart`, `chart_layout`, `chart_workspace_state`. Каждая запись привязана к `app_window` через `windowId`; удаление окна каскадно удаляет связанное состояние. `ChartLayout.itemList` сохраняется в JSON.

Контракты Storage:

- `ChartStorage`: `create`, `get`, `list_by_window_id`, `timeframe_set`, `visible_candle_count_set`, `delete`.
- `ChartLayoutStorage`: `create`, `get`, `orientation_set`, `item_list_set`.
- `ChartWorkspaceStateStorage`: `create`, `get`, `watchlist_selected_set`, `instrument_selected_set`.

Явные методы удаления `ChartLayout` и `ChartWorkspaceState` не нужны: действует каскадное удаление по внешнему ключу.

## 5. Загрузка рабочего пространства

`ChartWorkspaceGetCase` читает графики, layout и workspace state в одной read-транзакции. Case проверяет, что множество `chartId` в `ChartLayout.itemList` соответствует фактически сохранённым графикам. При нарушении целостности возвращает ошибку, не выполняя неявного восстановления или исправления данных.

Пустое рабочее пространство (ноль графиков) — допустимое состояние; интерфейс отображает соответствующий empty state.

## 6. Создание нового Chart-окна

При создании нового Chart-окна `WindowChartCreateCase` в одной SQLite-транзакции создаёт `AppWindow`, один `Chart`, `ChartLayout` и `ChartWorkspaceState`. Первый график получает таймфрейм `1d`.

Первоначальный выбранный Watchlist — первый по `createdAt`. Первоначальный инструмент — первый инструмент выбранного Watchlist; если список пуст либо отсутствует, инструмент равен `null`. Другие списки для поиска инструмента не просматриваются. Состояние других окон не копируется.

После успешного коммита создаётся физическое окно Tauri. Обработка ошибки создания физического окна относится к контракту Window.

## 7. Создание и удаление графиков

`ChartCreateCase` создаёт новый `Chart` и согласованно изменяет `ChartLayout.itemList` в одной транзакции. Новый график по умолчанию использует таймфрейм `1h`; интерфейс предлагает только таймфреймы, ещё не используемые в данном рабочем пространстве. Новый график добавляется после последнего, временно разделяя с ним его долю пространства поровну. Если рабочее пространство пусто, первый добавленный график получает `proportion = 1`; его таймфрейм выбирается пользователем, по умолчанию `1h`.

`ChartDeleteCase` удаляет `Chart` и изменяет `ChartLayout.itemList` в одной транзакции. Освободившаяся доля переходит соседу справа, а если его нет — соседу слева. Последний график удалять разрешено.

Структурные операции изменения `itemList` на стороне React выполняются последовательно, чтобы исключить конфликт параллельных изменений. Ограничение уникальности таймфреймов реализовано в интерфейсе; отдельного ограничения в backend нет.

## 8. Ориентация, размеры и максимизация

`ChartLayoutOrientationSetCase` изменяет ориентацию (`horizontal` или `vertical`) и возвращает обновлённый layout. Изменение долей при перетаскивании разделителя сохраняется через `ChartLayoutProportionsSetCase` после завершения drag, а не на каждом движении указателя.

При неудачном сохранении пропорций не выполняется откат UI; ошибка логируется. Максимизация отдельного графика — временное состояние интерфейса, не изменяющее структуру `ChartLayout`.

Перестановка графиков перетаскиванием не входит в MVP.

## 9. Переключение инструмента

`ChartWorkspaceInstrumentSelectedSetCase` сохраняет `selectedInstrumentId` и возвращает обновлённый `ChartWorkspaceState`. Изменение выбранного инструмента распространяется на все `ChartProvider` внутри данного окна.

При переключении:

1. Предыдущие свечи немедленно убираются с экрана.
2. Устаревшие запросы и подписки отменяются или освобождаются; поздние ответы игнорируются.
3. Загружается история и устанавливается realtime-подписка для нового инструмента.
4. Сохраняется масштаб конкретного графика; отображение позиционируется на последних свечах.

Быстрые последовательные переключения обрабатываются по принципу «актуален последний выбор».

Выбранный инструмент может оставаться выбранным, даже если он не входит в текущий Watchlist. История показывается, если доступна; realtime-подписка для неактивного инструмента не создаётся.

## 10. Переключение таймфрейма и масштаба

`ChartTimeframeSetCase` сохраняет таймфрейм конкретного графика и возвращает обновлённый `Chart`. Затем `ChartProvider` загружает данные нового таймфрейма. Если загрузка истории завершилась ошибкой, выбранный таймфрейм остаётся сохранённым, а на графике показывается состояние ошибки с возможностью повторной попытки.

`ChartVisibleCandleCountSetCase` сохраняет количество видимых свечей конкретного `Chart` с debounce. При ошибке сохранения интерфейс не откатывает масштаб, ошибка логируется. Переключение инструмента или таймфрейма не сбрасывает масштаб конкретного графика.

## 11. Удаление выбранного Watchlist

Если выбранный Watchlist удалён, рабочее пространство выбирает первый оставшийся список по `createdAt` и сохраняет его ID; если списков больше нет — `selectedWatchlistId = null`. Выбранный инструмент при этом не меняется. Межоконное оповещение об изменениях Watchlist описано в контексте Watchlist.

## 12. Интеграция с историей и realtime

Каждый `ChartProvider` независимо управляет жизненным циклом данных своего графика, но использует общие `HistoryManager` и `SubscriptionManager` на стороне Rust. Менеджеры дедуплицируют совпадающие запросы и физические подписки между потребителями.

История и realtime запускаются параллельно. До завершения первоначальной загрузки истории realtime-обновления буферизуются по времени открытия свечи. При объединении realtime-состояние заменяет REST-свечу с тем же временем открытия. После инициализации обновления применяются к последней свече через Lightweight Charts; устаревшие свечи не передаются напрямую в `series.update()`.

После переподключения недостающая история запрашивается через `HistoryManager`. Отдельный график показывает собственную ошибку загрузки; сбой одного графика не блокирует другие.

## 13. Контракты Cases и обновление UI

- `ChartWorkspaceGetCase` — полный снимок рабочего пространства.
- `ChartCreateCase` — возвращает `{ chart, layout }`.
- `ChartDeleteCase` — возвращает обновлённый layout.
- `ChartTimeframeSetCase` — возвращает обновлённый `Chart`.
- `ChartVisibleCandleCountSetCase` — сохраняет настройку масштаба.
- `ChartLayoutOrientationSetCase` — возвращает обновлённый layout.
- `ChartLayoutProportionsSetCase` — сохраняет пропорции.
- `ChartWorkspaceInstrumentSelectedSetCase` и `ChartWorkspaceWatchlistSelectedSetCase` — возвращают обновлённый workspace state.

Изменения сохраняемого структурного состояния проходят сначала через Rust, затем применяются в React по результату команды. Ошибки команд отображаются в соответствии с общим контрактом `ApiError`.

## 14. Тестирование и критерии готовности

- Создание нового Chart-окна атомарно формирует исходные записи Chart/Layout/Workspace.
- `ChartWorkspaceGetCase` возвращает согласованный снимок и обнаруживает повреждённый layout.
- Добавление и удаление графиков корректно меняют порядок и пропорции; последний график удаляем.
- Таймфрейм и масштаб одного графика не изменяют настройки других.
- Переключение инструмента обновляет все графики одного окна, не затрагивая другие окна.
- Быстрые переключения не приводят к отображению устаревшей истории или подписки.
- Ошибка загрузки истории не отменяет сохранённый таймфрейм и не блокирует остальные графики.
- Удаление выбранного Watchlist корректно выбирает замену, не сбрасывая выбранный инструмент.
- При удалении Chart-окна связанное состояние удаляется каскадно; при завершении приложения сохраняется для восстановления.

Интеграционные тесты Storage и Cases выполняются с временной SQLite и настоящими миграциями. Для UI проверяются операции layout, переключение инструмента, таймфрейма и жизненный цикл `ChartProvider`.


## 15. Типизированные контракты (согласовано)

Контракты ниже уточняют разделы 3–13. Публичные Rust-типы сериализуются в TypeScript с `camelCase`; идентификаторы `ChartId`, `WindowId`, `WatchlistId`, `InstrumentId` — типизированные UUID в Rust и строки в TypeScript. `Timeframe` используется из Market History с утверждёнными строковыми значениями.

### 15.1. Модели

```ts
interface Chart {
  id: ChartId;
  windowId: WindowId;
  timeframe: Timeframe;
  visibleCandleCount: number;
}

type ChartLayoutOrientation = 'horizontal' | 'vertical';

interface ChartLayoutItem {
  chartId: ChartId;
  proportion: number;
}

interface ChartLayout {
  windowId: WindowId;
  orientation: ChartLayoutOrientation;
  itemList: ChartLayoutItem[];
}

interface ChartWorkspaceState {
  windowId: WindowId;
  selectedWatchlistId: WatchlistId | null;
  selectedInstrumentId: InstrumentId | null;
}
```

Пропорции положительные, нормализованы к сумме 1 с допустимой погрешностью округления. Для пустого `itemList` сумма не проверяется. `ChartLayout.itemList` содержит каждый существующий `chartId` ровно один раз.

### 15.2. Payload, результаты и Cases

```ts
interface ChartWorkspaceGetPayload { windowId: WindowId }
interface ChartWorkspaceGetResult {
  chartList: Chart[];
  layout: ChartLayout;
  state: ChartWorkspaceState;
}

interface ChartCreatePayload {
  windowId: WindowId;
  timeframe: Timeframe;
}
interface ChartCreateResult {
  chart: Chart;
  layout: ChartLayout;
}

interface ChartDeletePayload { chartId: ChartId }
interface ChartTimeframeSetPayload { chartId: ChartId; timeframe: Timeframe }
interface ChartVisibleCandleCountSetPayload {
  chartId: ChartId;
  visibleCandleCount: number;
}
interface ChartLayoutOrientationSetPayload {
  windowId: WindowId;
  orientation: ChartLayoutOrientation;
}
interface ChartLayoutProportionsSetPayload {
  windowId: WindowId;
  itemList: ChartLayoutItem[];
}
interface ChartWorkspaceInstrumentSelectedSetPayload {
  windowId: WindowId;
  instrumentId: InstrumentId | null;
}
interface ChartWorkspaceWatchlistSelectedSetPayload {
  windowId: WindowId;
  watchlistId: WatchlistId | null;
}
```

| Case | Payload | Успешный результат |
|---|---|---|
| `ChartWorkspaceGetCase` | `ChartWorkspaceGetPayload` | `ChartWorkspaceGetResult` |
| `ChartCreateCase` | `ChartCreatePayload` | `ChartCreateResult` |
| `ChartDeleteCase` | `ChartDeletePayload` | `ChartLayout` |
| `ChartTimeframeSetCase` | `ChartTimeframeSetPayload` | `Chart` |
| `ChartVisibleCandleCountSetCase` | `ChartVisibleCandleCountSetPayload` | `Chart` |
| `ChartLayoutOrientationSetCase` | `ChartLayoutOrientationSetPayload` | `ChartLayout` |
| `ChartLayoutProportionsSetCase` | `ChartLayoutProportionsSetPayload` | `ChartLayout` |
| `ChartWorkspaceInstrumentSelectedSetCase` | `ChartWorkspaceInstrumentSelectedSetPayload` | `ChartWorkspaceState` |
| `ChartWorkspaceWatchlistSelectedSetCase` | `ChartWorkspaceWatchlistSelectedSetPayload` | `ChartWorkspaceState` |

При создании нового Chart-окна начальный график имеет `1d`, как определено в разделе 6. При добавлении графика в существующее пустое рабочее пространство таймфрейм по умолчанию `1h`, доля `1`. При добавлении в непустое пространство новая доля равна половине доли последнего графика; оставшаяся половина сохраняется за прежним последним графиком.

### 15.3. Tauri Commands

| Command | Case |
|---|---|
| `chart_workspace_get` | `ChartWorkspaceGetCase` |
| `chart_create` | `ChartCreateCase` |
| `chart_delete` | `ChartDeleteCase` |
| `chart_timeframe_set` | `ChartTimeframeSetCase` |
| `chart_visible_candle_count_set` | `ChartVisibleCandleCountSetCase` |
| `chart_layout_orientation_set` | `ChartLayoutOrientationSetCase` |
| `chart_layout_proportions_set` | `ChartLayoutProportionsSetCase` |
| `chart_workspace_instrument_selected_set` | `ChartWorkspaceInstrumentSelectedSetCase` |
| `chart_workspace_watchlist_selected_set` | `ChartWorkspaceWatchlistSelectedSetCase` |

Команды принимают соответствующий Payload и возвращают результат Case либо общий `ApiError`. Отдельные события для изменений Chart Workspace в пределах одного окна не нужны: после успешной команды React применяет возвращённое состояние.

### 15.4. Storage

- `ChartStorage`: `create(Chart) -> Chart`, `get(ChartId) -> Chart`, `list_by_window_id(WindowId) -> Vec<Chart>`, `timeframe_set(ChartId, Timeframe) -> Chart`, `visible_candle_count_set(ChartId, u32) -> Chart`, `delete(ChartId) -> ()`.
- `ChartLayoutStorage`: `create(ChartLayout) -> ChartLayout`, `get(WindowId) -> ChartLayout`, `orientation_set(WindowId, ChartLayoutOrientation) -> ChartLayout`, `item_list_set(WindowId, Vec<ChartLayoutItem>) -> ChartLayout`.
- `ChartWorkspaceStateStorage`: `create(ChartWorkspaceState) -> ChartWorkspaceState`, `get(WindowId) -> ChartWorkspaceState`, `watchlist_selected_set(WindowId, Option<WatchlistId>) -> ChartWorkspaceState`, `instrument_selected_set(WindowId, Option<InstrumentId>) -> ChartWorkspaceState`.

Здесь указаны логические контракты; для операций, объединённых в одну транзакцию, Storage должен принимать транзакционный executor согласно общим правилам [project.md](../project.md). SQL и преобразование строк остаются в Storage; оркестрация — в Case.

### 15.5. Проверки и ошибки

- Отсутствующие `ChartId` / `WindowId` возвращают `NotFound` через общую модель ошибок.
- Неверные пропорции, повторяющиеся или отсутствующие `chartId` в layout, некорректный `visibleCandleCount` и неподдерживаемый `Timeframe` возвращают ошибку валидации.
- Структурные изменения `Chart` и `ChartLayout` атомарны; при ошибке не сохраняется частичный результат.
- Для изменения масштаба и пропорций остаётся ранее согласованное поведение UI без отката при ошибке сохранения.
- Изменения одного Chart Workspace не изменяют состояние других окон.
