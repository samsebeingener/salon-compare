from salon_compare.maps_parse import (
    candidates_from_twogis_items,
    candidates_from_yandex_features,
    card_from_twogis,
    card_from_yandex,
)


def test_parse_twogis_reviews_and_address() -> None:
    card = card_from_twogis(
        {
            "id": "firm-1",
            "address_name": "Москва, Бауманская",
            "reviews": {"general_rating": 4.6, "general_review_count": 80},
        }
    )
    assert card.rating == 4.6
    assert card.review_count == 80
    assert card.address == "Москва, Бауманская"
    assert card.html_url.endswith("firm-1")


def test_parse_twogis_keeps_website_from_contacts() -> None:
    card = card_from_twogis(
        {
            "id": "firm-1",
            "contact_groups": [
                {
                    "contacts": [
                        {"type": "phone", "value": "+79990000000"},
                        {
                            "type": "website",
                            "url": "https://studio.example/",
                            "value": "studio.example",
                        },
                    ]
                }
            ],
        }
    )
    assert card.website == "https://studio.example"
    assert "2gis.ru/firm/firm-1" in card.html_url


def test_parse_yandex_website_is_not_maps_source() -> None:
    card = card_from_yandex(
        {
            "properties": {
                "CompanyMetaData": {
                    "id": "org-1",
                    "url": "https://studio.example",
                    "address": "Москва",
                }
            }
        }
    )
    assert card.website == "https://studio.example"
    assert "yandex.ru/maps" in card.html_url
    assert card.source_url == card.html_url


def test_parse_yandex_optional_rating() -> None:
    card = card_from_yandex(
        {
            "properties": {
                "CompanyMetaData": {
                    "id": "org-1",
                    "address": "Москва",
                    "Ratings": {"value": 4.2},
                    "Reviews": {"Count": 15},
                }
            }
        }
    )
    assert card.rating == 4.2
    assert card.review_count == 15
    assert card.address == "Москва"


def test_twogis_search_hits_keep_distinct_addresses() -> None:
    found = candidates_from_twogis_items(
        [
            {
                "id": "70000001020631928",
                "name": "I like nails, студия маникюра",
                "address_name": "Москва, Бауманская",
            },
            {
                "id": "70000001035144425",
                "name": "I like nails, студия маникюра",
                "full_address_name": "Москва, Таганская",
                "address_name": "Таганская",
            },
        ]
    )
    assert found[0].address == "Москва, Бауманская"
    assert found[1].address == "Москва, Таганская"


def test_yandex_search_hit_keeps_address() -> None:
    found = candidates_from_yandex_features(
        [
            {
                "properties": {
                    "CompanyMetaData": {
                        "id": "org-1",
                        "name": "I like nails",
                        "address": "Москва, Бауманская",
                    }
                }
            }
        ]
    )
    assert found[0].title == "I like nails"
    assert found[0].address == "Москва, Бауманская"


def test_twogis_search_address_appends_mall_and_floor() -> None:
    found = candidates_from_twogis_items(
        [
            {
                "id": "1",
                "name": "I like nails, студия маникюра",
                "full_address_name": "Москва, Бауманская, 7",
                "address_comment": "1 этаж",
                "address": {"building_name": "ТЦ Атриум"},
            }
        ]
    )
    assert found[0].address == "Москва, Бауманская, 7, ТЦ Атриум, 1 этаж"


def test_twogis_search_skips_missing_floor_and_mall() -> None:
    found = candidates_from_twogis_items(
        [
            {
                "id": "2",
                "name": "I like nails, студия маникюра",
                "address_name": "Москва, Таганская",
            }
        ]
    )
    assert found[0].address == "Москва, Таганская"


def test_twogis_search_does_not_repeat_mall_already_in_street() -> None:
    found = candidates_from_twogis_items(
        [
            {
                "id": "3",
                "name": "Студия",
                "full_address_name": "Москва, ТЦ Атриум",
                "address_comment": "1 этаж",
                "address": {"building_name": "ТЦ Атриум"},
            }
        ]
    )
    assert found[0].address == "Москва, ТЦ Атриум, 1 этаж"


def _week_hours(start: str = "10:00", end: str = "22:00") -> dict[str, object]:
    slot = {"working_hours": [{"from": start, "to": end}]}
    return {day: slot for day in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")}


def test_twogis_card_reads_hours_district_metro() -> None:
    card = card_from_twogis(
        {
            "id": "firm-1",
            "schedule": _week_hours(),
            "adm_div": [
                {"type": "city", "name": "Москва"},
                {"type": "district", "name": "Замоскворечье"},
            ],
            "links": {
                "nearest_stations": [
                    {
                        "name": "Павелецкая",
                        "distance": 140,
                        "route_types": ["metro"],
                    },
                    {
                        "name": "Новокузнецкая",
                        "distance": 800,
                        "route_types": ["metro"],
                    },
                ]
            },
        }
    )
    assert card.hours == "пн-вс 10:00-22:00"
    assert card.district == "Замоскворечье"
    assert card.metro == "Павелецкая, 140 м"


def test_twogis_card_missing_hours_district_metro() -> None:
    card = card_from_twogis({"id": "firm-1"})
    assert card.hours is None
    assert card.district is None
    assert card.metro is None
