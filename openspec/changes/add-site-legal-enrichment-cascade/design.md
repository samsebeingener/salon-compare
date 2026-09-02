# Design: add-site-legal-enrichment-cascade

## Decisions

- `ddg_site_search_url(title, address)` — DuckDuckGo HTML, пауза как у rusprofile.
- `ddg_site_urls(html)` — парсить `class="result__a"`, фильтр агрегаторов/соцсетей.
- `internal_legal_links(html, base)` — same-host ссылки по ключевым словам path.
- `rbc_company_card_url(search_html, ogrn)` + `rbc_website(html)` — блок «Сайт» на id-странице.
- `_collect_site`: бюджет 10 GET; about и ogrn собираются отдельно (не выходить до обхода legal-ссылок).
- `labeled_inn` — только с подписью «ИНН».
