"""Три зацепки, подтверждение карточек со ссылками, таблица полей."""

from collections.abc import Callable
from typing import cast

import streamlit as st

from salon_compare.collect import (
    CollectDeps,
    EmptyParser,
    PlaceRecord,
    SleepPacer,
    SourcedField,
    Trust,
    collect_three,
)
from salon_compare.html_fetch import HttpxHtmlFetcher
from salon_compare.intake import (
    IntakeStatus,
    VenueCandidate,
    apply_slot_choices,
    resolve_intake,
)
from salon_compare.legal import LegalOrg, MarkerLegalParser
from salon_compare.maps_http import map_api_from_env
from salon_compare.resolver import MapsSearchResolver
from salon_compare.store import (
    collect_cache_key,
    list_runs,
    load_run,
    rows_from_cache,
    save_run,
)

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
            st.session_state.pop("outcome", None)

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
            return f"{item.title} — {item.source_url}"
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
    return MapsSearchResolver(map_api_from_env("twogis"), map_api_from_env("yandex"))


def _show_table(rows: list[PlaceRecord]) -> None:
    st.subheader("Поля точек")
    table: dict[str, list[str]] = {
        "Поле": [
            "Яндекс рейтинг",
            "Яндекс отзывы",
            "2ГИС рейтинг",
            "2ГИС отзывы",
            "Адрес",
            "Соседи 500 м",
            "Рейтинг соседей",
            "Сайт «о нас»",
            "ЕГРЮЛ дата",
            "ЕГРЮЛ статус",
            "ЕГРЮЛ деятельность",
            "Федресурс",
            "КАД",
        ]
    }
    for row in rows:
        table[row.title] = [
            _cell(row.yandex_rating),
            _cell(row.yandex_review_count),
            _cell(row.twogis_rating),
            _cell(row.twogis_review_count),
            _cell(row.address),
            _cell(row.neighbor_count),
            _cell(row.neighbor_vs),
            _cell(row.site_about),
            _legal_cell(row, row.egrul_registered_at),
            _legal_cell(row, row.egrul_status),
            _legal_cell(row, row.egrul_activity),
            _legal_cell(row, row.fedresurs),
            _legal_cell(row, row.kad),
        ]
    st.table(table)


if st.button("Разобрать зацепки"):
    st.session_state.pop("saved_rows", None)
    st.session_state["outcome"] = resolve_intake(
        [hook_one, hook_two, hook_three],
        _resolver(),
    )
    st.session_state["legal_choices"] = {}

outcome = st.session_state.get("outcome")
saved_rows = st.session_state.get("saved_rows")
if saved_rows:
    st.write("Сохранённый разбор, нового поиска нет.")
    _show_table(saved_rows)
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
                st.write(f"{item.title} — {item.source_url}")
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
                    yandex=map_api_from_env("yandex"),
                    twogis=map_api_from_env("twogis"),
                    html=HttpxHtmlFetcher(),
                    parser=EmptyParser(),
                    legal=MarkerLegalParser(),
                    pacer=SleepPacer(3.0),
                ),
                legal_choices=legal_choices,
            )

        rows, wrote = rows_from_cache(cache, key, _collect)
        if wrote:
            save_run(rows)
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
        _show_table(rows)
    else:
        for slot in outcome.candidates_by_slot:
            for candidate in slot:
                st.write(f"{candidate.title} — {candidate.source_url}")
