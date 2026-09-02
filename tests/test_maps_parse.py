from salon_compare.maps_parse import card_from_twogis, card_from_yandex


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
