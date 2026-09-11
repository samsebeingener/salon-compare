# Design: add-llm-field-extract

## Context

Сбор уже заполняет `PlaceRecord` каскадом API/HTML/реестров. Модель сейчас только пишет вердикт в `report.py`. Ревьюер ждёт LLM-извлечение признаков; пользователь выбрал **гибрид**, не полный extract.

## Goals / Non-Goals

**Goals:**

- Добирать только MISSING из whitelist после парсеров.
- Один `complete` на точку, если есть дыры.
- Валидация JSON через Pydantic; мусор → без записи.
- Учесть токены добора в накопленном usage разбора.
- Точка вызова: Streamlit `app.py` после `collect_three`, не `maps_http`.

**Non-Goals:**

- Сырой HTML → целиком новый `PlaceRecord`.
- Повторный добор при cache-hit (`wrote=False`).
- Обход капчи, новые GET, правка `maps_http.py`.

## Decisions

- **Whitelist v1:** `EXTRACT_FIELDS = ("site_about", "egrul_activity")`. `hours` MAY добавить в тот же `ExtractPatch` и тот же вызов; отдельный `complete` на часы запрещён.
- **`ExtractPatch`:** опциональные `str` под имена whitelist плюс опциональный `source_quote` (цитата для отладки, не поле отчёта).
- **`gaps_for(row)`:** имена из `EXTRACT_FIELDS`, где `trust` is MISSING или `value` is None. Уже WEAK/FOUND с текстом — не gap.
- **`parse_extract(raw)`:** снять markdown fence как `parse_verdict`; `json.loads` + `model_validate`; иначе `None`.
- **`apply_extract(row, patch)`:** копирует запись; для каждого gap, если в патче непустая строка — `SourcedField(value=..., trust=WEAK, source_url="модель")`. Пустая строка и чужие ключи игнорируются. FOUND не перезаписывается.
- **`extract_missing(row, llm, context)`:** нет gaps → `(row, LlmUsage())` без `complete`. Иначе один prompt: верни JSON только запрошенных полей из `context`. Затем parse → apply → `usage = llm.last_usage()`. Нет сети в модуле.
- **Контекст в app:** уже известные строки (title, `site_about` если есть, тексты `egrul_*`). Не сырой повторный HTML.
- **Ключ:** `make_llm()` дал `NullLlm` → добор не вызывать.
- **Когда:** только если `rows_from_cache` вернул `wrote=True` (свежий сбор). Кэш сессии без нового collect — без второго extract.
- **Сбой сбора:** `collect_ok` ложь → эту точку не кормить модели (каркас пустых полей, токены не жечь).
- **Оркестрация:** цикл по трём точкам в `app.py`; после каждой успешной попытки `session["llm_usage"] = merge_usage(...)` и `save_run_usage` по тем же правилам, что вердикт (пустой usage не затирает сумму).
- **Развилка стоимости:** если реализация скатывается к одному вызову на поле — СТОП, не плодить N запросов.

## Risks / Trade-offs

- [Тонкий context] → модель может вернуть пусто/мусор → поля остаются MISSING; это честно, не выдумка парсера.
- [WEAK «модель» vs WEAK rusprofile] → полка та же; отличает `source_url`.
- [Extract до вердикта] → usage разбора = добор + вердикт; экран «Расход» уже умеет сумму.
- [Cache] → добор один раз на новый collect; правки ячеек не перезапускают extract.
