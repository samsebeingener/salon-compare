"""Три зацепки, подтверждение карточек со ссылками, таблица полей."""

from collections.abc import Callable
from html import escape
from typing import cast

import streamlit as st

from salon_compare.collect import (
    CollectDeps,
    PlaceRecord,
    SleepPacer,
    as_sourced_field,
    coerce_place_record,
    collect_three,
)
from salon_compare.hooks import HOOK_KIND_LABELS
from salon_compare.html_fetch import HttpxHtmlFetcher
from salon_compare.html_parse import OpenHtmlParser
from salon_compare.intake import (
    MISSING_VENUE_ID,
    MISSING_VENUE_LABEL,
    IntakeStatus,
    VenueCandidate,
    apply_slot_choices,
    candidate_label,
    resolve_intake,
)
from salon_compare.legal import LegalOrg, MarkerLegalParser
from salon_compare.llm import (
    LlmUsage,
    NullLlm,
    estimated_usd_parts,
    format_usd_sum_line,
    make_llm,
    merge_usage,
)
from salon_compare.llm_extract import extract_context, extract_missing
from salon_compare.llm_log import log_path
from salon_compare.load_env import load_project_env
from salon_compare.maps_http import map_api_from_env
from salon_compare.report import (
    EDITABLE_FIELDS,
    FIELD_LABELS,
    ModelVerdict,
    card_payload,
    cell_help,
    complete_verdict,
    footnote_lines,
    footnote_map,
    mark_unreliable,
    patch_field,
    rows_fingerprint,
    table_cell_parts,
)
from salon_compare.resolver import MapsSearchResolver, RbcBrandLookup
from salon_compare.score import score_place
from salon_compare.store import (
    collect_cache_key,
    list_runs,
    load_run_bundle,
    rows_from_cache,
    save_run,
    save_run_usage,
    save_run_verdict,
    update_run,
)
from salon_compare.yandex_viz import (
    build_yandex_map_html,
    has_map_data,
    markers_from_rows,
    resolve_marker_coords,
    yandex_geocoder_key,
    yandex_maps_js_key,
)

load_project_env()

st.set_page_config(page_title="salon-compare", layout="wide")
st.title("salon-compare")
st.write("Введите три зацепки — по одной на точку.")


def _resolver() -> MapsSearchResolver:
    return MapsSearchResolver(
        map_api_from_env(),
        RbcBrandLookup(HttpxHtmlFetcher()),
    )


_saved = list_runs()
if _saved:
    _ids = [item[0] for item in _saved]
    _labels = {item[0]: item[1] for item in _saved}
    _picked = st.selectbox(
        "Сохранённые разборы",
        _ids,
        format_func=lambda run_id: _labels[int(run_id)],
    )
    if st.button("Открыть сохранённый"):
        bundle = load_run_bundle(int(_picked))
        if bundle:
            loaded = bundle.rows
            st.session_state["saved_rows"] = loaded
            st.session_state["working_rows"] = list(loaded)
            st.session_state["working_key"] = (
                "saved",
                tuple(row.venue_id for row in loaded),
            )
            st.session_state["llm_usage"] = bundle.usage
            st.session_state["llm_verdict"] = bundle.verdict
            st.session_state["llm_kind"] = "SavedRun"
            st.session_state["llm_fp"] = rows_fingerprint(loaded)
            st.session_state["run_id"] = int(_picked)
            st.session_state.pop("outcome", None)
            st.session_state.pop("llm_error", None)

hook_one = st.text_input("Зацепка 1", key="hook-1")
hook_two = st.text_input("Зацепка 2", key="hook-2")
hook_three = st.text_input("Зацепка 3", key="hook-3")


def _card_label(slot: list[VenueCandidate], venue_id: str) -> str:
    for item in slot:
        if item.venue_id == venue_id:
            return candidate_label(item)
    return venue_id


def _pick_format(slot: list[VenueCandidate]) -> Callable[[str], str]:
    def _fmt(venue_id: str) -> str:
        if venue_id == MISSING_VENUE_ID:
            return MISSING_VENUE_LABEL
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


_CELL_EDIT_CSS = """
<style>
.block-container {
  max-width: 1100px;
  margin-left: auto;
  margin-right: auto;
}
div[class*="st-key-cell-"] button [data-testid="stIconMaterial"] {
  opacity: 0;
  transition: opacity 0.12s ease;
}
div[class*="st-key-cell-"] button:hover [data-testid="stIconMaterial"],
div[class*="st-key-cell-"] button:focus-visible [data-testid="stIconMaterial"] {
  opacity: 1;
}
.sc-cell-value {
  font-size: 1.12em;
  font-variant-numeric: tabular-nums;
}
.sc-cell-ref {
  font-weight: 400;
  font-size: 1em;
}
.sc-row-even {
  background: #f6f7f9;
  padding: 0.28rem 0.4rem;
  margin: -0.28rem -0.4rem;
}
</style>
"""

