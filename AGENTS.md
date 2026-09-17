## Соглашения об именовании

### Порядок слов: СУЩЕСТВИТЕЛЬНОЕ всегда первым (Noun-Verb)
`<существительное>[<прилагательное>]<глагол/предлог>`

- `userListSet` ✓ (не `setUserList`)
- `documentConfigCurrent` ✓
- `keyParsed` ✓ (не `parsedKey`)
- `variableResolved` ✓ (не `resolvedVariable`)
- `variableFormatted` ✓ (не `formattedVariable`)
- `errorValidation` ✓ (не `validationError`)
- `documentIdCurrent` ✓
- `printFormIsEdited` ✓

### ЖЁСТКОЕ ПРАВИЛО: НИКАКИХ `s` ДЛЯ МНОЖЕСТВЕННОГО ЧИСЛА
Только `List`: `documentConfigList`, `fieldConfigList`, `keyParsedList`, `errorList`, `variableList`.

Исключение — названия entity/классов: `PrintForm`, `DocumentConfig`, `FieldConfig`.

### Никаких сокращений
Если по типам у нас сущность `DocumentConfig`, то в переменной используем только `documentConfig`, никаких `doc`, `docs` и пр.

### Примеры
- `documentConfig`, `documentConfigCurrent`, `documentConfigList`, `documentConfigKey`
- `fieldConfig`, `fieldConfigCurrent`, `fieldConfigList`, `fieldConfigKey`
- `documentCurrent` / `documentRow`, `documentList`, `documentId`
- `printForm`, `printFormList`
- `keyParsed`, `keyParsedList`
- `variableResolved`, `variableResolvedList`
- `variableFormatted`, `variableFormattedList`
- `errorValidation`, `errorValidationList`
- `fieldConfigListByDocumentConfigKey` (Map)
- `documentRowByConfigKey` (Map)

## ЗАПРЕЩЕНО: `!.` (non-null assertion)
Вместо `documentConfigCurrent!.key` — if проверка с ошибкой.

## Стиль кода
- Комментариев НЕТ (кроме TODO с номером задачи)
- TODO в коде — для разработчика, НЕ призыв к действию для агента
- Error messages — English, parseable, без подсказок
- UI messages — Russian
- camelCase, PascalCase

### Zustand: подписка на сторы
- Все значения (данные и экшены) — через селекторы, по одному на значение:
  const data = useStore((s) => s.data);
  const act = useStore((s) => s.act);
- Экшены — стабильные ссылки: селекторы на них дают 0 ре-рендеров.
- Деструктуризация из useStore() без селектора — ЗАПРЕЩЕНА (даже для экшенов: подписка на весь стор даёт лишние ре-рендеры).
- useShallow — НЕ использовать (избыточный боилерплейт).

### Порядок хуков в React-компоненте
Строго в таком порядке:
1. `useStore` (Zustand-подписки)
2. `useState`
3. `useRef`
4. `useMemo`
5. `useCallback`
6. `useEffect`

Остальные хуки (`useReducer`, `useContext`, `useLayoutEffect` и пр.) допустимы, но используются редко — порядок определять по ситуации.