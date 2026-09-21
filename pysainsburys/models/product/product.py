"""Grocery catalogue product models."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ...exceptions import NotBoundError
from ..basket.basket import Basket, basket_from_response
from ..common.pagination import PageControls
from ..common.price import Price
from .catalogue import (
    AverageWeight,
    HfssRestriction,
    ProductBreadcrumb,
    ProductCategory,
    ProductHeader,
    ProductImage,
    ProductLabel,
    ProductPromise,
    attributes_from_api,
    breadcrumbs_from_api,
    categories_from_api,
    health_rating_from_api,
    hfss_from_api,
    images_from_api,
    labels_from_api,
    page_url,
    string_list,
    text,
)
from .details import ProductDetails, product_details_from_api
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
class Promotion:
    """
    A catalogue promotion attached to a product.

    Attributes:
        promotion_uid: Promotion identifier.
        strap_line: Customer-facing offer text, such as ``Buy 1 for 3``.
        start_date: Offer start timestamp from the API.
        end_date: Offer end timestamp from the API.
        original_price: Shelf price before the promotion, in pounds sterling.
        is_nectar: Whether the offer is a Nectar price.
        promo_type: Promotion mechanic type from the API.
        promo_group: Promotion grouping from the API.
        promo_mechanic_id: Mechanic identifier from the API.
        icon: Promotion icon URL when provided.
        link: Relative link to the promotion lister.

    """

    promotion_uid: str
    strap_line: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    original_price: float | None = None
    is_nectar: bool = False
    promo_type: str | None = None
    promo_group: str | None = None
    promo_mechanic_id: str | None = None
    icon: str | None = None
    link: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Promotion | None:
        """Parse a promotion from grocery API JSON."""
        if not data:
            return None
        promotion_uid = data.get("promotion_uid")
        if not promotion_uid and not data.get("strap_line"):
            return None
        original_price = data.get("original_price")
        mechanic_id = data.get("promo_mechanic_id")
        return cls(
            promotion_uid=str(promotion_uid or ""),
            strap_line=data.get("strap_line"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            original_price=(
                float(original_price) if original_price is not None else None
            ),
            is_nectar=bool(data.get("is_nectar", False)),
            promo_type=data.get("promo_type"),
            promo_group=data.get("promo_group"),
            promo_mechanic_id=str(mechanic_id) if mechanic_id is not None else None,
            icon=data.get("icon") or None,
            link=data.get("link"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the promotion to a plain dictionary."""
        return {
            "promotion_uid": self.promotion_uid,
            "strap_line": self.strap_line,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "original_price": self.original_price,
            "is_nectar": self.is_nectar,
            "promo_type": self.promo_type,
            "promo_group": self.promo_group,
            "promo_mechanic_id": self.promo_mechanic_id,
            "icon": self.icon,
            "link": self.link,
        }


