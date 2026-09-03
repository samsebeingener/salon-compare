"""Живой прогон LLM: демо-тройка → досье → вывод модели.

Лог: data/llm-interactions.log
"""

from __future__ import annotations

import json
import sys

from salon_compare.collect import CollectDeps, SleepPacer, collect_three
from salon_compare.hooks import classify_hook
from salon_compare.html_fetch import HttpxHtmlFetcher
from salon_compare.html_parse import OpenHtmlParser
from salon_compare.intake import IntakeOutcome, IntakeStatus, resolve_intake
from salon_compare.legal import MarkerLegalParser
from salon_compare.llm import estimate_usd, make_llm
from salon_compare.llm_log import log_path
from salon_compare.load_env import load_project_env
from salon_compare.maps_http import map_api_from_env
from salon_compare.report import build_evidence_dossier, complete_verdict
from salon_compare.resolver import MapsSearchResolver, RbcBrandLookup
from salon_compare.score import score_place


def _chosen_venues(outcome: IntakeOutcome) -> tuple | None:
    if outcome.status is IntakeStatus.READY and outcome.chosen_venues is not None:
        return outcome.chosen_venues
    if outcome.status is not IntakeStatus.NEED_DISAMBIGUATION:
        return None
    venues = []
    for slot_idx, slot in enumerate(outcome.candidates_by_slot, start=1):
        if not slot:
            return None
        picked = slot[0]
        print(
            f"  слот {slot_idx}: авто-выбор первого из {len(slot)} — {picked.title}",
            flush=True,
        )
        venues.append(picked)
    return tuple(venues)


DEMO_HOOKS = (
    "https://pinklemon-nails.ru/baumanskaya",
    "Вишня Таганская",
    "1147746349552",
)


def _resolver() -> MapsSearchResolver:
    return MapsSearchResolver(
        map_api_from_env(),
        RbcBrandLookup(HttpxHtmlFetcher()),
    )


def _deps() -> CollectDeps:
    return CollectDeps(
        twogis=map_api_from_env(),
        html=HttpxHtmlFetcher(),
        parser=OpenHtmlParser(),
        legal=MarkerLegalParser(),
        pacer=SleepPacer(seconds=0.0),
    )


def main() -> int:
    load_project_env()
    log_path().unlink(missing_ok=True)

    print("=== salon-compare LLM probe ===", flush=True)
    print(f"Лог: {log_path()}", flush=True)

    outcome = resolve_intake(list(DEMO_HOOKS), _resolver())
    venues = _chosen_venues(outcome)
    if venues is None:
        print(f"intake не готов: {outcome.status.value}", file=sys.stderr)
        if outcome.message:
            print(outcome.message, file=sys.stderr)
        return 1
    if outcome.status is IntakeStatus.NEED_DISAMBIGUATION:
        print("Авто-выбор при неоднозначности (только для probe):", flush=True)

    print("Сбор трёх точек (сеть, может занять минуту)...", flush=True)
    hooks = [classify_hook(item) for item in DEMO_HOOKS]
    rows = collect_three(venues, hooks, _deps())
    for row in rows:
        scored = score_place(row)
        print(f"- {row.title}: index={scored.index}", flush=True)

    dossier = build_evidence_dossier(rows)
    print("\n--- досье (укорочено) ---", flush=True)
    preview = json.dumps(dossier, ensure_ascii=False, indent=2)
    if len(preview) > 2500:
        preview = preview[:2500] + "\n..."
    print(preview, flush=True)

    llm = make_llm()
    print(f"\nКлиент LLM: {type(llm).__name__}", flush=True)
    if type(llm).__name__ == "NullLlm":
        print("Нет ключей LLM — см. лог", file=sys.stderr)
        return 2

    print("Запрос к модели...", flush=True)
    verdict = complete_verdict(rows, llm)
    raw_error = llm.last_error()
    usage = llm.last_usage()

    print("\n--- usage ---", flush=True)
    print(usage.model_dump_json(indent=2), flush=True)
    usd = estimate_usd(usage)
    if usd is not None:
        print(f"оценка USD: {usd}", flush=True)

    if raw_error:
        print(f"\nОшибка LLM: {raw_error}", file=sys.stderr)

    print("\n--- вывод модели ---", flush=True)
    if verdict is None:
        print("вердикт не разобран или не прошёл валидацию", file=sys.stderr)
        return 3

    print(f"Интереснее: {verdict.interesting}", flush=True)
    print(f"Чем лучше: {verdict.why_better}", flush=True)
    print(f"Сломается, если: {verdict.breaks_if}", flush=True)
    if verdict.compared_index is not None:
        print(f"Индекс в выводе: {verdict.compared_index}", flush=True)

    print(f"\nПолный лог: {log_path().resolve()}", flush=True)
    if log_path().is_file():
        lines = log_path().read_text(encoding="utf-8").strip().splitlines()
        print(f"Событий в логе: {len(lines)}", flush=True)
        for line in lines[-3:]:
            event = json.loads(line)
            print(
                f"  [{event.get('event')}] model={event.get('model', '-')}", flush=True
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
