# Design: add-html-freshness-and-usage

## Decisions

- Парсер: regex + JSON-LD `Review.datePublished` / `time[datetime]`, без BeautifulSoup. Капча по-прежнему отсекается fetch-слоем.
- 90 дней считаем от `as_of` по сохранённой дате отзыва, не парсером «сегодня».
- Плюс/минус — одна строка `N плюс / M минус`, только если обе цифры (или хотя бы одна) явно в HTML.
- `LlmUsage` из `usage` chat/completions: токены и `cost` провайдера (OpenRouter). Свои `$ / 1M` — только запас, если `cost` нет.
- Payload SQLite: `{"rows":[...],"usage":{...}}`; старый JSON-массив без `usage` читается.

## Non-Goals

Новые пакеты. Instagram. График по месяцам. Выдуманные цены моделей.
