"""Catalogue product models and nutrition parsing."""

from .nutrition import (
    NutrientSummary,
    NutritionInfo,
    NutritionTable,
    NutritionTableRow,
    decode_details_html,
    parse_nutrition,
    parse_nutrition_from_details_html,
)
from .product import (
    Product,
    ProductList,
    ProductReviews,
    bind_product,
    bind_products,
)

__all__ = [
    "NutrientSummary",
    "NutritionInfo",
    "NutritionTable",
    "NutritionTableRow",
    "Product",
    "ProductList",
    "ProductReviews",
    "bind_product",
    "bind_products",
    "decode_details_html",
    "parse_nutrition",
    "parse_nutrition_from_details_html",
]