_TABLE_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Репутация",
        (
            "twogis_rating",
            "twogis_last_review",
            "twogis_reviews_90d",
            "twogis_plus_minus",
            "hours",
            "neighbor_count",
            "neighbor_vs",
        ),
    ),
    (
        "Локация",
        (
            "place_type",
            "twogis_rubrics",
            "twogis_price_level",
            "district",
            "metro",
            "address",
        ),
    ),
    ("", ("site_about",)),
    (
        "Юрлицо",
        (
            "egrul_registered_at",
            "egrul_status",
            "egrul_activity",
            "fedresurs",
            "kad",
            "efrsb",
        ),
    ),
)

_BLOCK_SHORT = {
    "reputation": "репутация",
    "stability": "устойчивость",
    "location": "локация",
}


def _field_cell_html(body: str, marks: str, *, even: bool = False) -> str:
    stripe = " sc-row-even" if even else ""
    value = f'<span class="sc-cell-value">{escape(body)}</span>'
    if not marks:
        return f'<div class="sc-cell{stripe}">{value}</div>'
    ref = f'<span class="sc-cell-ref">{escape(marks)}</span>'
    return f'<div class="sc-cell{stripe}">{value} {ref}</div>'


def _leader_bits(rows: list[PlaceRecord]) -> list[str]:
    scores = [score_place(row) for row in rows]
    best: dict[str, int] = {}
    for scored in scores:
        for block in scored.blocks:
            if block.points is None:
                continue
            prev = best.get(block.name)
            if prev is None or block.points > prev:
                best[block.name] = block.points
    marks: list[str] = []
    for scored in scores:
        bits: list[str] = []
        for block in scored.blocks:
            if block.points is None:
                continue
            if best.get(block.name) == block.points:
                bits.append(f"▲ {_BLOCK_SHORT[block.name]}")
        marks.append(" ".join(bits))
    return marks


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
    st.caption(
        "Если ссылка не открывается, попробуйте открыть её без использования proxy/vpn."
    )


@st.dialog("Править поле")
def _edit_dialog(venue_index: int, field_name: str) -> None:
    current = st.session_state.get("working_rows")
    if not isinstance(current, list) or venue_index >= len(current):
        st.write("строка не найдена")
        return
    row = coerce_place_record(current[venue_index])
    if row is None or field_name not in EDITABLE_FIELDS:
        st.write("поле не найдено")
        return
    labels = dict(FIELD_LABELS)
    field = as_sourced_field(getattr(row, field_name, None))
    if field is None or field.value is None:
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
    labels = dict(FIELD_LABELS)
    leaders = _leader_bits(rows)
    widths = [2.2] + [1] * len(rows)
    header = st.columns(widths)
    header[0].markdown("**Поле**")
    for index, row in enumerate(rows):
        heading = f"{row.title} · недостоверный" if row.unreliable else row.title
        header[index + 1].markdown(f"**{heading}**")
    stripe = 0
    for caption, names in _TABLE_SECTIONS:
        if caption:
            st.caption(caption)
        for name in names:
            even = stripe % 2 == 1
            stripe += 1
            cols = st.columns(widths)
            label_html = (
                f'<div class="sc-cell{" sc-row-even" if even else ""}">'
                f"{escape(labels[name])}</div>"
            )
            cols[0].markdown(label_html, unsafe_allow_html=True)
            for index, row in enumerate(rows):
                body, marks = table_cell_parts(row, name, notes)
                value_col, edit_col = cols[index + 1].columns([8, 1], gap="small")
                value_col.markdown(
                    _field_cell_html(body, marks, even=even),
                    unsafe_allow_html=True,
                )
                if edit_col.button(
                    "\u200b",
                    key=f"cell-{index}-{name}",
                    icon=":material/edit:",
                    help=cell_help(row, name),
                ):
                    _edit_dialog(index, name)
    scored_cols = st.columns(widths)
    even = stripe % 2 == 1
    scored_cols[0].markdown(
        f'<div class="sc-cell{" sc-row-even" if even else ""}">'
        f"{escape('Индекс 50/25/25')}</div>",
        unsafe_allow_html=True,
    )
    for index, row in enumerate(rows):
        scored = score_place(row)
        index_text = "не найдено" if scored.index is None else str(scored.index)
        if leaders[index]:
            index_text = f"{index_text} {leaders[index]}"
        scored_cols[index + 1].markdown(
            _field_cell_html(index_text, "", even=even),
            unsafe_allow_html=True,
        )
    _show_footnotes(notes)
    st.caption("Ориентир по формуле, не инвестиционный совет.")


