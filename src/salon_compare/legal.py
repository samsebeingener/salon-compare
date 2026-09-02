"""ОГРН/ИНН и открытые реестры. Несколько записей — наружу, первую не берём."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel

from salon_compare.hooks import ClassifiedHook, HookKind


@dataclass(frozen=True)
class LegalOrg:
    ogrn: str
    title: str
    source_url: str


class LegalExtract(BaseModel):
    registered_at: str | None = None
    status: str | None = None
    activity: str | None = None
    orgs: list[LegalOrg] = []


class LegalIdCard(Protocol):
    @property
    def ogrn(self) -> str | None: ...

    @property
    def inn(self) -> str | None: ...

    @property
    def source_url(self) -> str: ...


class LegalParser(Protocol):
    def parse_egrul(self, html: str) -> LegalExtract: ...

    def parse_fedresurs(self, html: str) -> str | None: ...

    def parse_kad(self, html: str) -> str | None: ...


class EmptyLegalParser:
    def parse_egrul(self, html: str) -> LegalExtract:
        del html
        return LegalExtract()

    def parse_fedresurs(self, html: str) -> str | None:
        del html
        return None

    def parse_kad(self, html: str) -> str | None:
        del html
        return None


def egrul_url(query: str) -> str:
    return f"https://egrul.nalog.ru/index.html?query={query}"


def fedresurs_url(ogrn: str) -> str:
    return f"https://fedresurs.ru/search?searchString={ogrn}"


def kad_url(ogrn: str) -> str:
    return f"https://kad.arbitr.ru/?ogrn={ogrn}"


def resolve_legal_orgs(
    hook: ClassifiedHook,
    yandex: LegalIdCard,
    twogis: LegalIdCard,
    inn_hits: Sequence[LegalOrg],
) -> list[LegalOrg]:
    if hook.kind is HookKind.OGRN:
        return [LegalOrg(hook.normalized, hook.raw.strip(), egrul_url(hook.normalized))]
    if hook.kind is HookKind.INN:
        return list(inn_hits)
    found: dict[str, LegalOrg] = {}
    for card in (yandex, twogis):
        ident = (card.ogrn or card.inn or "").strip()
        if not ident:
            continue
        url = card.source_url or egrul_url(ident)
        found[ident] = LegalOrg(ident, ident, url)
    return list(found.values())


_DATE = re.compile(r"\b(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})\b")
_OGRN = re.compile(r"\b(\d{13}|\d{15})\b")


class MarkerLegalParser:
    """Только явные маркеры HTML. Нет маркера — пусто, не «долгов нет»."""

    def parse_egrul(self, html: str) -> LegalExtract:
        orgs: list[LegalOrg] = []
        seen: set[str] = set()
        for ogrn in _OGRN.findall(html):
            if ogrn in seen:
                continue
            seen.add(ogrn)
            orgs.append(LegalOrg(ogrn, ogrn, egrul_url(ogrn)))
        status: str | None = None
        lowered = html.lower()
        if "действует" in lowered:
            status = "действует"
        elif "ликвидир" in lowered or "исключен" in lowered:
            status = "не действует"
        registered = None
        if "регистрац" in lowered:
            found_date = _DATE.search(html)
            if found_date:
                registered = found_date.group(1)
        activity = None
        for marker in ("оквэд", "вид деятельности"):
            idx = lowered.find(marker)
            if idx >= 0:
                snippet = html[idx : idx + 180]
                activity = re.sub(r"\s+", " ", snippet).strip()[:120]
                break
        return LegalExtract(
            registered_at=registered,
            status=status,
            activity=activity,
            orgs=orgs,
        )

    def parse_fedresurs(self, html: str) -> str | None:
        lowered = html.lower()
        if "банкрот" in lowered:
            return "банкротство"
        if "торги" in lowered or "продаж" in lowered:
            return "продажа имущества"
        if "ничего не найдено" in lowered or "не найден" in lowered:
            return "не обнаружено"
        return None

    def parse_kad(self, html: str) -> str | None:
        lowered = html.lower()
        if "дел не найден" in lowered or "ничего не найдено" in lowered:
            return "не обнаружено"
        if "арбитражн" in lowered and ("дело" in lowered or "дел " in lowered):
            return "есть дела"
        return None
