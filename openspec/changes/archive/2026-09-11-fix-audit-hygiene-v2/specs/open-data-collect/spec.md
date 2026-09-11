## ADDED Requirements

### Requirement: Лимит размера HTML fetch
Один GET или POST открытой HTML-страницы MUST отбрасывать ответ, если `Content-Length` больше 2_000_000 байт или фактическое тело больше 2_000_000 байт. В этом случае статус fetch MUST быть «пусто» (`empty`), тело MUST быть пустой строкой, капчу MUST NOT разбирать. Лимит SHALL действовать и без заголовка `Content-Length`, по длине загруженного тела. Ответ в пределах лимита SHALL разбираться как сейчас (ok / blocked / empty по статусу и маркерам).

#### Scenario: Content-Length больше лимита
- GIVEN HTTP 200 и `Content-Length` больше 2_000_000
- WHEN делают HTML fetch
- THEN статус `empty`
- THEN тело пустое
- THEN текст ответа не идёт в парсер полей

#### Scenario: Тело больше лимита без Content-Length
- GIVEN HTTP 200 без `Content-Length` и тело больше 2_000_000 байт
- WHEN делают HTML fetch
- THEN статус `empty`
- THEN тело пустое

#### Scenario: Страница в пределах лимита
- GIVEN HTTP 200, тело меньше 2_000_000 байт, без капчи
- WHEN делают HTML fetch
- THEN статус `ok`
- THEN тело доступно парсеру
