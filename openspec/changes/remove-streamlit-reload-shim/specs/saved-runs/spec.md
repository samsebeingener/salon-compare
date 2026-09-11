## ADDED Requirements

### Requirement: Бандл разбора одним чтением JSON
Загрузка сохранённого разбора по id SHALL один раз прочитать и разобрать JSON payload и вернуть строки, usage и вердикт вместе. Отдельные загрузчики строк, usage и вердикта MAY остаться как обёртки над тем же чтением. Формат payload `{rows, usage, verdict}` MUST NOT меняться. Ключи API MUST NOT попадать в ответ загрузчика из `.env`.

#### Scenario: Одно чтение на бандл
- GIVEN запись SQLite с тремя точками, объектом usage и объектом вердикта
- WHEN загружают бандл по id
- THEN строки, usage и вердикт совпадают с сохранёнными
- THEN JSON payload разбирают один раз на этот вызов

#### Scenario: Обёртки не дублируют смысл
- GIVEN тот же id
- WHEN вызывают загрузчик только строк, только usage или только вердикта
- THEN результат совпадает с соответствующей частью бандла
- THEN отсутствие usage или вердикта в payload даёт пусто для этой части, не падает

#### Scenario: Старый payload-список
- GIVEN JSON разбора — массив точек без обёртки usage/verdict
- WHEN загружают бандл
- THEN строки читаются
- THEN usage и вердикт пусты

### Requirement: Coerce только для старой схемы JSON
При чтении JSON из SQLite система SHALL подставлять отсутствующие поля схемы точки (`map_lat`/`map_lon`, `efrsb`, `collect_ok`/`collect_error` и аналогичные дефолты модели) через coerce / `as_sourced_field`. Эти хелперы MUST NOT существовать ради смены класса после `importlib.reload`. Запись текущего формата SHALL читаться без обязательного «лечения» identity класса.

#### Scenario: Старый JSON без координат и флагов сбора
- GIVEN payload точки без `map_lat`, `efrsb` и `collect_ok`
- WHEN загружают разбор из SQLite
- THEN запись поднимается
- THEN координаты пусты, `efrsb` — поле по умолчанию, `collect_ok` истина

#### Scenario: Актуальный JSON без reload-хака
- GIVEN payload с полным набором полей текущей модели
- WHEN загружают разбор
- THEN поля совпадают без перезагрузки модуля collect
