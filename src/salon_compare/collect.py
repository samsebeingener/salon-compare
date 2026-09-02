"""Каскад открытых полей: API карт, затем один HTML, иначе не найдено."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict

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
    resolve_legal_orgs,
    rusprofile_card_urls,
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


class PlaceRecord(BaseModel):
    venue_id: str
    title: str
    yandex_rating: SourcedField
    yandex_review_count: SourcedField
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
    yandex: MapApi
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


class EmptyParser:
    def parse(self, html: str) -> HtmlExtract:
        del html
        return HtmlExtract()


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


def _is_paced(url: str) -> bool:
    lowered = url.lower()
    return "duckduckgo.com" in lowered or "rusprofile.ru" in lowered


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
        yandex_rating=gap,
        yandex_review_count=gap,
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


def collect_place(
    venue: VenueCandidate,
    hook: ClassifiedHook,
    deps: CollectDeps,
    legal_choice: str | None = None,
) -> PlaceRecord:
    html = _OnceHtml(deps.html)
    yandex = _safe_card(deps.yandex, venue)
    twogis = _safe_card(deps.twogis, venue)

    yandex_rating = _field(
        yandex.rating,
        yandex.source_url,
        yandex.html_url,
        lambda item: item.rating,
        html,
        deps.parser,
    )
    yandex_reviews = _field(
        yandex.review_count,
        yandex.source_url,
        yandex.html_url,
        lambda item: item.review_count,
        html,
        deps.parser,
    )
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
        yandex.address,
        yandex.source_url,
        yandex.html_url,
        lambda item: item.address,
        html,
        deps.parser,
    )
    if address.trust is Trust.MISSING:
        address = _field(
            twogis.address,
            twogis.source_url,
            twogis.html_url,
            lambda item: item.address,
            html,
            deps.parser,
        )

    neighbor_count = _field(
        yandex.neighbor_count,
        yandex.source_url,
        yandex.html_url,
        lambda item: item.neighbor_count,
        html,
        deps.parser,
    )
    if neighbor_count.trust is Trust.MISSING:
        neighbor_count = _field(
            twogis.neighbor_count,
            twogis.source_url,
            twogis.html_url,
            lambda item: item.neighbor_count,
            html,
            deps.parser,
        )
    neighbor_avg = _field(
        yandex.neighbor_avg_rating,
        yandex.source_url,
        yandex.html_url,
        lambda item: item.neighbor_avg_rating,
        html,
        deps.parser,
    )
    our = yandex_rating.value if yandex_rating.trust is Trust.FOUND else None
    if (
        isinstance(our, int | float)
        and isinstance(neighbor_avg.value, int | float)
        and neighbor_avg.trust is Trust.FOUND
    ):
        label = "выше" if float(neighbor_avg.value) > float(our) else "ниже"
        neighbor_vs = _found(label, neighbor_avg.source_url or yandex.source_url)
    else:
        neighbor_vs = _missing()

    site_about = _missing()
    if hook.kind is HookKind.WEBSITE:
        site_about = _field(
            None,
            "",
            hook.normalized,
            lambda item: item.about,
            html,
            deps.parser,
        )

    legal = _collect_legal(
        hook, yandex, twogis, html, deps.legal, legal_choice, deps.pacer
    )

    return PlaceRecord(
        venue_id=venue.venue_id,
        title=venue.title,
        yandex_rating=yandex_rating,
        yandex_review_count=yandex_reviews,
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
    )


@dataclass(frozen=True)
class _LegalBundle:
    candidates: tuple[LegalOrg, ...]
    registered_at: SourcedField
    status: SourcedField
    activity: SourcedField
    fedresurs: SourcedField
    kad: SourcedField


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
    page = html.get(egrul_url(hook.normalized))
    if page.status != "ok":
        return []
    return list(parser.parse_egrul(page.body).orgs)


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
    yandex: MapCard,
    twogis: MapCard,
    html: HtmlFetcher,
    parser: LegalParser,
    legal_choice: str | None,
    pacer: RequestPacer,
) -> _LegalBundle:
    gap = _missing()
    empty = _LegalBundle((), gap, gap, gap, gap, gap)
    orgs = resolve_legal_orgs(
        hook,
        yandex,
        twogis,
        _inn_hits(hook, html, parser, legal_choice),
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