def _show_cards(rows: list[PlaceRecord]) -> None:
    for row in rows:
        card = card_payload(row, score_place(row))
        with st.expander(f"Карточка: {card['title']}"):
            if card["unreliable"]:
                st.write("недостоверный")
            index_value = card["index"]
            if index_value is None:
                st.write("Индекс: не найдено")
            else:
                st.write(f"Индекс: {index_value}")
            if card["note"]:
                st.caption(card["note"])
            for item in card["fields"]:
                st.write(f"{item['label']}: {item['text']}")
            if card["missing"]:
                st.write("Не найдено: " + ", ".join(card["missing"]))


def _working_rows(rows: list[PlaceRecord], key: object) -> list[PlaceRecord]:
    if st.session_state.get("working_key") != key:
        st.session_state["working_rows"] = list(rows)
        st.session_state["working_key"] = key
        st.session_state.pop("llm_fp", None)
    current = st.session_state.get("working_rows")
    if not isinstance(current, list) or not current:
        st.session_state["working_rows"] = list(rows)
        return list(rows)
    typed = [
        coerced
        for item in current
        if (coerced := coerce_place_record(item)) is not None
    ]
    if not typed:
        st.session_state["working_rows"] = list(rows)
        return list(rows)
    st.session_state["working_rows"] = typed
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
        with st.spinner("Ждём ответ модели…"):
            llm = make_llm()
            st.session_state["llm_kind"] = type(llm).__name__
            st.session_state["llm_verdict"] = complete_verdict(rows, llm)
            st.session_state["llm_error"] = llm.last_error()
            usage = llm.last_usage()
            run_id = st.session_state.get("run_id")
            has_new = (
                usage.prompt_tokens is not None
                or usage.completion_tokens is not None
                or usage.total_tokens is not None
                or usage.cost is not None
            )
            if has_new:
                previous = st.session_state.get("llm_usage")
                prev_usage = previous if isinstance(previous, LlmUsage) else None
                st.session_state["llm_usage"] = merge_usage(prev_usage, usage)
                if isinstance(run_id, int):
                    save_run_usage(run_id, usage)
            elif st.session_state.get("llm_usage") is None:
                st.session_state["llm_usage"] = usage
            stored = st.session_state.get("llm_verdict")
            if isinstance(stored, ModelVerdict) and isinstance(run_id, int):
                save_run_verdict(run_id, stored)
            st.session_state["llm_fp"] = fingerprint
    verdict = st.session_state.get("llm_verdict")
    kind = st.session_state.get("llm_kind")
    if not isinstance(verdict, ModelVerdict) and kind == "SavedRun":
        st.write("вывод модели не найден (в разборе не сохранялся)")
        return
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
        st.write(f"{str(usage.cost).replace('.', ',')}$")
        return
    parts = estimated_usd_parts(usage)
    if parts is None:
        st.write("стоимость не найдена")
        return
    st.write(format_usd_sum_line(*parts))


def _show_map(rows: list[PlaceRecord]) -> None:
    points = markers_from_rows(rows)
    with st.expander("Карта (справочно)", expanded=False):
        st.caption(
            "Не влияет на сбор полей и индекс. "
            "Координаты из 2ГИС; иначе геокод адреса на сервере (отдельный ключ)."
        )
        js_key = yandex_maps_js_key()
        if not js_key:
            st.info("Добавьте YANDEX_MAPS_JS_API_KEY в .env, чтобы показать карту.")
            return
        if not has_map_data(points):
            st.write("Нет адресов или координат для карты.")
            return
        needs_geocode = any(point.lat is None or point.lon is None for point in points)
        geocoder_key = yandex_geocoder_key()
        if needs_geocode and not geocoder_key:
            st.warning(
                "Для меток без координат 2ГИС добавьте YANDEX_GEOCODER_API_KEY в .env "
                "(отдельный ключ API Геокодера в кабинете Яндекса)."
            )
        resolved, stats = resolve_marker_coords(
            points,
            geocoder_key if needs_geocode else "",
        )
        if stats.placed == 0:
            st.warning(
                "Метки не найдены: нет координат 2ГИС и геокодер не разобрал адрес. "
                "Проверьте YANDEX_GEOCODER_API_KEY и пересоберите разбор."
            )
            if stats.missing_titles:
                st.write("Без координат: " + ", ".join(stats.missing_titles))
            return
        st.caption(f"Меток на карте: {stats.placed} из {stats.total}")
        if stats.missing_titles:
            st.write("Без координат: " + ", ".join(stats.missing_titles))
        st.components.v1.html(build_yandex_map_html(resolved, js_key), height=450)


