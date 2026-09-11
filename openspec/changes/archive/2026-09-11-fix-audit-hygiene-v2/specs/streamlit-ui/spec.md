## MODIFIED Requirements

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
