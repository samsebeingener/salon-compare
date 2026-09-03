"""Три зацепки, подтверждение карточек со ссылками, таблица полей."""

from collections.abc import Callable
from typing import cast

import streamlit as st

from salon_compare.collect import (
    CollectDeps,
    PlaceRecord,
    SleepPacer,
    SourcedField,
    Trust,
    collect_three,
)
from salon_compare.html_fetch import HttpxHtmlFetcher
from salon_compare.html_parse import OpenHtmlParser
from salon_compare.intake import (
    IntakeStatus,
    VenueCandidate,
    apply_slot_choices,
    candidate_label,
    resolve_intake,
)
from salon_compare.legal import LegalOrg, MarkerLegalParser
from salon_compare.llm import LlmUsage, NullLlm, estimate_usd, make_llm
from salon_compare.load_env import load_project_env
from salon_compare.maps_http import map_api_from_env
from salon_compare.report import (
    EDITABLE_FIELDS,
    FIELD_LABELS,
    ModelVerdict,
    card_payload,
    complete_verdict,
    mark_unreliable,
    patch_field,
    rows_fingerprint,
)
from salon_compare.resolver import MapsSearchResolver, RbcBrandLookup
from salon_compare.score import score_place
from salon_compare.store import (
    collect_cache_key,
    list_runs,
    load_run,
    load_run_usage,
    rows_from_cache,
    save_run,
    save_run_usage,
)

load_project_env()

st.set_page_config(page_title="salon-compare", layout="centered")
st.title("salon-compare")
st.write("Введите три зацепки — по одной на точку.")

_saved = list_runs()
if _saved:
    _ids = [item[0] for item in _saved]
    _labels = {item[0]: f"#{item[0]} · {item[1]}" for item in _saved}
    _picked = st.selectbox(
        "Сохранённые разборы",
        _ids,
        format_func=lambda run_id: _labels[int(run_id)],
    )
    if st.button("Открыть сохранённый"):
        loaded = load_run(int(_picked))
        if loaded:
            st.session_state["saved_rows"] = loaded
            st.session_state["working_rows"] = list(loaded)
            st.session_state["working_key"] = (
                "saved",
                tuple(row.venue_id for row in loaded),
            )
            st.session_state["llm_usage"] = load_run_usage(int(_picked))
            st.session_state["run_id"] = int(_picked)
            st.session_state.pop("outcome", None)
            st.session_state.pop("llm_fp", None)

hook_one = st.text_input("Зацепка 1")
hook_two = st.text_input("Зацепка 2")
hook_three = st.text_input("Зацепка 3")


def _cell(field: SourcedField) -> str:
    if field.trust is Trust.MISSING or field.value is None:
        return "не найдено"
    link = f" · {field.source_url}" if field.source_url else ""
    if field.trust is Trust.WEAK:
        return f"{field.value} · слабо{link}"
    if field.trust is Trust.FOUND:
        return f"{field.value}{link}" if field.source_url else str(field.value)
    unreachable: Trust = field.trust
    raise ValueError(unreachable)


def _card_label(slot: list[VenueCandidate], venue_id: str) -> str:
    for item in slot:
        if item.venue_id == venue_id:
            return candidate_label(item)
    return venue_id


def _radio_format(slot: list[VenueCandidate]) -> Callable[[str], str]:
    def _fmt(venue_id: str) -> str:
        return _card_label(slot, venue_id)

    return _fmt


def _legal_cell(row: PlaceRecord, field: SourcedField) -> str:
    if row.legal_candidates:
        links = " · ".join(
            f"{item.title} — {item.source_url}" for item in row.legal_candidates
        )
        return f"уточните юрлицо · {links}"
    return _cell(field)


def _org_label(orgs: tuple[LegalOrg, ...], ogrn: str) -> str:
    for item in orgs:
        if item.ogrn == ogrn:
            return f"{item.title} — {item.source_url}"
    return ogrn


def _org_format(orgs: tuple[LegalOrg, ...]) -> Callable[[str], str]:
    def _fmt(ogrn: str) -> str:
        return _org_label(orgs, ogrn)

    return _fmt


def _resolver() -> MapsSearchResolver:
    return MapsSearchResolver(
        map_api_from_env(),
        RbcBrandLookup(HttpxHtmlFetcher()),
    )