def _show_report(rows: list[PlaceRecord]) -> None:
    _show_map(rows)
    for row in rows:
        if not row.collect_ok:
            st.error(f"Сбор «{row.title}» упал: {row.collect_error or 'ошибка'}")
    st.divider()
    st.subheader("Сравнение")
    _show_table(rows)
    _show_cards(rows)
    _show_verdict(rows)
    _show_usage()


if st.button("Разобрать зацепки", key="parse-hooks"):
    st.session_state.pop("saved_rows", None)
    st.session_state.pop("working_rows", None)
    st.session_state.pop("working_key", None)
    st.session_state.pop("row_cache", None)
    st.session_state.pop("llm_fp", None)
    st.session_state.pop("llm_usage", None)
    st.session_state.pop("llm_verdict", None)
    st.session_state.pop("llm_kind", None)
    st.session_state.pop("llm_error", None)
    st.session_state.pop("run_id", None)
    with st.spinner("Уточняем данные ..."):
        st.session_state["outcome"] = resolve_intake(
            [hook_one, hook_two, hook_three],
            _resolver(),
        )
    st.session_state["legal_choices"] = {}

outcome = st.session_state.get("outcome")
saved_raw = st.session_state.get("saved_rows")
saved_rows = (
    [
        coerced
        for item in saved_raw
        if (coerced := coerce_place_record(item)) is not None
    ]
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
        st.write(
            f"{index}. {HOOK_KIND_LABELS.get(hook.kind, hook.kind.value)}: "
            f"{hook.raw.strip()}"
        )
    if outcome.status == IntakeStatus.NEED_DISAMBIGUATION:
        choices: dict[int, str] = {}
        for index, slot in enumerate(outcome.candidates_by_slot):
            st.markdown(f"Зацепка {index + 1}")
            if not slot:
                st.write(MISSING_VENUE_LABEL)
                continue
            options = [item.venue_id for item in slot] + [MISSING_VENUE_ID]
            picked = st.radio(
                "Выберите карточку по ссылке",
                options,
                format_func=_pick_format(slot),
                key=f"pick-{index}",
            )
            if picked is not None:
                choices[index] = str(picked)
        if st.button("Подтвердить точки", key="confirm-venues"):
            st.session_state["outcome"] = apply_slot_choices(outcome, choices)
            st.rerun()
    elif outcome.status == IntakeStatus.READY and outcome.chosen_venues:
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
            with st.status("Собираем поля…") as status:

                def _on_progress(msg: str) -> None:
                    status.update(label=msg)

                return collect_three(
                    venues,
                    classified,
                    CollectDeps(
                        twogis=map_api_from_env(),
                        html=HttpxHtmlFetcher(),
                        parser=OpenHtmlParser(),
                        legal=MarkerLegalParser(),
                        pacer=SleepPacer(3.0),
                        on_progress=_on_progress,
                    ),
                    legal_choices=legal_choices,
                )

        rows, wrote = rows_from_cache(cache, key, _collect)
        if wrote:
            llm = make_llm()
            extract_usage = LlmUsage()
            if not isinstance(llm, NullLlm):
                filled: list[PlaceRecord] = []
                for row in rows:
                    updated, usage = extract_missing(row, llm, extract_context(row))
                    filled.append(updated)
                    extract_usage = merge_usage(extract_usage, usage)
                rows = filled
                cache[key] = rows
            st.session_state["run_id"] = save_run(rows)
            has_extract = (
                extract_usage.prompt_tokens is not None
                or extract_usage.completion_tokens is not None
                or extract_usage.total_tokens is not None
                or extract_usage.cost is not None
            )
            if has_extract:
                previous = st.session_state.get("llm_usage")
                prev_usage = previous if isinstance(previous, LlmUsage) else None
                st.session_state["llm_usage"] = merge_usage(prev_usage, extract_usage)
                run_id = st.session_state.get("run_id")
                if isinstance(run_id, int):
                    save_run_usage(run_id, extract_usage)
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
