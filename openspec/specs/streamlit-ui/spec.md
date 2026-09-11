# streamlit-ui Specification

## Purpose

Опциональная визуализация точек разбора на карте Яндекс в Streamlit: expander в отчёте, два viz-ключа, координаты из 2ГИС или серверный геокод. Не влияет на сбор полей, scoring и SQLite payload.

## Requirements

### Requirement: Опциональная карта Яндекс в expander отчёта
После сбора трёх точек или открытия сохранённого разбора интерфейс SHALL показать свёрнутый по умолчанию expander «Карта (Яндекс JS API, только просмотр)» с подписью, что блок не влияет на сбор полей и индекс. Без `YANDEX_MAPS_JS_API_KEY` система MUST показать подсказку добавить ключ и MUST NOT падать. Таблица, карточки, индекс и вывод модели SHALL работать независимо от наличия карты.

#### Scenario: Нет JS-ключа
- GIVEN разбор с тремя точками и пустой `YANDEX_MAPS_JS_API_KEY`
- WHEN пользователь открывает отчёт
- THEN expander карты есть
- THEN внутри подсказка про `YANDEX_MAPS_JS_API_KEY`
- THEN таблица полей видна

#### Scenario: Карта с координатами 2ГИС
- GIVEN три точки с заполненными `map_lat` и `map_lon` из 2ГИС и валидный `YANDEX_MAPS_JS_API_KEY`
- WHEN пользователь раскрывает expander
- THEN отображается HTML-виджет карты с метками
- THEN подпись «Меток на карте: N из N»

### Requirement: Два отдельных ключа Яндекса для визуализации
Система SHALL читать `YANDEX_MAPS_JS_API_KEY` только для подгрузки JavaScript API карт в браузере. Система SHALL читать `YANDEX_GEOCODER_API_KEY` только для серверного HTTP-геокода адреса или названия, если у точки нет `map_lat` / `map_lon`. Один ключ MUST NOT подменять другой. Система MUST NOT использовать `YANDEX_MAPS_API_KEY` (ключ сбора Places, удалён в `drop-yandex-maps-source`).

#### Scenario: Разные env-переменные
- GIVEN `YANDEX_MAPS_JS_API_KEY=js-key` и `YANDEX_GEOCODER_API_KEY=geo-key`
- WHEN читают ключи из окружения
- THEN JS-ключ равен `js-key`
- THEN ключ геокодера равен `geo-key`

#### Scenario: Нужен геокодер, ключа нет
- GIVEN точка без `map_lat` / `map_lon`, но с адресом
- AND пустой `YANDEX_GEOCODER_API_KEY`
- WHEN раскрывают expander карты
- THEN предупреждение про отдельный ключ API Геокодера
- THEN метки с координатами 2ГИС всё равно могут отображаться

### Requirement: Координаты меток из 2ГИС или геокодера
Для каждой точки отчёта система SHALL взять `map_lat` и `map_lon` из собранной записи (источник — 2ГИС). Если координат нет, система MAY один раз запросить Geocoder API по адресу (с префиксом «Москва,» при необходимости), затем по названию салона. Геокод MUST выполняться на сервере (`geocode-maps.yandex.ru`), не в браузере. HTTP-клиент геокодера MUST использовать те же `httpx_client_kwargs` из `proxy.py`, что и остальные исходящие запросы каркаса (`trust_env` истина), MUST NOT отключать прокси окружения (`trust_env=False`). Система MUST NOT записывать результат геокода в payload SQLite и MUST NOT менять поля сбора.

#### Scenario: Координаты уже в записи
- GIVEN `map_lat=55.75` и `map_lon=37.62` из 2ГИС
- WHEN строят маркеры
- THEN HTTP-геокод не вызывается
- THEN метка использует эти координаты

#### Scenario: Геокод по адресу
- GIVEN пустые `map_lat` / `map_lon` и адрес «ул. Примерная, 1»
- AND валидный `YANDEX_GEOCODER_API_KEY`
- WHEN разрешают координаты меток
- THEN один запрос к Geocoder с текстом «Москва, ул. Примерная, 1»
- THEN координаты попадают только в HTML карты

#### Scenario: Геокодер уважает прокси окружения
- GIVEN запрос Geocoder API
- WHEN собирают kwargs HTTP-клиента для геокода
- THEN kwargs совпадают с `httpx_client_kwargs()` из `proxy.py`
- THEN `trust_env` истина