@dataclass(slots=True)
class NectarPrice:
    """
    Nectar member price for a product.

    Attributes:
        retail_price: Nectar price for the purchasable quantity.
        unit_price: Nectar price per unit of measure, when provided.
        measure: Unit label for ``unit_price``.
        url: Link to the Nectar prices listing.
        category_seo_url: SEO path for the Nectar prices category.

    """

    retail_price: float
    unit_price: float | None = None
    measure: str | None = None
    url: str | None = None
    category_seo_url: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> NectarPrice | None:
        """Parse a Nectar price from grocery API JSON."""
        if not data or data.get("retail_price") is None:
            return None
        unit_price = data.get("unit_price")
        return cls(
            retail_price=float(data["retail_price"]),
            unit_price=float(unit_price) if unit_price is not None else None,
            measure=data.get("measure"),
            url=data.get("url"),
            category_seo_url=data.get("category_seo_url"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the Nectar price to a plain dictionary."""
        return {
            "retail_price": self.retail_price,
            "unit_price": self.unit_price,
            "measure": self.measure,
            "url": self.url,
            "category_seo_url": self.category_seo_url,
        }


def _promotions_from_api(data: dict[str, Any]) -> list[Promotion]:
    """Parse the ``promotions`` array from a product payload."""
    raw = data.get("promotions")
    if not isinstance(raw, list):
        return []
    promotions: list[Promotion] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        promotion = Promotion.from_dict(item)
        if promotion is not None:
            promotions.append(promotion)
    return promotions


@dataclass(slots=True)
class Product:
    """
    A grocery product from the online catalogue.

    When bound to a :class:`~pysainsburys.Sainsburys` client, a product can
    mutate the authenticated customer's basket directly via
    :meth:`add_to_basket`, :meth:`set_basket_quantity`, and
    :meth:`remove_from_basket`.

    Nutrition data is parsed automatically from ``details_html`` when present
    on the API response (see :attr:`nutrition`). The same HTML also supplies
    description, storage, and related copy on :attr:`details`. Search results
    omit ``details_html``, so those sections stay empty until the product is
    loaded with :meth:`~pysainsburys.Sainsburys.get_product`.

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
        details: Description, storage, and other product-text sections.
        promotions: Catalogue offers attached to the product.
        nectar_price: Nectar member price when the product has one.
        favourite_uid: Favourite-list identifier when the product is saved.
        short_description: One-line summary from the product payload.
        full_url: Absolute product page URL.
        original_unit_price: Unit price before a promotion, when the API
            returns one.
        image: Large product image URL.
        image_thumbnail: Medium product image URL.
        image_thumbnail_small: Small product image URL.
        image_zoom: Zoom image URL when provided.
        images: Sized image variants from the assets block.
        zone: Merchandising zone, such as ``Drinks``.
        department: Department name when the API returns one.
        labels: Merchandising labels such as British or Chilled.
        categories: Catalogue categories that include the product.
        breadcrumbs: Breadcrumb trail for the product page.
        attributes: Attribute groups from the API, including brand.
        header: Promotional header, such as a Nectar price banner.
        is_spotlight: Whether the product is flagged as featured.
        spotlight_label: Featured label when ``is_spotlight`` is set.
        not_for_eu: Whether the product is marked not for EU sale.
        is_intolerant: Whether the product carries an intolerance flag.
        is_mhra: Whether MHRA restrictions apply.
        is_supply_chain_orderable: Whether supply-chain ordering is enabled.
        display_icons: Icon identifiers shown on the product.
        health_rating: Health rating score from ``health_classification``.
        hfss_restrictions: HFSS advertising restrictions by UK nation.
        pdp_deep_link: Legacy product-display path.
        average_weight: Typical weight for a loose product.
        promise: Delivery promise when a slot context is present.

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
    details: ProductDetails | None = None
    promotions: list[Promotion] = field(default_factory=list)
    nectar_price: NectarPrice | None = None
    favourite_uid: str | None = None
    short_description: str | None = None
    full_url: str | None = None
    original_unit_price: Price | None = None
    image: str | None = None
    image_thumbnail: str | None = None
    image_thumbnail_small: str | None = None
    image_zoom: str | None = None
    images: list[ProductImage] = field(default_factory=list)
    zone: str | None = None
    department: str | None = None
    labels: list[ProductLabel] = field(default_factory=list)
    categories: list[ProductCategory] = field(default_factory=list)
    breadcrumbs: list[ProductBreadcrumb] = field(default_factory=list)
    attributes: dict[str, list[str]] = field(default_factory=dict)
    header: ProductHeader | None = None
    is_spotlight: bool = False
    spotlight_label: str | None = None
    not_for_eu: bool = False
    is_intolerant: bool = False
    is_mhra: bool = False
    is_supply_chain_orderable: bool = False
    display_icons: list[str] = field(default_factory=list)
    health_rating: str | None = None
    hfss_restrictions: list[HfssRestriction] = field(default_factory=list)
    pdp_deep_link: str | None = None
    average_weight: AverageWeight | None = None
    promise: ProductPromise | None = None
    _api: API | None = field(default=None, repr=False, compare=False, hash=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, api: API | None = None) -> Product:
        """Parse a product from grocery API JSON."""
        assets_raw = data.get("assets")
        assets: dict[str, Any] = assets_raw if isinstance(assets_raw, dict) else {}
        details_html = data.get("details_html")
        if not isinstance(details_html, str):
            details_html = None
        header_raw = data.get("header")
        header = header_raw if isinstance(header_raw, dict) else None
        weight = data.get("average_weight")
        promise_raw = data.get("promise")
        promise = promise_raw if isinstance(promise_raw, dict) else None
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
            image_url=text(assets.get("plp_image")),
            nutrition=parse_nutrition_from_details_html(details_html),
            details=product_details_from_api(details_html, data.get("description")),
            promotions=_promotions_from_api(data),
            nectar_price=NectarPrice.from_dict(
                data["nectar_price"]
                if isinstance(data.get("nectar_price"), dict)
                else None
            ),
            favourite_uid=text(data.get("favourite_uid")),
            short_description=text(data.get("short_description")),
            full_url=page_url(data.get("full_url")),
            original_unit_price=Price.from_dict(
                data["original_unit_price"]
                if isinstance(data.get("original_unit_price"), dict)
                else None
            ),
            image=text(data.get("image")),
            image_thumbnail=text(data.get("image_thumbnail")),
            image_thumbnail_small=text(data.get("image_thumbnail_small")),
            image_zoom=text(data.get("image_zoom")),
            images=images_from_api(assets),
            zone=text(data.get("zone")),
            department=text(data.get("department")),
            labels=labels_from_api(data),
            categories=categories_from_api(data),
            breadcrumbs=breadcrumbs_from_api(data),
            attributes=attributes_from_api(data),
            header=ProductHeader.from_dict(header),
            is_spotlight=bool(data.get("is_spotlight", False)),
            spotlight_label=text(data.get("spotlight_label")),
            not_for_eu=bool(data.get("not_for_eu", False)),
            is_intolerant=bool(data.get("is_intolerant", False)),
            is_mhra=bool(data.get("is_mhra", False)),
            is_supply_chain_orderable=bool(
                data.get("is_supply_chain_orderable", False)
            ),
            display_icons=string_list(data.get("display_icons")),
            health_rating=health_rating_from_api(data),
            hfss_restrictions=hfss_from_api(data),
            pdp_deep_link=text(data.get("pdp_deep_link")),
            average_weight=AverageWeight.from_dict(
                weight if isinstance(weight, dict) else None
            ),
            promise=ProductPromise.from_dict(promise),
            _api=api,
        )

    @property
    def brand(self) -> list[str]:
        """Brand names from the product attributes."""
        return list(self.attributes.get("brand", []))

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
                "fetch it via Sainsburys.get_product() or search_products()."
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

    async def _resolve_basket_item_uid(self, item_uid: str | None) -> str:
        """Resolve a basket line uid without importing basket at module load."""
        from ...basket import resolve_basket_item_uid

        return await resolve_basket_item_uid(
            self._require_api(),
            self.product_uid,
            item_uid,
        )

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
        resolved_item_uid = await self._resolve_basket_item_uid(item_uid)
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
        resolved_item_uid = await self._resolve_basket_item_uid(item_uid)
        response = await self._require_api().send_request(
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
            "details": self.details.to_dict() if self.details else None,
            "promotions": [promotion.to_dict() for promotion in self.promotions],
            "nectar_price": (
                self.nectar_price.to_dict() if self.nectar_price else None
            ),
            "favourite_uid": self.favourite_uid,
            "short_description": self.short_description,
            "full_url": self.full_url,
            "original_unit_price": (
                self.original_unit_price.to_dict() if self.original_unit_price else None
            ),
            "image": self.image,
            "image_thumbnail": self.image_thumbnail,
            "image_thumbnail_small": self.image_thumbnail_small,
            "image_zoom": self.image_zoom,
            "images": [image.to_dict() for image in self.images],
            "zone": self.zone,
            "department": self.department,
            "labels": [label.to_dict() for label in self.labels],
            "categories": [category.to_dict() for category in self.categories],
            "breadcrumbs": [crumb.to_dict() for crumb in self.breadcrumbs],
            "attributes": self.attributes,
            "brand": self.brand,
            "header": self.header.to_dict() if self.header else None,
            "is_spotlight": self.is_spotlight,
            "spotlight_label": self.spotlight_label,
            "not_for_eu": self.not_for_eu,
            "is_intolerant": self.is_intolerant,
            "is_mhra": self.is_mhra,
            "is_supply_chain_orderable": self.is_supply_chain_orderable,
            "display_icons": self.display_icons,
            "health_rating": self.health_rating,
            "hfss_restrictions": [
                restriction.to_dict() for restriction in self.hfss_restrictions
            ],
            "pdp_deep_link": self.pdp_deep_link,
            "average_weight": (
                self.average_weight.to_dict() if self.average_weight else None
            ),
            "promise": self.promise.to_dict() if self.promise else None,
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