def _show_table(rows: list[PlaceRecord]) -> None:
    st.subheader("Поля точек")
    table: dict[str, list[str]] = {
        "Поле": [
            "2ГИС рейтинг",
            "2ГИС отзывы",
            "Часы",
            "Район",
            "Метро",
            "2ГИС последний отзыв",
            "2ГИС отзывы за 90 дней",
            "2ГИС плюс/минус",
            "Адрес",
            "Соседи 500 м",
            "Соседи выше/ниже",
            "Сайт «о нас»",
            "ЕГРЮЛ/ЕГРИП дата",
            "ЕГРЮЛ/ЕГРИП статус",
            "ЕГРЮЛ/ЕГРИП деятельность",
            "Индекс 50/25/25",
            "Индекс пояснение",
        ]
    }
    for row in rows:
        scored = score_place(row)
        index_cell = "не найдено" if scored.index is None else str(scored.index)
        heading = f"{row.title} · недостоверный" if row.unreliable else row.title
        table[heading] = [
            _cell(row.twogis_rating),
            _cell(row.twogis_review_count),
            _cell(row.hours),
            _cell(row.district),
            _cell(row.metro),
            _cell(row.twogis_last_review),
            _cell(row.twogis_reviews_90d),
            _cell(row.twogis_plus_minus),
            _cell(row.address),
            _cell(row.neighbor_count),
            _cell(row.neighbor_vs),
            _cell(row.site_about),
            _legal_cell(row, row.egrul_registered_at),
            _legal_cell(row, row.egrul_status),
            _legal_cell(row, row.egrul_activity),
            index_cell,
            scored.note,
        ]
    st.table(table)
    st.caption("Ориентир по формуле, не инвестиционный совет.")


def _working_rows(rows: list[PlaceRecord], key: object) -> list[PlaceRecord]:
    if st.session_state.get("working_key") != key:
        st.session_state["working_rows"] = list(rows)
        st.session_state["working_key"] = key
        st.session_state.pop("llm_fp", None)
    current = st.session_state.get("working_rows")
    if not isinstance(current, list) or not current:
        st.session_state["working_rows"] = list(rows)
        return list(rows)
    typed = [item for item in current if isinstance(item, PlaceRecord)]
    if not typed:
        st.session_state["working_rows"] = list(rows)
        return list(rows)
    return typed


def _replace_working(index: int, row: PlaceRecord) -> None:
    current = list(st.session_state.get("working_rows", []))
    if index < 0 or index >= len(current):
        return
    current[index] = row
    st.session_state["working_rows"] = current
    st.session_state.pop("llm_fp", None)
    saved = st.session_state.get("saved_rows")
    if isinstance(saved, list) and len(saved) == len(current):
        st.session_state["saved_rows"] = current


def _show_cards(rows: list[PlaceRecord]) -> None:
    st.subheader("Карточки")
    for row in rows:
        scored = score_place(row)
        card = card_payload(row, scored)
        mark = " · недостоверный" if card["unreliable"] else ""
        index_text = "не найдено" if card["index"] is None else str(card["index"])
        st.markdown(f"**{card['title']}**{mark}")
        st.write(f"Индекс: {index_text}. {card['note']}")
        for item in card["fields"]:
            st.write(f"{item['label']}: {item['text']}")
        if card["missing"]:
            st.write("Не нашли: " + ", ".join(card["missing"]))


def _show_corrections(rows: list[PlaceRecord]) -> None:
    st.subheader("Правки")
    labels = dict(FIELD_LABELS)
    picked = st.selectbox(
        "Точка",
        range(len(rows)),
        format_func=lambda index: rows[int(index)].title,
        key="edit-venue",
    )
    field_name = st.selectbox(
        "Поле",
        list(EDITABLE_FIELDS),
        format_func=lambda name: labels[str(name)],
        key="edit-field",
    )
    raw = st.text_input("Новое значение", key="edit-value")
    left, right = st.columns(2)
    if left.button("Поправить поле") and picked is not None and field_name:
        updated = patch_field(rows[int(picked)], str(field_name), raw)
        _replace_working(int(picked), updated)
        st.rerun()
    if right.button("Пометить недостоверным") and picked is not None:
        _replace_working(int(picked), mark_unreliable(rows[int(picked)]))
        st.rerun()


def _show_verdict(rows: list[PlaceRecord]) -> None:
    st.subheader("Вывод модели")
    st.caption("текст модели, не инвестиционный совет")
    fingerprint = rows_fingerprint(rows)
    if st.session_state.get("llm_fp") != fingerprint:
        llm = make_llm()
        st.session_state["llm_kind"] = type(llm).__name__
        st.session_state["llm_verdict"] = complete_verdict(rows, llm)
        usage = llm.last_usage()
        if usage.total_tokens is not None:
            st.session_state["llm_usage"] = usage
            run_id = st.session_state.get("run_id")
            if isinstance(run_id, int):
                save_run_usage(run_id, usage)
        elif st.session_state.get("llm_usage") is None:
            st.session_state["llm_usage"] = usage
        st.session_state["llm_fp"] = fingerprint
    verdict = st.session_state.get("llm_verdict")
    kind = st.session_state.get("llm_kind")
    if not isinstance(verdict, ModelVerdict) and kind == NullLlm.__name__:
        st.write("вывод модели не найден (нет ключа)")
        return
    if not isinstance(verdict, ModelVerdict):
        st.write("вывод модели не разобран")
        return
    st.write(f"Интереснее: {verdict.interesting}")
    st.write(f"Чем лучше: {verdict.why_better}")
    st.write(f"Сломается, если: {verdict.breaks_if}")
    if verdict.compared_index is not None:
        st.write(f"Индекс в выводе: {verdict.compared_index}")


