"""Structured catalogue fields parsed from a grocery product payload."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def text(value: Any) -> str | None:
    """Return a stripped string, or ``None`` when the value is empty."""
    if value is None:
        return None
    rendered = str(value).strip()
    return rendered or None


def page_url(value: Any) -> str | None:
    """Normalise a product page URL, including protocol-relative values."""
    url = text(value)
    if url and url.startswith("://"):
        return f"https{url}"
    return url


def string_list(value: Any) -> list[str]:
    """Return the non-empty strings in a JSON list."""
    if not isinstance(value, list):
        return []
    return [item for item in (text(entry) for entry in value) if item]


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


@dataclass(slots=True)
class ProductLabel:
    """A merchandising label such as ``British`` or ``Chilled``."""

    label_uid: str
    text: str | None = None
    alt_text: str | None = None
    color: str | None = None
    link: str | None = None
    link_opens_in_new_window: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ProductLabel | None:
        """Parse a label from grocery API JSON."""
        if not data:
            return None
        label_uid = text(data.get("label_uid") or data.get("text"))
        if not label_uid:
            return None
        return cls(
            label_uid=label_uid,
            text=text(data.get("text")),
            alt_text=text(data.get("alt_text")),
            color=text(data.get("color")),
            link=text(data.get("link")),
            link_opens_in_new_window=bool(data.get("link_opens_in_new_window", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the label to a plain dictionary."""
        return {
            "label_uid": self.label_uid,
            "text": self.text,
            "alt_text": self.alt_text,
            "color": self.color,
            "link": self.link,
            "link_opens_in_new_window": self.link_opens_in_new_window,
        }


@dataclass(slots=True)
class ProductCategory:
    """A catalogue category the product belongs to."""

    category_id: str
    name: str

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ProductCategory | None:
        """Parse a category from grocery API JSON."""
        if not data:
            return None
        category_id = text(data.get("id") or data.get("category_id"))
        name = text(data.get("name"))
        if not category_id or not name:
            return None
        return cls(category_id=category_id, name=name)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the category to a plain dictionary."""
        return {"category_id": self.category_id, "name": self.name}


@dataclass(slots=True)
class ProductBreadcrumb:
    """One step in the product page breadcrumb trail."""

    label: str
    url: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ProductBreadcrumb | None:
        """Parse a breadcrumb from grocery API JSON."""
        if not data:
            return None
        label = text(data.get("label"))
        if not label:
            return None
        return cls(label=label, url=page_url(data.get("url")))

    def to_dict(self) -> dict[str, Any]:
        """Serialise the breadcrumb to a plain dictionary."""
        return {"label": self.label, "url": self.url}


@dataclass(slots=True)
class ProductHeader:
    """Promotional header shown above the product, such as a Nectar price."""

    text: str | None = None
    type: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ProductHeader | None:
        """Parse a product header from grocery API JSON."""
        if not data:
            return None
        header_text = text(data.get("text"))
        header_type = text(data.get("type"))
        if not header_text and not header_type:
            return None
        return cls(text=header_text, type=header_type)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the header to a plain dictionary."""
        return {"text": self.text, "type": self.type}


