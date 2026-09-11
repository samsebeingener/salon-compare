## ADDED Requirements

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
