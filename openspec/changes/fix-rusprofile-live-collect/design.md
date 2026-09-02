# Design: fix-rusprofile-live-collect

## Context

Прогон 2 сентября 2026 с ОГРН `1147746349552`: GET `html.duckduckgo.com` обрывается; POST с `q` даёт ссылки. Карточка rusprofile содержит публичные поля и внизу JSON `"has_captcha":true` для оплаты. На странице есть «6 ликвидированных связанных организаций».

## Goals / Non-Goals

**Goals:** тот же fallback без ключа реально заполняет дату/статус/ОКВЭД на живом HTML.

**Non-Goals:** решать капчу, слать cookie/TLS-отпечаток, заполнять КАД/Федресурс.

## Decisions

- `HttpxHtmlFetcher.get` для URL `html.duckduckgo.com` делает POST `application/x-www-form-urlencoded` с `q` из query. Остальные URL — GET. Каскад сбора не меняет порт `get(url)`.
- Перед поиском маркеров капчи вырезать пары `"has_captcha"` / `"disable_captcha"` и boolean. Маркеры `smartcaptcha`, `recaptcha`, `g-recaptcha`, `cloudflare`, голое `captcha` в форме остаются блокирующими.
- Статус: `ликвидированная организация` / `не действует` → не действует; иначе `действующая организация` / `действует` → действует. Не матчить `ликвидированных связанных`.
- Деятельность: искать `основной вид деятельности` раньше `оквэд`.

## Risks / Trade-offs

- POST DuckDuckGo тоже могут закрыть — тогда снова «не найдено».
- Если когда-нибудь вся карточка rusprofile станет за капчей без полей в HTML — честно пусто.