@dataclass(slots=True)
class ProductImageSize:
    """One rendered size of a product image."""

    url: str
    width: int | None = None
    height: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ProductImageSize | None:
        """Parse an image size from grocery API JSON."""
        if not data:
            return None
        url = text(data.get("url"))
        if not url:
            return None
        return cls(
            url=url,
            width=_int(data.get("width")),
            height=_int(data.get("height")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the image size to a plain dictionary."""
        return {"url": self.url, "width": self.width, "height": self.height}


@dataclass(slots=True)
class ProductImage:
    """A product image and the sizes the API provides for it."""

    image_id: str | None = None
    sizes: list[ProductImageSize] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ProductImage | None:
        """Parse a product image from grocery API JSON."""
        if not data:
            return None
        sizes = [
            size
            for item in _mapping_list(data.get("sizes"))
            if (size := ProductImageSize.from_dict(item)) is not None
        ]
        image_id = text(data.get("id") or data.get("image_id"))
        if not image_id and not sizes:
            return None
        return cls(image_id=image_id, sizes=sizes)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the product image to a plain dictionary."""
        return {
            "image_id": self.image_id,
            "sizes": [size.to_dict() for size in self.sizes],
        }


@dataclass(slots=True)
class AverageWeight:
    """Typical weight for a loose product."""

    amount: float
    measure: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> AverageWeight | None:
        """Parse an average weight from grocery API JSON."""
        if not data or data.get("amount") is None:
            return None
        return cls(amount=float(data["amount"]), measure=text(data.get("measure")))

    def to_dict(self) -> dict[str, Any]:
        """Serialise the average weight to a plain dictionary."""
        return {"amount": self.amount, "measure": self.measure}


@dataclass(slots=True)
class HfssRestriction:
    """HFSS advertising restriction for one UK nation."""

    country: str
    restricted: bool
    category: str | None = None
    score: int | None = None
    last_change_date: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> HfssRestriction | None:
        """Parse an HFSS restriction from grocery API JSON."""
        if not data:
            return None
        country = text(data.get("country"))
        if not country:
            return None
        return cls(
            country=country,
            restricted=bool(data.get("restricted", False)),
            category=text(data.get("hfss_category")),
            score=_int(data.get("hfss_score")),
            last_change_date=text(data.get("last_change_date")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the HFSS restriction to a plain dictionary."""
        return {
            "country": self.country,
            "restricted": self.restricted,
            "category": self.category,
            "score": self.score,
            "last_change_date": self.last_change_date,
        }


@dataclass(slots=True)
class ProductPromise:
    """Delivery promise attached to a product when a slot context exists."""

    type: str | None = None
    earliest_promise_date: str | None = None
    last_amendment_date: str | None = None
    status_label: str | None = None
    status_type: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ProductPromise | None:
        """Parse a product promise from grocery API JSON."""
        if not data:
            return None
        status_raw = data.get("status")
        status = status_raw if isinstance(status_raw, dict) else {}
        promise = cls(
            type=text(data.get("type")),
            earliest_promise_date=text(data.get("earliest_promise_date")),
            last_amendment_date=text(data.get("last_amendment_date")),
            status_label=text(status.get("label")),
            status_type=text(status.get("type")),
        )
        if promise.status_type == "NONE":
            promise.status_type = None
        if promise.is_empty():
            return None
        return promise

    def is_empty(self) -> bool:
        """Return whether the promise carries no slot information."""
        return all(
            value is None
            for value in (
                self.type,
                self.earliest_promise_date,
                self.last_amendment_date,
                self.status_label,
                self.status_type,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the promise to a plain dictionary."""
        return {
            "type": self.type,
            "earliest_promise_date": self.earliest_promise_date,
            "last_amendment_date": self.last_amendment_date,
            "status_label": self.status_label,
            "status_type": self.status_type,
        }


def labels_from_api(data: dict[str, Any]) -> list[ProductLabel]:
    """Parse product labels."""
    return [
        label
        for item in _mapping_list(data.get("labels"))
        if (label := ProductLabel.from_dict(item)) is not None
    ]


def categories_from_api(data: dict[str, Any]) -> list[ProductCategory]:
    """Parse product categories."""
    return [
        category
        for item in _mapping_list(data.get("categories"))
        if (category := ProductCategory.from_dict(item)) is not None
    ]


def breadcrumbs_from_api(data: dict[str, Any]) -> list[ProductBreadcrumb]:
    """Parse product breadcrumbs."""
    return [
        crumb
        for item in _mapping_list(data.get("breadcrumbs"))
        if (crumb := ProductBreadcrumb.from_dict(item)) is not None
    ]


def images_from_api(assets: dict[str, Any]) -> list[ProductImage]:
    """Parse sized images from the product assets object."""
    return [
        image
        for item in _mapping_list(assets.get("images"))
        if (image := ProductImage.from_dict(item)) is not None
    ]


def attributes_from_api(data: dict[str, Any]) -> dict[str, list[str]]:
    """Parse product attributes, such as brand."""
    raw = data.get("attributes")
    if not isinstance(raw, dict):
        return {}
    attributes: dict[str, list[str]] = {}
    for key, value in raw.items():
        if isinstance(value, list):
            items = [item for item in (text(entry) for entry in value) if item]
        else:
            rendered = text(value)
            items = [rendered] if rendered else []
        if items:
            attributes[str(key)] = items
    return attributes


def hfss_from_api(data: dict[str, Any]) -> list[HfssRestriction]:
    """Parse HFSS restrictions."""
    return [
        restriction
        for item in _mapping_list(data.get("hfss_restriction"))
        if (restriction := HfssRestriction.from_dict(item)) is not None
    ]


def health_rating_from_api(data: dict[str, Any]) -> str | None:
    """Parse the health rating score from ``health_classification``."""
    raw = data.get("health_classification")
    if not isinstance(raw, dict):
        return None
    return text(raw.get("health_rating_score_value"))


def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)
