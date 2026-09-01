"""Tests for nutrition parsing."""

from __future__ import annotations

import base64

from pysainsburys.models import NutritionInfo, Product
from pysainsburys.models.product import (
    parse_nutrition,
    parse_nutrition_from_details_html,
)

BREAD_NUTRITION_HTML = """
<div class="textualNutrition">
<h3>Nutrition</h3>
<div class="nutritionalContentSummary">
<ul class="lozengeBlock">
<li class="lozenge energy energy">
<div class="lozengeHeaderSection">
<h3 class="lozengeTitle">ENERGY</h3>
<p>436kJ</p>
<p>104kcal</p>
</div>
<div class="percentage"><p>5%</p></div>
<p class="access">energy</p>
</li>
<li class="lozenge low fat">
<div class="lozengeHeaderSection">
<h3 class="lozengeTitle">FAT</h3>
<p>1.1g</p>
</div>
<div class="percentage"><p>2%</p></div>
<p class="access">Low</p>
</li>
</ul>
<div class="lozengeFooter">
<p>of your reference intake</p>
<p>Typical values per 100g: Energy 1021kJ/243kcal</p>
</div>
</div>
<p><strong>Table of Nutritional Information</strong></p>
<table class="nutritionTable">
<thead>
<tr>
<th scope="col"></th><th scope="col">Per 100g</th><th scope="col">Per slice</th>
</tr>
</thead>
<tbody>
<tr>
<th scope="row" class="rowHeader" rowspan="2">Energy</th><td>1021kJ</td><td>436kcal</td>
</tr>
<tr>
<td>243kcal</td><td>104kcal</td>
</tr>
<tr>
<th scope="row" class="rowHeader">Fat</th><td>2.5g</td><td>1.1g</td>
</tr>
</tbody>
</table>
</div>
"""

WATER_NUTRITION_HTML = """
<div class="textualNutrition">
<h3>Nutrition</h3>
<p><strong>Table of Nutritional Information</strong></p>
<table class="nutritionTable">
<thead>
<tr>
<th scope="col"></th>
<th scope="col">Typical Analysis (mg/L)</th>
</tr>
</thead>
<tbody>
<tr><th scope="row" class="rowHeader">Sodium Na+</th><td>31.2</td></tr>
</tbody>
</table>
</div>
"""


def test_parse_nutrition_summary_and_table() -> None:
    """Bread-style products expose lozenge summaries and tables."""
    nutrition = parse_nutrition(BREAD_NUTRITION_HTML)
    assert nutrition is not None
    assert len(nutrition.summary) == 2
    assert nutrition.summary[0].name == "ENERGY"
    assert nutrition.summary[0].values == ["436kJ", "104kcal"]
    assert nutrition.summary[1].level == "Low"
    assert nutrition.notes == [
        "of your reference intake",
        "Typical values per 100g: Energy 1021kJ/243kcal",
    ]
    assert nutrition.tables[0].title == "Table of Nutritional Information"
    assert nutrition.tables[0].columns == ["Per 100g", "Per slice"]
    assert nutrition.tables[0].rows[0].name == "Energy"
    assert nutrition.tables[0].rows[1].name == "Energy"
    assert nutrition.tables[0].rows[2].name == "Fat"


def test_parse_nutrition_table_only_product() -> None:
    """Some products only expose a nutrition table."""
    nutrition = parse_nutrition(WATER_NUTRITION_HTML)
    assert nutrition is not None
    assert nutrition.summary == []
    assert nutrition.tables[0].rows[0].name == "Sodium Na+"
    assert nutrition.tables[0].rows[0].values == ["31.2"]


def test_parse_nutrition_from_base64_details_html() -> None:
    """Product details_html is base64-encoded HTML."""
    encoded = base64.b64encode(WATER_NUTRITION_HTML.encode()).decode()
    nutrition = parse_nutrition_from_details_html(encoded)
    assert isinstance(nutrition, NutritionInfo)
    assert nutrition.tables[0].rows[0].values == ["31.2"]


def test_product_from_dict_parses_nutrition() -> None:
    """Products parse nutrition from details_html when present."""
    encoded = base64.b64encode(BREAD_NUTRITION_HTML.encode()).decode()
    product = Product.from_dict(
        {
            "product_uid": "3236048",
            "name": "Warburtons Bread",
            "details_html": encoded,
        }
    )
    assert product.nutrition is not None
    assert product.nutrition.summary[0].name == "ENERGY"
    assert product.to_dict()["nutrition"]["summary"][0]["values"] == [
        "436kJ",
        "104kcal",
    ]
