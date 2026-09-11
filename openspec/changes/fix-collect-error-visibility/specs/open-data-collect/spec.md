## MODIFIED Requirements

### Requirement: Три точки независимо
Сбой или пустые поля одной точки MUST NOT отменять сбор двух других. Система SHALL вернуть запись по каждой из трёх точек. Если сбор одной точки прервался исключением, эта запись MUST быть помечена как сбой сбора (`collect_ok` ложь и краткое `collect_error`), MUST NOT выглядеть как успешный прогон со всеми полями «не найдено» без следа сбоя. Две другие точки SHALL собираться как обычно.

#### Scenario: Один источник молчит у одной точки
- GIVEN у первой точки API 2ГИС пуст, у второй и третьей API полон
- WHEN собирают три точки
- THEN первая точка остаётся в результате с дырками «не найдено» где пусто
- THEN у первой точки `collect_ok` истина (нет исключения)
- THEN вторая и третья точки собраны
- THEN запуск не останавливается целиком

#### Scenario: Исключение на одной точке
- GIVEN `collect_place` для второй точки поднимает `TypeError`, первая и третья завершаются без исключения
- WHEN собирают три точки
- THEN в результате три записи
- THEN у второй `collect_ok` ложь и непустое `collect_error` с типом исключения
- THEN у первой и третьей `collect_ok` истина
- THEN прогон не останавливается целиком

## ADDED Requirements

### Requirement: Сбой сбора виден в записи точки
`PlaceRecord` SHALL иметь `collect_ok` (по умолчанию истина) и `collect_error` (по умолчанию пусто). При исключении вокруг сбора точки система SHALL залогировать traceback (`logging.exception`) и вернуть каркас пустых полей с `collect_ok` ложь. `collect_error` MUST содержать тип исключения и краткий текст, MUST NOT содержать stack trace. Старый JSON без этих ключей SHALL разбираться через `coerce_place_record` как `collect_ok` истина и `collect_error` пусто.

#### Scenario: Исключение в collect_place
- GIVEN сбор точки поднимает исключение
- WHEN обрабатывают сбой в `collect_three`
- THEN запись точки с пустыми полями «не найдено»
- THEN `collect_ok` ложь
- THEN `collect_error` без traceback
- THEN в логе есть exception с traceback

#### Scenario: Старый payload без полей сбоя
- GIVEN JSON точки без `collect_ok` и `collect_error`
- WHEN вызывают `coerce_place_record`
- THEN запись загружается
- THEN `collect_ok` истина
- THEN `collect_error` пусто

### Requirement: Пустая карточка API не маскирует баг кода
Загрузка карточки 2ГИС MAY вернуть пустые поля, если API не ответил или сеть недоступна (`httpx`/`OSError`): это «не найдено», `collect_ok` остаётся истиной. Ошибка кода при разборе карточки (`TypeError`, `AttributeError` и прочие не-сетевые исключения) MUST всплыть из безопасной обёртки карточки в сбор точки и MUST быть помечена как сбой сбора, а не как пустая карточка без флага.

#### Scenario: Сеть при fetch карточки
- GIVEN `fetch_card` поднимает ошибку HTTP-клиента или `OSError`
- WHEN собирают точку
- THEN поля карт — «не найдено»
- THEN `collect_ok` истина
- THEN сбой залогирован

#### Scenario: Баг разбора карточки
- GIVEN `fetch_card` поднимает `TypeError` или `AttributeError`
- WHEN собирают три точки
- THEN эта точка с `collect_ok` ложь
- THEN исключение не превращено в молчаливую пустую `MapCard` без флага сбоя
