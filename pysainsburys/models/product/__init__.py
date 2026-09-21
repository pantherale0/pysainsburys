"""Catalogue product models, detail sections, and nutrition parsing."""

from .details import (
    ProductDetails,
    parse_product_details,
    parse_product_details_from_details_html,
)
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
    NectarPrice,
    Product,
    ProductList,
    ProductReviews,
    Promotion,
    bind_product,
    bind_products,
)

__all__ = [
    "NectarPrice",
    "NutrientSummary",
    "NutritionInfo",
    "NutritionTable",
    "NutritionTableRow",
    "Product",
    "ProductDetails",
    "ProductList",
    "ProductReviews",
    "Promotion",
    "bind_product",
    "bind_products",
    "decode_details_html",
    "parse_nutrition",
    "parse_nutrition_from_details_html",
    "parse_product_details",
    "parse_product_details_from_details_html",
]
