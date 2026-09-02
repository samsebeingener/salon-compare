"""Каскад открытых полей: API карт, затем один HTML, иначе не найдено."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from salon_compare.hooks import ClassifiedHook, HookKind
from salon_compare.intake import VenueCandidate


class Trust(StrEnum):
    FOUND = "found"
    MISSING = "missing"


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


@dataclass(frozen=True)
class MapCard:
    rating: float | None
    review_count: int | None
    address: str | None
    source_url: str
    html_url: str
    neighbor_count: int | None
    neighbor_avg_rating: float | None


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


class EmptyMapApi:
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
    )


def collect_place(
    venue: VenueCandidate,
    hook: ClassifiedHook,
    deps: CollectDeps,
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
    )


def collect_three(
    venues: Sequence[VenueCandidate],
    hooks: Sequence[ClassifiedHook],
    deps: CollectDeps,
) -> list[PlaceRecord]:
    rows: list[PlaceRecord] = []
    for venue, hook in zip(venues, hooks, strict=True):
        try:
            rows.append(collect_place(venue, hook, deps))
        except Exception:
            rows.append(_empty_place(venue))
    return rows
