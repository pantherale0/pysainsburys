"""Physical store and in-store product models."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ...exceptions import NotBoundError
from ..common.pagination import PageControls

if TYPE_CHECKING:
    from ...api import API


@dataclass(slots=True)
class FinderPage:
    """
    Pagination metadata from the Product Finder API.

    Attributes:
        size: Page size requested.
        number: Zero-based page index returned by Product Finder.
        total_elements: Total matching elements across all pages.
        total_pages: Total number of pages available.

    """

    size: int
    number: int
    total_elements: int
    total_pages: int

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> FinderPage:
        """Parse Product Finder pagination JSON."""
        data = data or {}
        return cls(
            size=int(data.get("size", 0)),
            number=int(data.get("number", 0)),
            total_elements=int(data.get("totalElements", 0)),
            total_pages=int(data.get("totalPages", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise pagination metadata to a plain dictionary."""
        return {
            "size": self.size,
            "number": self.number,
            "total_elements": self.total_elements,
            "total_pages": self.total_pages,
        }


@dataclass(slots=True)
class Store:
    """
    A Sainsbury's store from Product Finder or click-and-collect.

    When bound to a :class:`~pysainsburys.Sainsburys` client, a store can
    search in-store stock via :meth:`search_products`.

    Attributes:
        name: Store display name.
        address1: Primary address line.
        city: Town or city.
        post_code: UK postcode.
        is_available: Whether the store accepts online orders or collection.
        store_id: Product Finder store identifier.
        store_number: Internal store number for click-and-collect locations.
        location_uid: Click-and-collect location uid when applicable.
        address2: Secondary address line.
        county: County or region.
        opening_hours: Opening hours text when provided.
        distance: Distance from the search origin in miles or kilometres.
        telephone: Store telephone number.
        latitude: WGS-84 latitude when available.
        longitude: WGS-84 longitude when available.
        is_open: Whether the store is currently open when known.
        click_and_collect_available: Whether click-and-collect is offered.

    """

    name: str
    address1: str
    city: str
    post_code: str
    is_available: bool
    store_id: str = ""
    store_number: str | None = None
    location_uid: str | None = None
    address2: str | None = None
    county: str | None = None
    opening_hours: str | None = None
    distance: float | None = None
    telephone: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_open: bool | None = None
    click_and_collect_available: bool = False
    _api: API | None = field(default=None, repr=False, compare=False, hash=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, api: API | None = None) -> Store:
        """Parse a store from Product Finder or click-and-collect JSON."""
        if "location_uid" in data or ("store_number" in data and "id" not in data):
            return cls.from_collect_dict(data, api=api)
        distance_raw = data.get("distance")
        distance = float(distance_raw) if distance_raw not in (None, "") else None
        lat_raw = data.get("latitude")
        lon_raw = data.get("longitude")
        return cls(
            store_id=str(data.get("id") or ""),
            name=str(data.get("name") or ""),
            address1=str(data.get("address1") or ""),
            address2=data.get("address2") or None,
            city=str(data.get("city") or ""),
            post_code=str(data.get("postCode") or data.get("postcode") or ""),
            opening_hours=data.get("openingHours"),
            distance=distance,
            telephone=data.get("telephone"),
            latitude=float(lat_raw) if lat_raw is not None else None,
            longitude=float(lon_raw) if lon_raw is not None else None,
            is_available=bool(data.get("isAvailable", True)),
            is_open=data.get("isOpen"),
            click_and_collect_available=bool(data.get("isAvailable", False)),
            _api=api,
        )

    @classmethod
    def from_collect_dict(
        cls,
        data: dict[str, Any],
        *,
        api: API | None = None,
    ) -> Store:
        """Parse a click-and-collect store location from grocery API JSON."""
        distance_raw = data.get("distance")
        return cls(
            name=str(data.get("name") or ""),
            address1=str(data.get("address1") or ""),
            city=str(data.get("city") or ""),
            post_code=str(data.get("postcode") or ""),
            is_available=bool(data.get("is_available", True)),
            location_uid=str(data.get("location_uid") or "") or None,
            store_number=str(data.get("store_number") or "") or None,
            address2=data.get("address2") or None,
            county=data.get("county") or None,
            distance=float(distance_raw) if distance_raw is not None else None,
            click_and_collect_available=bool(data.get("is_available", True)),
            _api=api,
        )

    def _require_api(self) -> API:
        if self._api is None:
            msg = (
                "Store is not bound to a Sainsburys client; "
                "fetch it via Sainsburys.find_stores(), find_stores_by_postcode(), "
                "or get_store()."
            )
            raise NotBoundError(msg)
        return self._api

    def bind_api(self, api: API) -> Store:
        """Attach a client for in-store product lookups."""
        self._api = api
        return self

    @property
    def product_finder_id(self) -> str:
        """Return the Product Finder store id used for in-store product search."""
        return self.store_id

    async def search_products(
        self,
        keyword: str,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> StoreProductList:
        """Search in-store products with aisle and stock for this store."""
        response = await self._require_api().send_product_finder_request(
            "/v2/products",
            params={
                "storeId": self.store_id,
                "keyword": keyword,
                "page": page,
                "size": page_size,
            },
        )
        if not isinstance(response, dict):
            msg = "Store product search response was not a JSON object."
            raise TypeError(msg)
        return StoreProductList.from_dict(response)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the store to a plain dictionary."""
        return {
            "store_id": self.store_id,
            "store_number": self.store_number,
            "location_uid": self.location_uid,
            "name": self.name,
            "address1": self.address1,
            "address2": self.address2,
            "city": self.city,
            "county": self.county,
            "post_code": self.post_code,
            "opening_hours": self.opening_hours,
            "distance": self.distance,
            "telephone": self.telephone,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "is_available": self.is_available,
            "is_open": self.is_open,
            "click_and_collect_available": self.click_and_collect_available,
        }


@dataclass(slots=True)
class StoreList:
    """A paginated list of stores."""

    stores: list[Store]
    page: FinderPage | None = None
    controls: PageControls | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, api: API | None = None) -> StoreList:
        """Parse stores from Product Finder or click-and-collect JSON."""
        if "locations" in data:
            stores = [
                Store.from_dict(item, api=api) for item in data.get("locations", [])
            ]
            return cls(
                stores=stores,
                controls=PageControls.from_dict(data.get("controls")),
            )
        stores = [Store.from_dict(item, api=api) for item in data.get("content", [])]
        return cls(stores=stores, page=FinderPage.from_dict(data.get("page")))

    def to_dict(self) -> dict[str, Any]:
        """Serialise the store list to a plain dictionary."""
        payload: dict[str, Any] = {
            "stores": [store.to_dict() for store in self.stores],
        }
        if self.page is not None:
            payload["page"] = self.page.to_dict()
        if self.controls is not None:
            payload["controls"] = self.controls.to_dict()
        return payload


@dataclass(slots=True)
class StoreProduct:
    """
    A product with in-store aisle and stock information.

    Attributes:
        product_code: In-store product code used by Product Finder.
        name: Shelf label product name.
        stock: Stock status string (for example ``In Stock``).
        price: Shelf price in pounds sterling.
        price_per_unit: Normalised unit price when provided.
        unit_of_measure: Unit label for ``price_per_unit``.
        aisle: Aisle number or location hint in the store.
        image_url: Product image URL when available.
        is_nectar_price: Whether the price is a Nectar offer.
        promotions: Raw promotion payloads from Product Finder.

    """

    product_code: str
    name: str
    stock: str
    price: float | None = None
    price_per_unit: float | None = None
    unit_of_measure: str | None = None
    aisle: str | None = None
    image_url: str | None = None
    is_nectar_price: bool = False
    promotions: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoreProduct:
        """Parse an in-store product from Product Finder JSON."""
        retail = data.get("retail") or {}
        price_raw = retail.get("price")
        ppu_raw = retail.get("pricePerUnit")
        return cls(
            product_code=str(data.get("productCode") or ""),
            name=str(data.get("productName") or ""),
            stock=str(data.get("stock") or ""),
            price=float(price_raw) if price_raw not in (None, "") else None,
            price_per_unit=float(ppu_raw) if ppu_raw not in (None, "") else None,
            unit_of_measure=data.get("unitOfMeasure"),
            aisle=data.get("aisle"),
            image_url=data.get("image"),
            is_nectar_price=bool(data.get("isNectarPrice", False)),
            promotions=list(data.get("promotions") or []),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the in-store product to a plain dictionary."""
        return {
            "product_code": self.product_code,
            "name": self.name,
            "stock": self.stock,
            "price": self.price,
            "price_per_unit": self.price_per_unit,
            "unit_of_measure": self.unit_of_measure,
            "aisle": self.aisle,
            "image_url": self.image_url,
            "is_nectar_price": self.is_nectar_price,
            "promotions": self.promotions,
        }


@dataclass(slots=True)
class StoreProductList:
    """In-store product search results for a chosen store."""

    products: list[StoreProduct]
    page: FinderPage
    suggested_search_terms: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoreProductList:
        """Parse in-store product results from Product Finder JSON."""
        products = [StoreProduct.from_dict(item) for item in data.get("content", [])]
        return cls(
            products=products,
            page=FinderPage.from_dict(data.get("page")),
            suggested_search_terms=[
                str(term) for term in data.get("suggestedSearchTerms", [])
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise in-store product results to a plain dictionary."""
        return {
            "products": [product.to_dict() for product in self.products],
            "page": self.page.to_dict(),
            "suggested_search_terms": self.suggested_search_terms,
        }

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        """Allow ``dict(store_product_list)`` conversion."""
        return iter(self.to_dict().items())


def bind_store(api: API, store: Store) -> Store:
    """Attach an API client to a store for in-store product lookups."""
    return store.bind_api(api)


def bind_stores(api: API, stores: list[Store]) -> list[Store]:
    """Attach an API client to each store in a list."""
    for store in stores:
        bind_store(api, store)
    return stores
