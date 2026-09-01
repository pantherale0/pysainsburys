"""Grocery catalogue product models."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ...basket import resolve_basket_item_uid
from ...exceptions import NotBoundError
from ..basket.basket import Basket, basket_from_response
from ..common.pagination import PageControls
from ..common.price import Price
from .nutrition import NutritionInfo, parse_nutrition_from_details_html

if TYPE_CHECKING:
    from ...api import API


@dataclass(slots=True)
class ProductReviews:
    """
    Aggregated review metadata for a product.

    Attributes:
        is_enabled: Whether reviews are shown for this product.
        product_uid: Product identifier referenced by the review service.
        total: Number of published reviews.
        average_rating: Mean star rating across reviews.

    """

    is_enabled: bool
    product_uid: str | None
    total: int
    average_rating: float

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ProductReviews | None:
        """Parse review metadata from grocery API JSON."""
        if not data:
            return None
        return cls(
            is_enabled=bool(data.get("is_enabled", False)),
            product_uid=data.get("product_uid"),
            total=int(data.get("total", 0)),
            average_rating=float(data.get("average_rating", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise review metadata to a plain dictionary."""
        return {
            "is_enabled": self.is_enabled,
            "product_uid": self.product_uid,
            "total": self.total,
            "average_rating": self.average_rating,
        }


