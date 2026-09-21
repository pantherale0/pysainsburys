"""Tests for product-text sections parsed from details_html."""

from __future__ import annotations

import base64

from pysainsburys.models import Product, ProductDetails
from pysainsburys.models.product import parse_product_details

MILK_DETAILS_HTML = """
<div class="itemTypeGroupContainer productText">
<h3 class="printOnlyBlock partHead">Description</h3>
<div class="itemTypeGroup">
<div class="memo">
<p>Pasteurised homogenised filtered semi-skimmed milk</p>
</div>
</div>
</div>
<div class="itemTypeGroupContainer productText">
<h3 class="printOnlyBlock partHead">Nutrition</h3>
<div class="itemTypeGroup">
<table class="nutritionTable"><tr><td>Energy</td></tr></table>
</div>
</div>
<div class="itemTypeGroupContainer productText">
<h3 class="printOnlyBlock partHead">Packaging</h3>
<div class="itemTypeGroup">
<div class="nameLookups">
<p>Jug</p>
</div>
</div>
</div>
<div class="itemTypeGroupContainer productText">
<h3 class="printOnlyBlock partHead">Storage</h3>
<div class="itemTypeGroup">
<div class="memo">
<p>For best before date: see front of bottle. Keep refrigerated below 5°C.<br>
Once opened, consume within 7 days. Keep upright.</p>
</div>
<p class="statements">
<p>Keep Refrigerated</p>
</p>
</div>
</div>
"""

CONDITIONER_DETAILS_HTML = """
<div class="itemTypeGroupContainer productText">
<h3 class="printOnlyBlock partHead">Description</h3>
<div class="memo"><p>Fabric conditioner</p></div>
</div>
<div class="itemTypeGroupContainer productText">
<h3 class="printOnlyBlock partHead">Ingredients</h3>
<div class="longTextItems"><p>Aqua, fragrance</p></div>
</div>
"""


def test_parse_storage_and_packaging() -> None:
    """Storage keeps memo paragraphs and the statements line."""
    details = parse_product_details(MILK_DETAILS_HTML)
    assert isinstance(details, ProductDetails)
    assert details.storage == [
        "For best before date: see front of bottle. Keep refrigerated below 5°C.",
        "Once opened, consume within 7 days. Keep upright.",
        "Keep Refrigerated",
    ]
    assert details.packaging == ["Jug"]
    assert details.description == ["Pasteurised homogenised filtered semi-skimmed milk"]
    assert details.ingredients is None
    assert details.preparation is None


def test_missing_storage_heading_stays_unset() -> None:
    """Products without a Storage block leave that field empty."""
    details = parse_product_details(CONDITIONER_DETAILS_HTML)
    assert details is not None
    assert details.storage is None
    assert details.ingredients == ["Aqua, fragrance"]
    assert details.description == ["Fabric conditioner"]


def test_product_from_dict_round_trips_details_and_nutrition() -> None:
    """Product detail HTML fills details and still parses nutrition."""
    encoded = base64.b64encode(MILK_DETAILS_HTML.encode()).decode()
    product = Product.from_dict(
        {
            "product_uid": "8172497",
            "name": "Filtered Semi Skimmed Milk",
            "details_html": encoded,
        }
    )
    assert product.details is not None
    assert product.details.storage is not None
    assert product.details.storage[-1] == "Keep Refrigerated"
    assert product.nutrition is not None
    payload = product.to_dict()["details"]
    assert payload["packaging"] == ["Jug"]
    restored = ProductDetails.from_dict(payload)
    assert restored is not None
    assert restored.storage == product.details.storage


def test_description_falls_back_to_json_list() -> None:
    """JSON description is used when the HTML has no Description section."""
    html = """
    <h3 class="partHead">Storage</h3>
    <div class="memo"><p>Keep refrigerated.</p></div>
    """
    encoded = base64.b64encode(html.encode()).decode()
    product = Product.from_dict(
        {
            "product_uid": "1",
            "name": "Milk",
            "details_html": encoded,
            "description": ["Pasteurised milk", ""],
        }
    )
    assert product.details is not None
    assert product.details.description == ["Pasteurised milk"]
    assert product.details.storage == ["Keep refrigerated."]


def test_json_description_without_details_html() -> None:
    """A description list still populates details when HTML is absent."""
    product = Product.from_dict(
        {
            "product_uid": "1",
            "name": "Milk",
            "description": ["Pasteurised milk"],
        }
    )
    assert product.details is not None
    assert product.details.description == ["Pasteurised milk"]
    assert product.details.storage is None
