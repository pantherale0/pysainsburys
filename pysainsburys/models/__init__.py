"""
Domain models for the Sainsbury's Groceries Online API.

Models are grouped by business domain:

* :mod:`pysainsburys.models.common` — shared value types and pagination
* :mod:`pysainsburys.models.product` — catalogue products and nutrition
* :mod:`pysainsburys.models.basket` — basket line items and totals
* :mod:`pysainsburys.models.customer` — authenticated customer profile
* :mod:`pysainsburys.models.order` — order history and status
* :mod:`pysainsburys.models.store` — stores and in-store product search
* :mod:`pysainsburys.models.nectar` — Nectar offers and Your Nectar Prices

Import from this package for a stable, organised surface::

    from pysainsburys.models import Product, Basket, Customer
"""

from .basket import Basket, BasketItem, basket_from_response
from .common import PageControls, Price
from .customer import Customer
from .nectar import (
    NectarOffer,
    NectarOffers,
    NectarSearchHit,
    NectarSearchResults,
    UnlockYourNectarPriceResult,
    YourNectarPriceOffer,
    YourNectarPrices,
)
from .order import OrderList, OrderStatus, OrderSummary
from .product import (
    NutrientSummary,
    NutritionInfo,
    NutritionTable,
    NutritionTableRow,
    Product,
    ProductList,
    ProductReviews,
    bind_product,
    bind_products,
    decode_details_html,
    parse_nutrition,
    parse_nutrition_from_details_html,
)
from .store import (
    FinderPage,
    Store,
    StoreList,
    StoreProduct,
    StoreProductList,
    bind_store,
    bind_stores,
)

__all__ = [
    "Basket",
    "BasketItem",
    "Customer",
    "FinderPage",
    "NectarOffer",
    "NectarOffers",
    "NectarSearchHit",
    "NectarSearchResults",
    "NutrientSummary",
    "NutritionInfo",
    "NutritionTable",
    "NutritionTableRow",
    "OrderList",
    "OrderStatus",
    "OrderSummary",
    "PageControls",
    "Price",
    "Product",
    "ProductList",
    "ProductReviews",
    "Store",
    "StoreList",
    "StoreProduct",
    "StoreProductList",
    "UnlockYourNectarPriceResult",
    "YourNectarPriceOffer",
    "YourNectarPrices",
    "basket_from_response",
    "bind_product",
    "bind_products",
    "bind_store",
    "bind_stores",
    "decode_details_html",
    "parse_nutrition",
    "parse_nutrition_from_details_html",
]
