# Models

Domain types are organised under :mod:`pysainsburys.models`, grouped by business
area. Each submodule exposes dataclasses with ``from_dict`` / ``to_dict``
helpers for API JSON.

## Package layout

```
pysainsburys.models
├── common/          # Shared value types
│   ├── Price
│   └── PageControls
├── product/         # Online catalogue
│   ├── Product, ProductList, ProductReviews
│   └── nutrition    # NutritionInfo, parsers
├── basket/          # Basket, BasketItem
├── customer/        # Customer profile
├── order/           # OrderSummary, OrderList, OrderStatus
└── store/           # Store, StoreProduct, Product Finder pagination
```

## Importing

Prefer the models package for new code:

```python
from pysainsburys.models import Product, Basket, Customer, NutritionInfo
from pysainsburys.models.product import parse_nutrition_from_details_html
from pysainsburys.models.common import Price, PageControls
```

Top-level names (``from pysainsburys import Product``) are also re-exported from
the root package for convenience.

## Common

| Type | Purpose |
| --- | --- |
| :class:`~pysainsburys.models.common.price.Price` | Monetary amount with optional unit of measure |
| :class:`~pysainsburys.models.common.pagination.PageControls` | Grocery API list pagination metadata |

## Product

| Type | Purpose |
| --- | --- |
| :class:`~pysainsburys.models.product.product.Product` | Catalogue product; supports basket mutations when bound to a client |
| :class:`~pysainsburys.models.product.product.ProductList` | Paginated search or favourites results |
| :class:`~pysainsburys.models.product.product.ProductReviews` | Review count and average rating |
| :class:`~pysainsburys.models.product.nutrition.NutritionInfo` | Parsed nutrition summary, tables, and footnotes |

Nutrition is extracted from the ``details_html`` field on product detail
responses (base64-encoded HTML from the website). Use
:func:`~pysainsburys.models.product.nutrition.parse_nutrition_from_details_html`
to parse raw API payloads directly.

## Basket

| Type | Purpose |
| --- | --- |
| :class:`~pysainsburys.models.basket.basket.Basket` | Basket totals and line items |
| :class:`~pysainsburys.models.basket.basket.BasketItem` | Single basket line |

Authenticated fetch/clear operations are provided by
:class:`~pysainsburys.basket.BasketAccess` on
``customer.basket``.

## Customer

| Type | Purpose |
| --- | --- |
| :class:`~pysainsburys.models.customer.customer.Customer` | Signed-in profile with ``basket``, ``favourites``, and ``orders`` accessors |

## Order

| Type | Purpose |
| --- | --- |
| :class:`~pysainsburys.models.order.order.OrderSummary` | Order in a history list |
| :class:`~pysainsburys.models.order.order.OrderList` | Paginated order history |
| :class:`~pysainsburys.models.order.order.OrderStatus` | Live status for the active slot |

Per-order helpers live in :class:`~pysainsburys.orders.OrderHandle` and
:class:`~pysainsburys.orders.Orders`.

## Store

| Type | Purpose |
| --- | --- |
| :class:`~pysainsburys.models.store.store.Store` | Physical store; supports in-store search when bound |
| :class:`~pysainsburys.models.store.store.StoreList` | Paginated store search results |
| :class:`~pysainsburys.models.store.store.StoreProduct` | In-store product with aisle and stock |
| :class:`~pysainsburys.models.store.store.StoreProductList` | In-store search results |
| :class:`~pysainsburys.models.store.store.FinderPage` | Product Finder pagination metadata |

## Serialisation

All models support ``to_dict()`` and many support ``dict(model)`` via
``__iter__``. Round-trip parsing uses ``from_dict`` class methods on each type.
