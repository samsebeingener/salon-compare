"""Каскад открытых полей: API карт, затем один HTML, иначе не найдено."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Protocol
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field

from salon_compare.hooks import ClassifiedHook, HookKind
from salon_compare.intake import VenueCandidate
from salon_compare.legal import (
    EmptyLegalParser,
    LegalOrg,
    LegalParser,
    ddg_rusprofile_url,
    egrul_url,
    fedresurs_url,
    is_ogrn,
    kad_url,
    labeled_inn,
    labeled_ogrn,
    rbc_company_snippet,
    rbc_search_url,
    resolve_legal_orgs,
    rusprofile_card_urls,
)
from salon_compare.site_enrichment import (
    MAX_SITE_PAGES,
    ddg_site_search_url,
    ddg_site_urls,
    internal_legal_links,
    rbc_company_card_url,
    rbc_website,
)


class Trust(StrEnum):
    FOUND = "found"
    WEAK = "weak"
    MISSING = "missing"


_MAX_RUSPROFILE_CARDS = 5


class RequestPacer(Protocol):
    def wait(self) -> None: ...


class NullPacer:
    def wait(self) -> None:
        return


class SleepPacer:
    def __init__(self, seconds: float = 3.0) -> None:
        self.seconds = seconds
        self._started = False

    def wait(self) -> None:
        if self._started:
            time.sleep(self.seconds)
        self._started = True


class SourcedField(BaseModel):
    model_config = ConfigDict(frozen=True)

    value: float | int | str | None = None
    source_url: str | None = None
    trust: Trust = Trust.MISSING


class HtmlExtract(BaseModel):
    rating: float | None = None
    review_count: int | None = None
    address: str | None = None
    neighbor_count: int | None = None
    neighbor_avg_rating: float | None = None
    about: str | None = None
    hours: str | None = None
    last_review: str | None = None
    plus_minus: str | None = None
    website: str | None = None


class PlaceRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    venue_id: str
    title: str
    twogis_rating: SourcedField
    twogis_review_count: SourcedField
    address: SourcedField
    neighbor_count: SourcedField
    neighbor_vs: SourcedField
    site_about: SourcedField
    egrul_registered_at: SourcedField
    egrul_status: SourcedField
    egrul_activity: SourcedField
    fedresurs: SourcedField
    kad: SourcedField
    legal_candidates: tuple[LegalOrg, ...] = ()
    unreliable: bool = False
    hours: SourcedField = Field(default_factory=SourcedField)
    twogis_last_review: SourcedField = Field(default_factory=SourcedField)
    twogis_reviews_90d: SourcedField = Field(default_factory=SourcedField)
    twogis_plus_minus: SourcedField = Field(default_factory=SourcedField)
    district: SourcedField = Field(default_factory=SourcedField)
    metro: SourcedField = Field(default_factory=SourcedField)


@dataclass(frozen=True)
class MapCard:
    rating: float | None
    review_count: int | None
    address: str | None
    source_url: str
    html_url: str
    neighbor_count: int | None
    neighbor_avg_rating: float | None
    ogrn: str | None = None
    inn: str | None = None
    lon: float | None = None
    lat: float | None = None
    hours: str | None = None
    last_review: str | None = None
    plus_minus: str | None = None
    website: str | None = None
    district: str | None = None
    metro: str | None = None


@dataclass(frozen=True)
class HtmlFetchResult:
    status: str
    body: str
    url: str


class MapApi(Protocol):
    def fetch_card(self, venue: VenueCandidate) -> MapCard | None: ...


class HtmlFetcher(Protocol):
    def get(self, url: str) -> HtmlFetchResult: ...


class HtmlParser(Protocol):
    def parse(self, html: str) -> HtmlExtract: ...


@dataclass(frozen=True)
class CollectDeps:
    twogis: MapApi
    html: HtmlFetcher
    parser: HtmlParser
    legal: LegalParser = field(default_factory=EmptyLegalParser)
    pacer: RequestPacer = field(default_factory=NullPacer)


class EmptyMapApi:
    def search(self, query: str) -> list[VenueCandidate]:
        del query
        return []

    def fetch_card(self, venue: VenueCandidate) -> MapCard | None:
        del venue
        return None


class _OnceHtml:
    def __init__(self, inner: HtmlFetcher) -> None:
        self._inner = inner
        self._cache: dict[str, HtmlFetchResult] = {}

    def get(self, url: str) -> HtmlFetchResult:
        if url not in self._cache:
            self._cache[url] = self._inner.get(url)
        return self._cache[url]


def _missing() -> SourcedField:
    return SourcedField(value=None, source_url=None, trust=Trust.MISSING)


def _found(value: float | int | str, source_url: str) -> SourcedField:
    return SourcedField(value=value, source_url=source_url, trust=Trust.FOUND)


def _weak(value: float | int | str, source_url: str) -> SourcedField:
    return SourcedField(value=value, source_url=source_url, trust=Trust.WEAK)


def html_suffix_url(url: str) -> str | None:
    parsed = urlparse(url)
    path = parsed.path
    if not path or path.endswith("/"):
        return None
    last = path.rsplit("/", 1)[-1]
    if not last or "." in last:
        return None
    return f"{parsed.scheme}://{parsed.netloc}{path}.html"


def _site_urls(
    hook: ClassifiedHook,
    twogis: MapCard,
) -> list[str]:
    raw: list[str] = []
    if hook.kind is HookKind.WEBSITE:
        raw.append(hook.normalized)
    if twogis.website:
        raw.append(twogis.website)
    seen: set[str] = set()
    urls: list[str] = []
    for url in raw:
        key = url.rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        urls.append(url)
    return urls


def _website_from_maps_html(
    html_url: str,
    html: HtmlFetcher,
    parser: HtmlParser,
) -> str | None:
    if not html_url:
        return None
    page = html.get(html_url)
    if page.status != "ok":
        return None
    found = parser.parse(page.body).website
    if not found:
        return None
    host = urlparse(found).netloc.lower()
    if "2gis." in host:
        return None
    return found


def _website_from_rbc(
    ogrn: str,
    html: HtmlFetcher,
    pacer: RequestPacer,
) -> str | None:
    search_url = rbc_search_url(ogrn)
    search = _paced_get(html, search_url, pacer)
    if search.status != "ok":
        return None
    card_url = rbc_company_card_url(search.body, ogrn)
    if card_url is None:
        return None
    card = html.get(card_url)
    if card.status != "ok":
        return None
    return rbc_website(card.body)


def _ddg_discover_sites(
    title: str,
    address: str | None,
    html: HtmlFetcher,
    pacer: RequestPacer,
) -> list[str]:
    if not title.strip():
        return []
    search_url = ddg_site_search_url(title, address)
    page = _paced_get(html, search_url, pacer)
    if page.status != "ok":
        return []
    return ddg_site_urls(page.body)


def _collect_site(
    hook: ClassifiedHook,
    twogis: MapCard,
    venue_title: str,
    venue_address: str | None,
    html: HtmlFetcher,
    parser: HtmlParser,
    pacer: RequestPacer,
) -> tuple[SourcedField, str | None, str | None]:
    maps_site = twogis.website or _website_from_maps_html(twogis.html_url, html, parser)
    ogrn: str | None = None
    inn: str | None = None
    seen: set[str] = set()
    queue: list[str] = list(_site_urls(hook, twogis))
    if maps_site:
        key = maps_site.rstrip("/")
        if key not in {item.rstrip("/") for item in queue}:
            queue.append(maps_site)
    if hook.kind is HookKind.OGRN:
        rbc_site = _website_from_rbc(hook.normalized, html, pacer)
        if rbc_site:
            key = rbc_site.rstrip("/")
            known = {item.rstrip("/") for item in queue}
            if key not in known:
                queue.append(rbc_site)
    if not queue and hook.kind in {HookKind.NAME, HookKind.MAPS_LINK}:
        blocked = False
        if twogis.html_url:
            page = html.get(twogis.html_url)
            blocked = page.status == "blocked"
        if blocked or not twogis.html_url:
            addr = venue_address or twogis.address
            queue.extend(_ddg_discover_sites(venue_title, addr, html, pacer))
    about_value: str | None = None
    about_url: str | None = None
    pages_fetched = 0
    index = 0
    while index < len(queue) and pages_fetched < MAX_SITE_PAGES:
        url = queue[index]
        index += 1
        key = url.rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        page = html.get(url)
        pages_fetched += 1
        if page.status == "ok":
            if ogrn is None:
                ogrn = labeled_ogrn(page.body)
            if inn is None:
                inn = labeled_inn(page.body)
            extracted = parser.parse(page.body).about
            if extracted is not None and about_value is None:
                about_value = extracted
                about_url = url
            if ogrn is None or inn is None:
                for link in internal_legal_links(page.body, url):
                    link_key = link.rstrip("/")
                    if link_key not in seen:
                        queue.append(link)
            continue
        if page.status != "empty":
            continue
        extra = html_suffix_url(url)
        if extra is not None and extra.rstrip("/") not in seen:
            queue.append(extra)
    if about_value and about_url:
        about_field = _found(about_value, about_url)
    else:
        about_field = _missing()
    return about_field, ogrn, inn


def _is_paced(url: str) -> bool:
    lowered = url.lower()
    return (
        "duckduckgo.com" in lowered
        or "rusprofile.ru" in lowered
        or "companies.rbc.ru" in lowered
    )


def _paced_get(html: HtmlFetcher, url: str, pacer: RequestPacer) -> HtmlFetchResult:
    if _is_paced(url):
        pacer.wait()
    return html.get(url)


def _field[T: float | int | str](
    api_value: T | None,
    api_url: str,
    html_url: str,
    pick: Callable[[HtmlExtract], T | None],
    html: HtmlFetcher,
    parser: HtmlParser,
) -> SourcedField:
    if api_value is not None:
        return _found(api_value, api_url)
    if not html_url:
        return _missing()
    page = html.get(html_url)
    if page.status != "ok":
        return _missing()
    extracted = pick(parser.parse(page.body))
    if extracted is None:
        return _missing()
    return _found(extracted, html_url)


def _safe_card(api: MapApi, venue: VenueCandidate) -> MapCard:
    try:
        card = api.fetch_card(venue)
    except Exception:
        card = None
    if card is None:
        return MapCard(None, None, None, "", "", None, None)
    return card


def _empty_place(venue: VenueCandidate) -> PlaceRecord:
    gap = _missing()
    return PlaceRecord(
        venue_id=venue.venue_id,
        title=venue.title,
        twogis_rating=gap,
        twogis_review_count=gap,
        address=gap,
        neighbor_count=gap,
        neighbor_vs=gap,
        site_about=gap,
        egrul_registered_at=gap,
        egrul_status=gap,
        egrul_activity=gap,
        fedresurs=gap,
        kad=gap,
    )


def _mark_90d(last: SourcedField, as_of: date) -> SourcedField:
    if last.trust is Trust.MISSING or last.value is None:
        return _missing()
    raw = str(last.value)[:10]
    try:
        parsed = date.fromisoformat(raw)
    except ValueError:
        return _missing()
    flag = "да" if (as_of - parsed).days <= 90 else "нет"
    return SourcedField(value=flag, source_url=last.source_url, trust=last.trust)


def _venue_address(address: SourcedField, fallback: str | None) -> str | None:
    if address.trust is Trust.FOUND and isinstance(address.value, str):
        return address.value
    return fallback


def collect_place(
    venue: VenueCandidate,
    hook: ClassifiedHook,
    deps: CollectDeps,
    legal_choice: str | None = None,
) -> PlaceRecord:
    html = _OnceHtml(deps.html)
    twogis = _safe_card(deps.twogis, venue)

    twogis_rating = _field(
        twogis.rating,
        twogis.source_url,
        twogis.html_url,
        lambda item: item.rating,
        html,
        deps.parser,
    )
    twogis_reviews = _field(
        twogis.review_count,
        twogis.source_url,
        twogis.html_url,
        lambda item: item.review_count,
        html,
        deps.parser,
    )
    address = _field(
        twogis.address,
        twogis.source_url,
        twogis.html_url,
        lambda item: item.address,
        html,
        deps.parser,
    )

    neighbor_count = _field(
        twogis.neighbor_count,
        twogis.source_url,
        twogis.html_url,
        lambda item: item.neighbor_count,
        html,
        deps.parser,
    )
    neighbor_avg = _field(
        twogis.neighbor_avg_rating,
        twogis.source_url,
        twogis.html_url,
        lambda item: item.neighbor_avg_rating,
        html,
        deps.parser,
    )
    our = twogis_rating.value if twogis_rating.trust is Trust.FOUND else None
    if (
        isinstance(our, int | float)
        and isinstance(neighbor_avg.value, int | float)
        and neighbor_avg.trust is Trust.FOUND
    ):
        label = "выше" if float(neighbor_avg.value) > float(our) else "ниже"
        neighbor_vs = _found(label, neighbor_avg.source_url or twogis.source_url)
    else:
        neighbor_vs = _missing()

    site_about, site_ogrn, site_inn = _collect_site(
        hook,
        twogis,
        venue.title,
        _venue_address(address, twogis.address),
        html,
        deps.parser,
        deps.pacer,
    )
    legal = _collect_legal(
        hook,
        twogis,
        html,
        deps.legal,
        legal_choice,
        deps.pacer,
        extra_ogrn=site_ogrn,
        extra_inn=site_inn,
    )
    as_of = date.today()
    hours = _field(
        twogis.hours,
        twogis.source_url,
        twogis.html_url,
        lambda item: item.hours,
        html,
        deps.parser,
    )
    twogis_last = _field(
        twogis.last_review,
        twogis.source_url,
        twogis.html_url,
        lambda item: item.last_review,
        html,
        deps.parser,
    )
    twogis_pm = _field(
        twogis.plus_minus,
        twogis.source_url,
        twogis.html_url,
        lambda item: item.plus_minus,
        html,
        deps.parser,
    )

    return PlaceRecord(
        venue_id=venue.venue_id,
        title=venue.title,
        twogis_rating=twogis_rating,
        twogis_review_count=twogis_reviews,
        address=address,
        neighbor_count=neighbor_count,
        neighbor_vs=neighbor_vs,
        site_about=site_about,
        egrul_registered_at=legal.registered_at,
        egrul_status=legal.status,
        egrul_activity=legal.activity,
        fedresurs=legal.fedresurs,
        kad=legal.kad,
        legal_candidates=legal.candidates,
        hours=hours,
        twogis_last_review=twogis_last,
        twogis_reviews_90d=_mark_90d(twogis_last, as_of),
        twogis_plus_minus=twogis_pm,
        district=(
            _found(twogis.district, twogis.source_url)
            if twogis.district
            else _missing()
        ),
        metro=(_found(twogis.metro, twogis.source_url) if twogis.metro else _missing()),
    )


@dataclass(frozen=True)
class _LegalBundle:
    candidates: tuple[LegalOrg, ...]
    registered_at: SourcedField
    status: SourcedField
    activity: SourcedField
    fedresurs: SourcedField
    kad: SourcedField


def _inn_hits_from_value(
    inn: str,
    html: HtmlFetcher,
    parser: LegalParser,
) -> list[LegalOrg]:
    page = html.get(egrul_url(inn))
    if page.status != "ok":
        return []
    return list(parser.parse_egrul(page.body).orgs)


def _inn_hits(
    hook: ClassifiedHook,
    html: HtmlFetcher,
    parser: LegalParser,
    legal_choice: str | None,
) -> list[LegalOrg]:
    if hook.kind is not HookKind.INN:
        return []
    if legal_choice:
        return [LegalOrg(legal_choice, legal_choice, egrul_url(legal_choice))]
    return _inn_hits_from_value(hook.normalized, html, parser)


def _registry_text(
    url: str,
    html: HtmlFetcher,
    pick: Callable[[str], str | None],
    needle: str,
) -> SourcedField:
    page = html.get(url)
    if page.status != "ok":
        return _missing()
    if needle not in page.body:
        return _missing()
    value = pick(page.body)
    if value is None:
        return _missing()
    return _found(value, url)


def _official_egrul(
    org: LegalOrg,
    html: HtmlFetcher,
    parser: LegalParser,
    gap: SourcedField,
) -> tuple[SourcedField, SourcedField, SourcedField]:
    egrul = html.get(egrul_url(org.ogrn))
    if egrul.status != "ok" or org.ogrn not in egrul.body:
        return gap, gap, gap
    extract = parser.parse_egrul(egrul.body)
    source = egrul_url(org.ogrn)
    registered = _found(extract.registered_at, source) if extract.registered_at else gap
    status = _found(extract.status, source) if extract.status else gap
    activity = _found(extract.activity, source) if extract.activity else gap
    return registered, status, activity


def _rbc_egrul(
    org: LegalOrg,
    html: HtmlFetcher,
    parser: LegalParser,
    gap: SourcedField,
) -> tuple[SourcedField, SourcedField, SourcedField]:
    url = rbc_search_url(org.ogrn)
    page = html.get(url)
    if page.status != "ok":
        return gap, gap, gap
    snippet = rbc_company_snippet(page.body, org.ogrn)
    if snippet is None:
        return gap, gap, gap
    extract = parser.parse_egrul(snippet)
    registered = _weak(extract.registered_at, url) if extract.registered_at else gap
    status = _weak(extract.status, url) if extract.status else gap
    activity = _weak(extract.activity, url) if extract.activity else gap
    if (
        registered.trust is Trust.MISSING
        and status.trust is Trust.MISSING
        and activity.trust is Trust.MISSING
    ):
        return gap, gap, gap
    return registered, status, activity


def _rusprofile_egrul(
    org: LegalOrg,
    html: HtmlFetcher,
    parser: LegalParser,
    pacer: RequestPacer,
    gap: SourcedField,
) -> tuple[SourcedField, SourcedField, SourcedField]:
    search = _paced_get(html, ddg_rusprofile_url(org.ogrn), pacer)
    if search.status != "ok":
        return gap, gap, gap
    for card_url in rusprofile_card_urls(search.body)[:_MAX_RUSPROFILE_CARDS]:
        card = _paced_get(html, card_url, pacer)
        if card.status == "blocked":
            return gap, gap, gap
        if card.status != "ok" or org.ogrn not in card.body:
            continue
        extract = parser.parse_egrul(card.body)
        registered = (
            _weak(extract.registered_at, card_url) if extract.registered_at else gap
        )
        status = _weak(extract.status, card_url) if extract.status else gap
        activity = _weak(extract.activity, card_url) if extract.activity else gap
        if (
            registered.trust is Trust.MISSING
            and status.trust is Trust.MISSING
            and activity.trust is Trust.MISSING
        ):
            continue
        return registered, status, activity
    return gap, gap, gap


def _collect_legal(
    hook: ClassifiedHook,
    twogis: MapCard,
    html: HtmlFetcher,
    parser: LegalParser,
    legal_choice: str | None,
    pacer: RequestPacer,
    extra_ogrn: str | None = None,
    extra_inn: str | None = None,
) -> _LegalBundle:
    gap = _missing()
    empty = _LegalBundle((), gap, gap, gap, gap, gap)
    inn_hits = _inn_hits(hook, html, parser, legal_choice)
    if not inn_hits and extra_inn:
        inn_hits = _inn_hits_from_value(extra_inn, html, parser)
    orgs = resolve_legal_orgs(
        hook,
        twogis,
        inn_hits,
        extra_ogrn=extra_ogrn,
    )
    if legal_choice:
        picked = [item for item in orgs if item.ogrn == legal_choice]
        if len(picked) == 1:
            orgs = picked
    if len(orgs) > 1:
        return _LegalBundle(tuple(orgs), gap, gap, gap, gap, gap)
    if len(orgs) != 1:
        return empty
    org = orgs[0]
    if not is_ogrn(org.ogrn):
        return empty
    registered, status, activity = _official_egrul(org, html, parser, gap)
    if (
        registered.trust is Trust.MISSING
        and status.trust is Trust.MISSING
        and activity.trust is Trust.MISSING
    ):
        registered, status, activity = _rbc_egrul(org, html, parser, gap)
    if (
        registered.trust is Trust.MISSING
        and status.trust is Trust.MISSING
        and activity.trust is Trust.MISSING
    ):
        registered, status, activity = _rusprofile_egrul(org, html, parser, pacer, gap)
    fedresurs = _registry_text(
        fedresurs_url(org.ogrn),
        html,
        parser.parse_fedresurs,
        org.ogrn,
    )
    kad = _registry_text(kad_url(org.ogrn), html, parser.parse_kad, org.ogrn)
    return _LegalBundle((), registered, status, activity, fedresurs, kad)


def collect_three(
    venues: Sequence[VenueCandidate],
    hooks: Sequence[ClassifiedHook],
    deps: CollectDeps,
    legal_choices: Mapping[str, str] | None = None,
) -> list[PlaceRecord]:
    choices = legal_choices or {}
    rows: list[PlaceRecord] = []
    for venue, hook in zip(venues, hooks, strict=True):
        try:
            rows.append(
                collect_place(
                    venue,
                    hook,
                    deps,
                    legal_choice=choices.get(venue.venue_id),
                )
            )
        except Exception:
            rows.append(_empty_place(venue))
    return rows
