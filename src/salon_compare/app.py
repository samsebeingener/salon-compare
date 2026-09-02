"""Три зацепки, подтверждение карточек со ссылками, таблица полей."""

from collections.abc import Callable

import streamlit as st

from salon_compare.collect import (
    CollectDeps,
    EmptyParser,
    PlaceRecord,
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
from salon_compare.maps_http import map_api_from_env
from salon_compare.resolver import MapsSearchResolver

st.set_page_config(page_title="salon-compare", layout="centered")
st.title("salon-compare")
st.write("Введите три зацепки — по одной на точку.")

hook_one = st.text_input("Зацепка 1")
hook_two = st.text_input("Зацепка 2")
hook_three = st.text_input("Зацепка 3")


def _cell(field: SourcedField) -> str:
    if field.trust is Trust.MISSING or field.value is None:
        return "не найдено"
    if field.source_url:
        return f"{field.value} · {field.source_url}"
    return str(field.value)


def _card_label(slot: list[VenueCandidate], venue_id: str) -> str:
    for item in slot:
        if item.venue_id == venue_id:
            return f"{item.title} — {item.source_url}"
    return venue_id


def _radio_format(slot: list[VenueCandidate]) -> Callable[[str], str]:
    def _fmt(venue_id: str) -> str:
        return _card_label(slot, venue_id)

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
        ]
    st.table(table)


if st.button("Разобрать зацепки"):
    st.session_state["outcome"] = resolve_intake(
        [hook_one, hook_two, hook_three],
        _resolver(),
    )

outcome = st.session_state.get("outcome")
if outcome is not None:
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
                choices[index] = str(picked) if picked is not None else options[0]
        if st.button("Подтвердить точки"):
            st.session_state["outcome"] = apply_slot_choices(outcome, choices)
            st.rerun()
    elif outcome.status is IntakeStatus.READY and outcome.chosen_venues:
        rows = collect_three(
            outcome.chosen_venues,
            outcome.classified,
            CollectDeps(
                yandex=map_api_from_env("yandex"),
                twogis=map_api_from_env("twogis"),
                html=HttpxHtmlFetcher(),
                parser=EmptyParser(),
            ),
        )
        _show_table(rows)
    else:
        for slot in outcome.candidates_by_slot:
            for candidate in slot:
                st.write(f"{candidate.title} — {candidate.source_url}")
