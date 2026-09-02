"""ОГРН/ИНН и открытые реестры. Несколько записей — наружу, первую не берём."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from html import unescape
from typing import Protocol
from urllib.parse import quote_plus, unquote

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


def ddg_rusprofile_url(ogrn: str) -> str:
    query = f"{ogrn} site:rusprofile.ru/id"
    return f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"


def rbc_search_url(ogrn: str) -> str:
    return f"https://companies.rbc.ru/search/?query={ogrn}"


def rbc_company_snippet(html: str, ogrn: str) -> str | None:
    needle = "company-card info-card"
    start = 0
    while True:
        idx = html.find(needle, start)
        if idx < 0:
            return None
        chunk = html[idx : idx + 5000]
        has_id = f"/id/{ogrn}-" in chunk
        has_label = "ОГРН" in chunk or "огрн" in chunk.lower()
        if ogrn in chunk and (has_id or has_label):
            return chunk
        start = idx + len(needle)


def rbc_brand_names(html: str, ogrn: str) -> list[str]:
    snippet = rbc_company_snippet(html, ogrn)
    if snippet is None:
        return []
    match = re.search(
        r"company-name-highlight[^>]*>(.*?)</a>",
        snippet,
        re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        return []
    text = unescape(re.sub(r"<[^>]+>", " ", match.group(1)))
    text = re.sub(r"\s+", " ", text).strip()
    return [text] if text else []


_RUSPROFILE_ID = re.compile(
    r"(?:https?://)?(?:www\.)?rusprofile\.ru/id/(\d+)",
    re.IGNORECASE,
)


def rusprofile_card_urls(html: str) -> list[str]:
    decoded = unquote(html)
    seen: set[str] = set()
    urls: list[str] = []
    for match in _RUSPROFILE_ID.finditer(decoded):
        url = f"https://www.rusprofile.ru/id/{match.group(1)}"
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def is_ogrn(value: str) -> bool:
    return value.isdigit() and len(value) in {13, 15}


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
        ident = (card.ogrn or "").strip()
        if not is_ogrn(ident):
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
        if "ликвидированная организация" in lowered or "не действует" in lowered:
            status = "не действует"
        elif "действующая организация" in lowered or "действует" in lowered:
            status = "действует"
        elif "действующ" in lowered:
            status = "действует"
        registered = None
        reg = re.search(
            r"дата регистрации.{0,80}?(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})",
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if reg:
            registered = reg.group(1)
        elif "регистрац" in lowered:
            found_date = _DATE.search(html)
            if found_date:
                registered = found_date.group(1)
        activity = None
        for marker in ("основной вид деятельности", "вид деятельности", "оквэд"):
            idx = lowered.find(marker)
            if idx >= 0:
                snippet = html[idx : idx + 180]
                cleaned = re.sub(r"<[^>]+>", " ", snippet)
                activity = re.sub(r"\s+", " ", cleaned).strip()[:120]
                break
        if activity is None:
            crumbs = re.findall(
                r'category-breadcrumb__item"[^>]*>([^<]+)',
                html,
                re.IGNORECASE,
            )
            if crumbs:
                activity = unescape(crumbs[-1]).strip()[:120]
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
