"""Tests for the remaining catalogue fields on a product."""

from __future__ import annotations

from pysainsburys.models import Product


def test_product_from_dict_keeps_catalogue_fields() -> None:
    """Brand, labels, images, and loose weight survive dict conversion."""
    product = Product.from_dict(
        {
            "product_uid": "1196757",
            "name": "Sainsbury's Bananas Loose",
            "full_url": "://www.sainsburys.co.uk/gol-ui/product/sainsburys-bananas-loose",
            "short_description": "Fairtrade Bananas",
            "zone": "Fruit & vegetables",
            "attributes": {"brand": ["Sainsbury's"]},
            "labels": [
                {
                    "label_uid": "British",
                    "text": "BRITISH",
                    "alt_text": "BRITISH",
                    "color": "#4c4c4c",
                    "link": "https://www.sainsburys.co.uk/gol-ui/features/best-of-british",
                    "link_opens_in_new_window": False,
                }
            ],
            "categories": [{"id": "310865", "name": "Bananas"}],
            "breadcrumbs": [
                {"label": "Fruit & vegetables", "url": "gb/groceries/fruit-veg"}
            ],
            "average_weight": {"amount": 0.17, "measure": "kg"},
            "original_unit_price": {"price": 0.9, "measure": "kg", "measure_amount": 1},
            "image": "https://example.test/large.jpg",
            "assets": {
                "plp_image": "https://example.test/plp.jpg",
                "images": [
                    {
                        "id": "1",
                        "sizes": [
                            {
                                "url": "https://example.test/100.jpg",
                                "width": 100,
                                "height": 100,
                            }
                        ],
                    }
                ],
            },
            "header": {"text": "Nectar price", "type": "NECTAR"},
            "is_spotlight": True,
            "spotlight_label": "Featured",
            "display_icons": ["FULL ON FIBRE"],
            "health_classification": {"health_rating_score_value": "5"},
            "hfss_restriction": [
                {
                    "country": "ENG",
                    "restricted": False,
                    "hfss_category": "Out of scope",
                    "hfss_score": 0,
                    "last_change_date": "2025-09-24T12:47:16Z",
                }
            ],
            "not_for_eu": True,
            "promise": {
                "type": "",
                "earliest_promise_date": None,
                "last_amendment_date": None,
                "status": {"label": "", "type": "NONE"},
            },
            "pdp_deep_link": "/shop/ProductDisplay?productId=1",
        }
    )
    assert product.brand == ["Sainsbury's"]
    assert product.full_url == (
        "https://www.sainsburys.co.uk/gol-ui/product/sainsburys-bananas-loose"
    )
    assert product.labels[0].text == "BRITISH"
    assert product.categories[0].category_id == "310865"
    assert product.breadcrumbs[0].url == "gb/groceries/fruit-veg"
    assert product.average_weight is not None
    assert product.average_weight.amount == 0.17
    assert product.original_unit_price is not None
    assert product.original_unit_price.price == 0.9
    assert product.image_url == "https://example.test/plp.jpg"
    assert product.images[0].sizes[0].width == 100
    assert product.header is not None
    assert product.header.type == "NECTAR"
    assert product.health_rating == "5"
    assert product.hfss_restrictions[0].country == "ENG"
    assert product.not_for_eu is True
    assert product.promise is None
    payload = product.to_dict()
    assert payload["brand"] == ["Sainsbury's"]
    assert payload["display_icons"] == ["FULL ON FIBRE"]
    assert payload["short_description"] == "Fairtrade Bananas"
