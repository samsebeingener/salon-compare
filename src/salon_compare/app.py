"""Три зацепки и таблица найденных полей. Баллы привлекательности — позже."""

import streamlit as st

from salon_compare.collect import (
    CollectDeps,
    EmptyParser,
    SourcedField,
    Trust,
    collect_three,
)
from salon_compare.html_fetch import HttpxHtmlFetcher
from salon_compare.intake import IntakeStatus, PassthroughResolver, resolve_intake
from salon_compare.maps_http import map_api_from_env

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


if st.button("Разобрать зацепки"):
    outcome = resolve_intake(
        [hook_one, hook_two, hook_three],
        PassthroughResolver(),
    )
    st.write(outcome.message)
    for index, hook in enumerate(outcome.classified, start=1):
        st.write(f"{index}. {hook.kind.value}: {hook.raw.strip()}")
    for slot in outcome.candidates_by_slot:
        for candidate in slot:
            st.write(f"{candidate.title} — {candidate.source_url}")
    if outcome.status is IntakeStatus.READY and outcome.chosen_venues:
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
        st.subheader("Поля точек")
        table = {
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
