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
    query = f"{ogrn} site:rusprofile.ru"
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
        has_company = f"/id/{ogrn}-" in chunk
        has_person = f"/persons/ogrnip/{ogrn}-" in chunk
        has_label = bool(re.search(r"огрн", chunk, re.IGNORECASE))
        if ogrn in chunk and (has_company or has_person or has_label):
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
    if not text:
        return []
    names = [text]
    stripped = re.sub(r"^ИП\s+", "", text, flags=re.IGNORECASE).strip()
    if stripped and stripped not in names:
        names.append(stripped)
    first = stripped.split()[0] if stripped else ""
    if len(first) >= 5 and first not in names:
        names.append(first)
    return names


_RUSPROFILE_CARD = re.compile(
    r"(?:https?://)?(?:www\.)?rusprofile\.ru/(id|ip)/(\d+)",
    re.IGNORECASE,
)


def rusprofile_card_urls(html: str) -> list[str]:
    decoded = unquote(html)
    seen: set[str] = set()
    urls: list[str] = []
    for match in _RUSPROFILE_CARD.finditer(decoded):
        kind = match.group(1).lower()
        url = f"https://www.rusprofile.ru/{kind}/{match.group(2)}"
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def is_ogrn(value: str) -> bool:
    return value.isdigit() and len(value) in {13, 15}


_LABELED_OGRN = re.compile(
    r"(?:огрн(?:\s*/\s*огрнип)?|огрнип)\s*[:№]?\s*([\d\s]{13,23})",
    re.IGNORECASE,
)


def _normalize_digits(value: str) -> str:
    return re.sub(r"\s+", "", value)


def labeled_ogrn(html: str) -> str | None:
    match = _LABELED_OGRN.search(unescape(html))
    if match is None:
        return None
    value = _normalize_digits(match.group(1))
    return value if is_ogrn(value) else None


_LABELED_INN = re.compile(
    r"инн\s*[:№]?\s*([\d\s]{10,18})",
    re.IGNORECASE,
)


def labeled_inn(html: str) -> str | None:
    body = unescape(html)
    for match in _LABELED_INN.finditer(body):
        value = _normalize_digits(match.group(1))
        if len(value) in {10, 12}:
            return value
    return None


_REQUISITES_NAME = re.compile(
    r"ИП\s+([А-ЯЁA-Z][А-ЯЁA-Zа-яёa-z.\s\-]{2,60}?)(?=\s+ИНН\b)",
    re.IGNORECASE,
)
_REQUISITES_IP_OGRNIP = re.compile(
    r"(?:индивидуальный\s+предприниматель|ИП)\s+"
    r"([А-ЯЁA-Z][А-ЯЁA-Zа-яёa-z.\s\-]{2,80}?)"
    r"(?=\s+ОГРНИП\b)",
    re.IGNORECASE,
)
_REQUISITES_OOO = re.compile(
    r'ООО\s+[«"]([^»"]+)[»"]',
    re.IGNORECASE,
)


def site_requisites_extract(html: str, ogrn: str) -> LegalExtract | None:
    if labeled_ogrn(html) != ogrn:
        return None
    text = unescape(re.sub(r"<[^>]+>", " ", html))
    text = re.sub(r"\s+", " ", text).strip()
    name: str | None = None
    ip_match = _REQUISITES_NAME.search(text)
    if ip_match:
        name = f"ИП {ip_match.group(1).strip()}"
    else:
        ip_ogrnip = _REQUISITES_IP_OGRNIP.search(text)
        if ip_ogrnip:
            name = f"ИП {ip_ogrnip.group(1).strip()}"
        else:
            ooo_match = _REQUISITES_OOO.search(text)
            if ooo_match:
                name = f"ООО «{ooo_match.group(1).strip()}»"
    inn = labeled_inn(html)
    parts: list[str] = []
    if name:
        parts.append(name)
    if inn:
        parts.append(f"ИНН {inn}")
    label = "ОГРНИП" if len(ogrn) == 15 else "ОГРН"
    parts.append(f"{label} {ogrn}")
    activity = ", ".join(parts)
    status: str | None = None
    lowered = text.lower()
    if "ликвидирован" in lowered or "не действует" in lowered:
        status = "не действует"
    elif "действует" in lowered or "действующ" in lowered:
        status = "действует"
    return LegalExtract(activity=activity, status=status, registered_at=None)


def resolve_legal_orgs(
    hook: ClassifiedHook,
    twogis: LegalIdCard,
    inn_hits: Sequence[LegalOrg],
    extra_ogrn: str | None = None,
) -> list[LegalOrg]:
    if hook.kind is HookKind.OGRN:
        return [LegalOrg(hook.normalized, hook.raw.strip(), egrul_url(hook.normalized))]
    if hook.kind is HookKind.INN:
        return list(inn_hits)
    ident = (twogis.ogrn or "").strip()
    if is_ogrn(ident):
        url = twogis.source_url or egrul_url(ident)
        return [LegalOrg(ident, ident, url)]
    extra = (extra_ogrn or "").strip()
    if is_ogrn(extra):
        return [LegalOrg(extra, extra, egrul_url(extra))]
    return []


_DATE = re.compile(r"\b(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})\b")
_OGRN = re.compile(r"\b(\d{15}|\d{13})\b")


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
