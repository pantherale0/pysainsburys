"""Nectar offers and Your Nectar Price models."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from ..product.product import Product


@dataclass(slots=True)
class NectarOffer:
    """
    A personalised Nectar bonus-points offer.

    Attributes:
        offer_id: Offer identifier from the Nectar API.
        title: Short offer headline.
        subtitle: Supporting offer copy.
        points: Bonus Nectar points awarded.
        skus: Product SKUs included in the offer.
        expires: Offer expiry timestamp when provided.

    """

    offer_id: str
    title: str
    subtitle: str
    points: int
    skus: list[str] = field(default_factory=list)
    expires: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NectarOffer:
        """Parse a Nectar offer from grocery API JSON."""
        skus = data.get("skus")
        if not isinstance(skus, list):
            skus = []
        return cls(
            offer_id=str(data.get("id") or data.get("offer_id") or ""),
            title=str(data.get("title") or ""),
            subtitle=str(data.get("subtitle") or ""),
            points=int(data.get("points", 0)),
            skus=[str(sku) for sku in skus],
            expires=data.get("expires") or data.get("expiry_date"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the offer to a plain dictionary."""
        return {
            "offer_id": self.offer_id,
            "title": self.title,
            "subtitle": self.subtitle,
            "points": self.points,
            "skus": self.skus,
            "expires": self.expires,
        }


@dataclass(slots=True)
class NectarOffers:
    """
    Nectar bonus-point offers for the signed-in customer.

    Attributes:
        account_status: Nectar linkage status from the API.
        offers: Active bonus-point offers.

    """

    account_status: str | None = None
    offers: list[NectarOffer] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NectarOffers:
        """Parse Nectar offers from grocery API JSON."""
        offers = [
            NectarOffer.from_dict(item)
            for item in data.get("offers", [])
            if isinstance(item, dict)
        ]
        return cls(
            account_status=data.get("account_status"),
            offers=offers,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the offers response to a plain dictionary."""
        return {
            "account_status": self.account_status,
            "offers": [offer.to_dict() for offer in self.offers],
        }

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        """Allow ``dict(offers)`` conversion."""
        return iter(self.to_dict().items())


@dataclass(slots=True)
class YourNectarPriceOffer:
    """
    A Your Nectar Price weekly offer.

    Attributes:
        offer_id: Offer identifier used for opt-in requests.
        sku: Product SKU the offer applies to.
        start_date: Offer start timestamp.
        expiry_date: Offer expiry timestamp.
        image: Product image URL when provided.
        product: Enriched catalogue product when fetched separately.

    """

    offer_id: str
    sku: str
    start_date: str | None = None
    expiry_date: str | None = None
    image: str | None = None
    product: Product | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> YourNectarPriceOffer:
        """Parse a Your Nectar Price offer from grocery API JSON."""
        return cls(
            offer_id=str(data.get("offer_id") or ""),
            sku=str(data.get("sku") or ""),
            start_date=data.get("start_date"),
            expiry_date=data.get("expiry_date"),
            image=data.get("image"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the offer to a plain dictionary."""
        return {
            "offer_id": self.offer_id,
            "sku": self.sku,
            "start_date": self.start_date,
            "expiry_date": self.expiry_date,
            "image": self.image,
            "product": self.product.to_dict() if self.product else None,
        }


@dataclass(slots=True)
class YourNectarPrices:
    """
    Your Nectar Price opt-in state for the signed-in customer.

    Attributes:
        opted_in: Offers the customer has unlocked.
        not_opted_in: Offers still waiting to be unlocked.
        available_until: When the current YNP selection window closes.
        released_on: When the current YNP offers were released.

    """

    opted_in: list[YourNectarPriceOffer] = field(default_factory=list)
    not_opted_in: list[YourNectarPriceOffer] = field(default_factory=list)
    available_until: str | None = None
    released_on: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> YourNectarPrices:
        """Parse Your Nectar Price opt-ins from grocery API JSON."""
        return cls(
            opted_in=[
                YourNectarPriceOffer.from_dict(item)
                for item in data.get("opted_in", [])
                if isinstance(item, dict)
            ],
            not_opted_in=[
                YourNectarPriceOffer.from_dict(item)
                for item in data.get("not_opted_in", [])
                if isinstance(item, dict)
            ],
            available_until=data.get("ynps_available_until"),
            released_on=data.get("ynps_released_on"),
        )

    @property
    def all_offers(self) -> list[YourNectarPriceOffer]:
        """Return opted-in and locked offers together."""
        return [*self.opted_in, *self.not_opted_in]

    def to_dict(self) -> dict[str, Any]:
        """Serialise the YNP response to a plain dictionary."""
        return {
            "opted_in": [offer.to_dict() for offer in self.opted_in],
            "not_opted_in": [offer.to_dict() for offer in self.not_opted_in],
            "available_until": self.available_until,
            "released_on": self.released_on,
        }

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        """Allow ``dict(prices)`` conversion."""
        return iter(self.to_dict().items())


@dataclass(slots=True)
class UnlockYourNectarPriceResult:
    """Result of unlocking Your Nectar Price offers."""

    updated_offer_ids: list[str] = field(default_factory=list)
    offer_response_failures: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UnlockYourNectarPriceResult:
        """Parse an unlock response from grocery API JSON."""
        failures = data.get("offer_response_failures")
        if not isinstance(failures, list):
            failures = []
        updated = data.get("updated_offer_ids")
        if not isinstance(updated, list):
            updated = []
        return cls(
            updated_offer_ids=[str(offer_id) for offer_id in updated],
            offer_response_failures=[
                failure for failure in failures if isinstance(failure, dict)
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the unlock response to a plain dictionary."""
        return {
            "updated_offer_ids": self.updated_offer_ids,
            "offer_response_failures": self.offer_response_failures,
        }


@dataclass(slots=True)
class NectarSearchHit:
    """A single Nectar search result."""

    kind: str
    offer_id: str | None = None
    title: str | None = None
    subtitle: str | None = None
    points: int | None = None
    sku: str | None = None
    expires: str | None = None
    opted_in: bool | None = None
    product: Product | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise the search hit to a plain dictionary."""
        return {
            "kind": self.kind,
            "offer_id": self.offer_id,
            "title": self.title,
            "subtitle": self.subtitle,
            "points": self.points,
            "sku": self.sku,
            "expires": self.expires,
            "opted_in": self.opted_in,
            "product": self.product.to_dict() if self.product else None,
        }


@dataclass(slots=True)
class NectarSearchResults:
    """Keyword search results across Nectar offers and Your Nectar Prices."""

    query: str
    hits: list[NectarSearchHit] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialise search results to a plain dictionary."""
        return {
            "query": self.query,
            "hits": [hit.to_dict() for hit in self.hits],
        }
