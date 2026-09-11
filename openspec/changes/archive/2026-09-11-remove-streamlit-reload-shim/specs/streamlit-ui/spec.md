## ADDED Requirements

### Requirement: Нет reload модулей на rerun Streamlit
Точка входа Streamlit MUST импортировать пакетные модули один раз обычным import. Система MUST NOT вызывать `importlib.reload` для `collect`, `store`, `score`, `report`, `proxy` или `llm` на rerun. Система MUST NOT проверять наличие `as_sourced_field` / `coerce_place_record` / полей модели как повод перезагрузить модуль.

#### Scenario: Исходник app без reload
- GIVEN файл точки входа Streamlit
- WHEN его читают как текст
- THEN нет `importlib.reload`
- THEN нет проверки «нужен reload collect» по отсутствию хелперов или полей модели

#### Scenario: Rerun не меняет identity классов ради UI
- GIVEN приложение запущено
- WHEN Streamlit делает rerun после нажатия кнопки
- THEN таблица полей и карточки работают без принудительной перезагрузки модулей

### Requirement: Открытие сохранённого разбора одним бандлом
По кнопке «Открыть сохранённый» интерфейс SHALL загрузить строки, usage LLM и вердикт одним чтением payload (`load_run_bundle` или эквивалент). Система MUST NOT делать три отдельных чтения одного JSON ради строк, usage и вердикта.

#### Scenario: Кнопка открыть сохранённый
- GIVEN запись в SQLite с тремя точками, usage и вердиктом
- WHEN нажимают «Открыть сохранённый»
- THEN на экране таблица полей из этой записи
- THEN usage и вердикт в сессии совпадают с payload
- THEN загрузчик HTML не вызывается
