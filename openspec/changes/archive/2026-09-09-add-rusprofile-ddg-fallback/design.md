# Design: add-rusprofile-ddg-fallback

## Context

Официальный GET `egrul.nalog.ru` в живом прогоне не содержит ОГРН. Поиск rusprofile `/search` — 404. Карточка `https://www.rusprofile.ru/id/7301223` по демо-ОГРН открывается. DuckDuckGo HTML по запросу `1147746349552 site:rusprofile.ru/id` отдаёт эту ссылку первым результатом, но в выдаче бывают ложные хиты (совпадение куска цифр).

## Goals / Non-Goals

**Goals:** заполнить дату, статус, вид деятельности, когда ФНС молчит; без ключа; с паузой; сверка ОГРН; полка слабо.

**Non-Goals:** капча, зеркала, платный API, устойчивость 25% из агрегатора, ФССП, учредители.

## Decisions

- Каскад ЕГРЮЛ: официальная страница → если все три поля пустые и есть ОГРН → один GET DuckDuckGo HTML → до пяти GET `rusprofile.ru/id/{n}` с паузой до каждого paced URL после первого.
- URL поиска: `https://html.duckduckgo.com/html/?q={quote_plus(ОГРН + " site:rusprofile.ru/id")}`.
- Ссылку принимать только шаблона `rusprofile.ru/id/{digits}` (не `/person/`, не `/ip/` для 13-значного ОГРН). Тело карточки MUST содержать тот же ОГРН.
- `Trust.WEAK` + подпись «слабо» в таблице. Федресурс и КАД по-прежнему только свои URL.
- Pacer в `CollectDeps`: в приложении `SleepPacer(3.0)`, в тестах запись вызовов без `time.sleep`. Пауза между paced-запросами (DuckDuckGo и rusprofile) на весь `collect_three`.
- Капча DuckDuckGo или rusprofile: `blocked` → стоп fallback, поля «не найдено». Следующие `/id/` после blocked не долбить.
- Разбор полей — тот же `LegalParser.parse_egrul`. Новых зависимостей нет.

## Risks / Trade-offs

- HTML DuckDuckGo и вёрстка rusprofile могут смениться — тогда снова «не найдено», без обхода.
- Соглашение rusprofile запрещает парсинг; это осознанный fallback без ключа, не первоисточник.
- Пауза 3 с × (поиск + карточки) × 3 салона удлиняет прогон; это плата за капчу.