def _show_usage() -> None:
    st.subheader("Расход")
    usage = st.session_state.get("llm_usage")
    if not isinstance(usage, LlmUsage):
        st.write("токены не найдены")
        return
    if usage.total_tokens is None:
        st.write("токены не найдены")
    else:
        st.write(f"Токены: {usage.total_tokens}")
        if usage.prompt_tokens is not None or usage.completion_tokens is not None:
            prompt = (
                usage.prompt_tokens if usage.prompt_tokens is not None else "не найдено"
            )
            completion = (
                usage.completion_tokens
                if usage.completion_tokens is not None
                else "не найдено"
            )
            st.write(f"Ввод / выход: {prompt} / {completion}")
    if usage.cost is not None:
        st.write(f"Стоимость (из ответа модели): ${usage.cost}")
    else:
        usd = estimate_usd(usage)
        if usd is None:
            st.write("стоимость не найдена")
        else:
            st.write(f"Стоимость (оценка по тарифу): ${usd}")


def _show_report(rows: list[PlaceRecord]) -> None:
    _show_table(rows)
    _show_cards(rows)
    _show_corrections(rows)
    _show_verdict(rows)
    _show_usage()


if st.button("Разобрать зацепки"):
    st.session_state.pop("saved_rows", None)
    st.session_state.pop("working_rows", None)
    st.session_state.pop("working_key", None)
    st.session_state.pop("row_cache", None)
    st.session_state.pop("llm_fp", None)
    st.session_state.pop("llm_usage", None)
    st.session_state.pop("run_id", None)
    st.session_state["outcome"] = resolve_intake(
        [hook_one, hook_two, hook_three],
        _resolver(),
    )
    st.session_state["legal_choices"] = {}

outcome = st.session_state.get("outcome")
saved_raw = st.session_state.get("saved_rows")
saved_rows = (
    [item for item in saved_raw if isinstance(item, PlaceRecord)]
    if isinstance(saved_raw, list)
    else []
)
if saved_rows:
    st.write("Сохранённый разбор, нового поиска нет.")
    display = _working_rows(
        saved_rows,
        ("saved", tuple(row.venue_id for row in saved_rows)),
    )
    _show_report(display)
elif outcome is not None:
    st.write(outcome.message)
    for index, hook in enumerate(outcome.classified, start=1):
        st.write(f"{index}. {hook.kind.value}: {hook.raw.strip()}")
    if outcome.status is IntakeStatus.NEED_DISAMBIGUATION:
        choices: dict[int, str] = {}
        for index, slot in enumerate(outcome.candidates_by_slot):
            st.markdown(f"Зацепка {index + 1}")
            if not slot:
                st.write("На картах ничего не нашли. Уточните зацепку.")
            elif len(slot) == 1:
                item = slot[0]
                st.write(candidate_label(item))
            else:
                options = [item.venue_id for item in slot]
                picked = st.radio(
                    "Выберите карточку по ссылке",
                    options,
                    format_func=_radio_format(slot),
                    key=f"pick-{index}",
                )
                if picked is not None:
                    choices[index] = str(picked)
        if st.button("Подтвердить точки"):
            st.session_state["outcome"] = apply_slot_choices(outcome, choices)
            st.rerun()
    elif outcome.status is IntakeStatus.READY and outcome.chosen_venues:
        legal_choices: dict[str, str] = st.session_state.setdefault("legal_choices", {})
        cache = cast(
            dict[object, list[PlaceRecord]],
            st.session_state.setdefault("row_cache", {}),
        )
        venues = outcome.chosen_venues
        classified = outcome.classified
        key = collect_cache_key(
            [venue.venue_id for venue in venues],
            legal_choices,
        )

        def _collect() -> list[PlaceRecord]:
            return collect_three(
                venues,
                classified,
                CollectDeps(
                    twogis=map_api_from_env(),
                    html=HttpxHtmlFetcher(),
                    parser=OpenHtmlParser(),
                    legal=MarkerLegalParser(),
                    pacer=SleepPacer(3.0),
                ),
                legal_choices=legal_choices,
            )

        rows, wrote = rows_from_cache(cache, key, _collect)
        if wrote:
            st.session_state["run_id"] = save_run(rows)
        pending = [row for row in rows if row.legal_candidates]
        if pending:
            st.write("Несколько юрлиц. Выберите запись по ссылке. Сами не выбираем.")
            picked_legal: dict[str, str] = {}
            for row in pending:
                options = [item.ogrn for item in row.legal_candidates]
                chosen = st.radio(
                    f"Юрлицо: {row.title}",
                    options,
                    format_func=_org_format(row.legal_candidates),
                    key=f"legal-{row.venue_id}",
                )
                if chosen is not None:
                    picked_legal[row.venue_id] = str(chosen)
            if st.button("Подтвердить юрлицо"):
                legal_choices.update(picked_legal)
                st.session_state["legal_choices"] = legal_choices
                st.rerun()
        display = _working_rows(rows, key)
        _show_report(display)
    else:
        for slot in outcome.candidates_by_slot:
            for candidate in slot:
                st.write(candidate_label(candidate))
