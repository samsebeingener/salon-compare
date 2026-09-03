"""Три зацепки, подтверждение карточек со ссылками, таблица полей."""

import importlib
from collections.abc import Callable
from typing import cast

import streamlit as st

import salon_compare.report as report
import salon_compare.store as store
from salon_compare.collect import (
    CollectDeps,
    PlaceRecord,
    SleepPacer,
    SourcedField,
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
from salon_compare.llm_log import log_path
from salon_compare.load_env import load_project_env
from salon_compare.maps_http import map_api_from_env
from salon_compare.resolver import MapsSearchResolver, RbcBrandLookup
from salon_compare.score import score_place

report = importlib.reload(report)
store = importlib.reload(store)
EDITABLE_FIELDS = report.EDITABLE_FIELDS
FIELD_LABELS = report.FIELD_LABELS
ModelVerdict = report.ModelVerdict
cell_help = report.cell_help
complete_verdict = report.complete_verdict
footnote_lines = report.footnote_lines
footnote_map = report.footnote_map
mark_unreliable = report.mark_unreliable
patch_field = report.patch_field
rows_fingerprint = report.rows_fingerprint
table_cell = report.table_cell
collect_cache_key = store.collect_cache_key
list_runs = store.list_runs
load_run = store.load_run
load_run_usage = store.load_run_usage
rows_from_cache = store.rows_from_cache
save_run = store.save_run
save_run_usage = store.save_run_usage
update_run = store.update_run

load_project_env()

st.set_page_config(page_title="salon-compare", layout="wide")
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


def _card_label(slot: list[VenueCandidate], venue_id: str) -> str:
    for item in slot:
        if item.venue_id == venue_id:
            return candidate_label(item)
    return venue_id


def _radio_format(slot: list[VenueCandidate]) -> Callable[[str], str]:
    def _fmt(venue_id: str) -> str:
        return _card_label(slot, venue_id)

    return _fmt


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


_CELL_EDIT_CSS = """
<style>
div[class*="st-key-cell-"] button [data-testid="stIconMaterial"] {
  opacity: 0;
  transition: opacity 0.12s ease;
}
div[class*="st-key-cell-"] button:hover [data-testid="stIconMaterial"],
div[class*="st-key-cell-"] button:focus-visible [data-testid="stIconMaterial"] {
  opacity: 1;
}
</style>
"""


def _show_footnotes(mapping: dict[str, int]) -> None:
    lines = footnote_lines(mapping)
    if not lines:
        return
    st.caption("Источники")
    for number, url in lines:
        if url.startswith("http://") or url.startswith("https://"):
            st.markdown(f"**[{number}]** [{url}]({url})")
        else:
            st.markdown(f"**[{number}]** {url}")


@st.dialog("Править поле")
def _edit_dialog(venue_index: int, field_name: str) -> None:
    current = st.session_state.get("working_rows")
    if not isinstance(current, list) or venue_index >= len(current):
        st.write("строка не найдена")
        return
    row = current[venue_index]
    if not isinstance(row, PlaceRecord) or field_name not in EDITABLE_FIELDS:
        st.write("поле не найдено")
        return
    labels = dict(FIELD_LABELS)
    field = getattr(row, field_name)
    if not isinstance(field, SourcedField) or field.value is None:
        shown = ""
    else:
        shown = str(field.value)
    st.write(f"{row.title} · {labels[field_name]}")
    raw = st.text_input(
        "Значение",
        value=shown,
        key=f"edit-raw-{venue_index}-{field_name}",
    )
    left, right = st.columns(2)
    if left.button("Сохранить", key=f"edit-save-{venue_index}-{field_name}"):
        _replace_working(venue_index, patch_field(row, field_name, raw))
        st.rerun()
    if right.button(
        "Пометить недостоверным",
        key=f"edit-bad-{venue_index}-{field_name}",
    ):
        _replace_working(venue_index, mark_unreliable(row))
        st.rerun()


def _show_table(rows: list[PlaceRecord]) -> None:
    st.subheader("Поля точек")
    st.markdown(_CELL_EDIT_CSS, unsafe_allow_html=True)
    notes = footnote_map(rows)
    widths = [1.35] + [1] * len(rows)
    header = st.columns(widths)
    header[0].markdown("**Поле**")
    for index, row in enumerate(rows):
        heading = f"{row.title} · недостоверный" if row.unreliable else row.title
        header[index + 1].markdown(f"**{heading}**")
    for name, label in FIELD_LABELS:
        cols = st.columns(widths)
        cols[0].write(label)
        for index, row in enumerate(rows):
            if cols[index + 1].button(
                table_cell(row, name, notes),
                key=f"cell-{index}-{name}",
                icon=":material/edit:",
                help=cell_help(row, name),
            ):
                _edit_dialog(index, name)
    scored_cols = st.columns(widths)
    scored_cols[0].write("Индекс 50/25/25")
    for index, row in enumerate(rows):
        scored = score_place(row)
        scored_cols[index + 1].write(
            "не найдено" if scored.index is None else str(scored.index)
        )
    _show_footnotes(notes)
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


def _persist_working(rows: list[PlaceRecord]) -> None:
    run_id = st.session_state.get("run_id")
    if isinstance(run_id, int):
        update_run(run_id, rows)
    else:
        st.session_state["run_id"] = save_run(rows)
    cache = st.session_state.get("row_cache")
    key = st.session_state.get("working_key")
    if isinstance(cache, dict) and key is not None:
        cache[key] = list(rows)


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
    _persist_working(current)


def _show_verdict(rows: list[PlaceRecord]) -> None:
    st.subheader("Вывод модели")
    st.caption("текст модели, не инвестиционный совет")
    fingerprint = rows_fingerprint(rows)
    if st.session_state.get("llm_fp") != fingerprint:
        llm = make_llm()
        st.session_state["llm_kind"] = type(llm).__name__
        st.session_state["llm_verdict"] = complete_verdict(rows, llm)
        st.session_state["llm_error"] = llm.last_error()
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
        error = st.session_state.get("llm_error")
        if isinstance(error, str) and error:
            st.write(f"вывод модели не разобран ({error})")
        else:
            st.write("вывод модели не разобран")
        st.caption(f"лог LLM: {log_path()}")
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
    _show_verdict(rows)
    _show_usage()


if st.button("Разобрать зацепки"):
    st.session_state.pop("saved_rows", None)
    st.session_state.pop("working_rows", None)
    st.session_state.pop("working_key", None)
    st.session_state.pop("row_cache", None)
    st.session_state.pop("llm_fp", None)
    st.session_state.pop("llm_usage", None)
    st.session_state.pop("llm_error", None)
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
