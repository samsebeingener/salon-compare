"""Три зацепки. Данные карт и таблица по точкам появятся позже."""

import streamlit as st

from salon_compare.intake import PassthroughResolver, resolve_intake

st.set_page_config(page_title="salon-compare", layout="centered")
st.title("salon-compare")
st.write("Введите три зацепки — по одной на точку. Сбор данных карт ещё не включён.")

hook_one = st.text_input("Зацепка 1")
hook_two = st.text_input("Зацепка 2")
hook_three = st.text_input("Зацепка 3")

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