@dataclass(slots=True)
class Product:
    """
    A grocery product from the online catalogue.

    When bound to a :class:`~pysainsburys.Sainsburys` client, a product can
    mutate the authenticated customer's basket directly via
    :meth:`add_to_basket`, :meth:`set_basket_quantity`, and
    :meth:`remove_from_basket`.

    Nutrition data is parsed automatically from ``details_html`` when present
    on the API response (see :attr:`nutrition`).

    Attributes:
        product_uid: Stable Sainsbury's product identifier.
        name: Display name shown on the website and app.
        sain_id: Legacy SAIN identifier when returned by the API.
        is_favourite: Whether the product is in the signed-in customer's
            favourites list.
        favourite_type: Favourite list type when provided by the API.
        product_type: Product classification string from the API.
        eans: European article numbers associated with the product.
        unit_price: Price per unit of measure, when available.
        retail_price: Shelf price for the purchasable quantity.
        is_available: Whether the product can be added to a basket.
        is_alcoholic: Whether age-restricted checks apply.
        reviews: Aggregated review metadata.
        image_url: Product listing image URL.
        nutrition: Parsed nutrition tables and traffic-light summary.

    """

    product_uid: str
    name: str
    sain_id: str | None = None
    is_favourite: bool = False
    favourite_type: str | None = None
    product_type: str | None = None
    eans: list[str] = field(default_factory=list)
    unit_price: Price | None = None
    retail_price: Price | None = None
    is_available: bool = True
    is_alcoholic: bool = False
    reviews: ProductReviews | None = None
    image_url: str | None = None
    nutrition: NutritionInfo | None = None
    _api: API | None = field(default=None, repr=False, compare=False, hash=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, api: API | None = None) -> Product:
        """Parse a product from grocery API JSON."""
        assets = data.get("assets") or {}
        details_html = data.get("details_html")
        return cls(
            product_uid=str(data.get("product_uid") or data.get("uid") or ""),
            name=str(data.get("name", "")),
            sain_id=data.get("sainId") or data.get("sain_id"),
            is_favourite=bool(data.get("is_favourite", False)),
            favourite_type=data.get("favourite_type"),
            product_type=data.get("product_type"),
            eans=[str(ean) for ean in data.get("eans", [])],
            unit_price=Price.from_dict(data.get("unit_price")),
            retail_price=Price.from_dict(data.get("retail_price")),
            is_available=bool(data.get("is_available", True)),
            is_alcoholic=bool(data.get("is_alcoholic", False)),
            reviews=ProductReviews.from_dict(data.get("reviews")),
            image_url=assets.get("plp_image"),
            nutrition=parse_nutrition_from_details_html(details_html),
            _api=api,
        )

    @classmethod
    def from_basket_nested(
        cls,
        data: dict[str, Any],
        *,
        api: API | None = None,
    ) -> Product:
        """Parse a product object nested inside a basket line item."""
        payload = dict(data)
        if payload.get("sku") and not payload.get("product_uid"):
            payload["product_uid"] = payload["sku"]
        return cls.from_dict(payload, api=api)

    def _require_api(self) -> API:
        if self._api is None:
            msg = (
                "Product is not bound to a Sainsburys client; "
                "fetch it via Sainsburys.get_product(), search_products(), "
                "or lookup_barcode()."
            )
            raise NotBoundError(msg)
        return self._api

    def bind_api(self, api: API) -> Product:
        """Attach a client for basket and favourites operations."""
        self._api = api
        return self

    def _default_uom(self) -> str:
        if self.retail_price and self.retail_price.measure:
            return self.retail_price.measure
        return "ea"

    async def add_to_basket(
        self,
        quantity: float = 1.0,
        *,
        selected_catchweight: str | None = None,
        uom: str | None = None,
    ) -> Basket:
        """Add this product to the basket (POST increment)."""
        if quantity <= 0:
            return await self.remove_from_basket()
        api = self._require_api()
        body: dict[str, Any] = {
            "product_uid": self.product_uid,
            "quantity": quantity,
            "uom": uom or self._default_uom(),
        }
        if selected_catchweight is not None:
            body["selected_catchweight"] = selected_catchweight
        response = await api.send_request(endpoint="add_basket_item", body=body)
        return basket_from_response(response)

    async def set_basket_quantity(
        self,
        quantity: float,
        *,
        item_uid: str | None = None,
        selected_catchweight: str | None = None,
        uom: str | None = None,
    ) -> Basket:
        """Set the absolute basket quantity for this product."""
        if quantity <= 0:
            return await self.remove_from_basket(item_uid=item_uid)
        api = self._require_api()
        resolved_item_uid = await resolve_basket_item_uid(
            api,
            self.product_uid,
            item_uid,
        )
        item: dict[str, Any] = {
            "product_uid": self.product_uid,
            "quantity": quantity,
            "uom": uom or self._default_uom(),
            "item_uid": resolved_item_uid,
        }
        if selected_catchweight is not None:
            item["selected_catchweight"] = selected_catchweight
        response = await api.send_request(
            endpoint="update_basket",
            body={"items": [item]},
        )
        return basket_from_response(response)

    async def remove_from_basket(
        self,
        *,
        item_uid: str | None = None,
        force_delete: bool = False,
    ) -> Basket:
        """Remove this product from the basket."""
        del force_delete
        api = self._require_api()
        resolved_item_uid = await resolve_basket_item_uid(
            api,
            self.product_uid,
            item_uid,
        )
        response = await api.send_request(
            endpoint="update_basket",
            body={
                "items": [
                    {
                        "product_uid": self.product_uid,
                        "quantity": 0,
                        "uom": "ea",
                        "item_uid": resolved_item_uid,
                    }
                ]
            },
        )
        return basket_from_response(response)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the product to a plain dictionary."""
        return {
            "product_uid": self.product_uid,
            "name": self.name,
            "sain_id": self.sain_id,
            "is_favourite": self.is_favourite,
            "favourite_type": self.favourite_type,
            "product_type": self.product_type,
            "eans": self.eans,
            "unit_price": self.unit_price.to_dict() if self.unit_price else None,
            "retail_price": self.retail_price.to_dict() if self.retail_price else None,
            "is_available": self.is_available,
            "is_alcoholic": self.is_alcoholic,
            "reviews": self.reviews.to_dict() if self.reviews else None,
            "image_url": self.image_url,
            "nutrition": self.nutrition.to_dict() if self.nutrition else None,
        }

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        """Allow ``dict(product)`` conversion."""
        return iter(self.to_dict().items())


@dataclass(slots=True)
class ProductList:
    """A paginated list of catalogue products."""

    products: list[Product]
    controls: PageControls

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProductList:
        """Parse a paginated product list from grocery API JSON."""
        products = [Product.from_dict(item) for item in data.get("products", [])]
        return cls(
            products=products,
            controls=PageControls.from_dict(data.get("controls")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the product list to a plain dictionary."""
        return {
            "products": [product.to_dict() for product in self.products],
            "controls": self.controls.to_dict(),
        }

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        """Allow ``dict(product_list)`` conversion."""
        return iter(self.to_dict().items())


def bind_product(api: API, product: Product) -> Product:
    """Attach an API client to a product for basket and favourites operations."""
    return product.bind_api(api)


def bind_products(api: API, products: list[Product]) -> list[Product]:
    """Attach an API client to each product in a list."""
    for product in products:
        bind_product(api, product)
    return products