### Requirement: Карта не влияет на сбор и scoring
Модуль визуализации (`yandex_viz.py`) MUST NOT импортироваться из `collect`, `score`, `maps_http` или `resolver` для сбора полей. Вызовы API Яндекса в этом capability MUST ограничиваться отображением в Streamlit. Отсутствие ключей, ошибка геокода или пустая карта MUST NOT менять индекс, таблицу полей и сохранённый JSON разбора.

#### Scenario: Сбор без ключей Яндекса
- GIVEN пустые viz-ключи и валидный `TWOGIS_API_KEY`
- WHEN пользователь разбирает три зацепки
- THEN поля карт заполняются только из 2ГИС
- THEN индекс считается без участия Яндекса

#### Scenario: Карта не пишет в SQLite
- GIVEN успешный геокод для отображения
- WHEN сохраняют разбор в SQLite
- THEN в payload нет полей координат от Яндекса
- THEN `map_lat` / `map_lon` остаются как после сбора 2ГИС

### Requirement: Начальный viewport подгоняется под метки
HTML карты SHALL центрировать и масштабировать вид так, чтобы все поставленные метки были видны. Для одной метки система SHALL использовать увеличенный zoom (около 15). Для нескольких меток система SHALL вызвать `setBounds` коллекции с отступом и MUST NOT опускать zoom ниже минимального порога (13), если API позволяет. Без меток система SHALL показать сообщение вместо карты.

#### Scenario: Три метки в Москве
- GIVEN три точки с координатами в пределах города
- WHEN рендерят карту
- THEN в HTML есть `setBounds` для коллекции меток
- THEN начальный center — среднее координат меток

#### Scenario: Одна метка
- GIVEN одна точка с координатами
- WHEN рендерят карту
- THEN карта центрируется на этой точке с zoom около 15

#### Scenario: Нет координат после геокода
- GIVEN ни одна точка не получила lat/lon
- WHEN строят HTML
- THEN текст «Метки не поставлены» без падения приложения

### Requirement: Безопасная вставка данных 2ГИС в HTML карты
HTML карты MUST NOT содержать сырую последовательность `</script>` из `title` или `address` внутри executable JavaScript. Точки SHALL сериализоваться в JSON и вставляться через `<script type="application/json">` с чтением `JSON.parse` на клиенте (MUST NOT `const POINTS = {payload}` внутри JS). После `json.dumps` система SHALL экранировать `<`, `>`, `&` как `\u003c`, `\u003e`, `\u0026` и/или заменить `"</"` так, чтобы HTML-парсер не закрывал скрипт. Содержимое `balloonContentHeader` и `balloonContentBody` MUST быть HTML-экранировано через `html.escape` на сервере до свойств метки.

#### Scenario: Script breakout в названии
- GIVEN точка с названием, содержащим `</script>`
- WHEN строят HTML карты
- THEN в разметке нет сырой последовательности `</script>` из названия внутри JS
- THEN точки читаются из JSON (`application/json` и/или `JSON.parse`), а не из сырого `const POINTS = {payload}`

#### Scenario: img onerror в адресе балуна
- GIVEN точка с адресом `<img src=x onerror=alert(1)>`
- WHEN строят HTML карты
- THEN содержимое балуна HTML-экранировано (`html.escape`)
- THEN в HTML нет незаэскейпленного `<img src=x onerror=`

### Requirement: Баннер падения сбора точки
Если у записи точки `collect_ok` ложь, интерфейс MUST показать предупреждение вида «Сбор точки X упал», где X — заголовок точки. Система MAY показать краткое `collect_error`. Stack trace MUST NOT выводиться в UI. Таблица полей и остальные точки SHALL оставаться на экране. Точки с `collect_ok` истина MUST NOT получать этот баннер, даже если поля «не найдено».

#### Scenario: Одна точка упала при сборе
- GIVEN три записи, у второй `collect_ok` ложь, `collect_error` с типом исключения, title «Студия Б»
- WHEN показывают отчёт
- THEN есть баннер «Сбор точки Студия Б упал»
- THEN нет traceback в интерфейсе
- THEN таблица полей видна

#### Scenario: Честно пустые поля без сбоя
- GIVEN точка со всеми полями «не найдено» и `collect_ok` истина
- WHEN показывают отчёт
- THEN баннера падения сбора для этой точки нет
