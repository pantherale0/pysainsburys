"""Authenticated customer profile models."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ...exceptions import NotBoundError

if TYPE_CHECKING:
    from ...api import API
    from ...basket import BasketAccess
    from ...favourites import Favourites
    from ...nectar import Nectar
    from ...orders import Orders
    from ...slots import Slots


@dataclass(slots=True)
class Customer:
    """
    Authenticated Sainsbury's Groceries Online customer profile.

    A customer is returned by :meth:`~pysainsburys.Sainsburys.get_customer` and
    exposes convenience accessors for basket, favourites, orders, and slot
    resources when bound to a client.

    Attributes:
        user_id: Commerce platform user identifier.
        customer_id: Customer record identifier when distinct from ``user_id``.
        identity_id: Identity provider subject identifier.
        email: Account email address.
        family_name: Family name from the profile.
        given_name: Given name from the profile.
        primary_phone: Primary contact telephone number.
        postcode: Default delivery postcode when set.
        title: Salutation or title when provided.
        is_very_important_customer: VIP flag from the API.
        delivery_pass_expiry_date: Delivery pass expiry when subscribed.
        personalization_id: Personalisation token for recommendations.
        has_nectar_associated: Whether a Nectar card is associated.
        has_nectar_linked: Whether Nectar is fully linked for rewards.
        is_digital_nectar: Whether the account uses digital Nectar.

    """

    user_id: str
    customer_id: str | None = None
    identity_id: str | None = None
    email: str | None = None
    family_name: str | None = None
    given_name: str | None = None
    primary_phone: str | None = None
    postcode: str | None = None
    title: str | None = None
    is_very_important_customer: bool = False
    delivery_pass_expiry_date: str | None = None
    personalization_id: str | None = None
    has_nectar_associated: bool = False
    has_nectar_linked: bool = False
    is_digital_nectar: bool = False
    _api: API | None = field(default=None, repr=False, compare=False, hash=False)
    _favourites: Favourites | None = field(
        default=None, init=False, repr=False, compare=False, hash=False
    )
    _basket_access: BasketAccess | None = field(
        default=None, init=False, repr=False, compare=False, hash=False
    )
    _orders: Orders | None = field(
        default=None, init=False, repr=False, compare=False, hash=False
    )
    _nectar: Nectar | None = field(
        default=None, init=False, repr=False, compare=False, hash=False
    )
    _slots: Slots | None = field(
        default=None, init=False, repr=False, compare=False, hash=False
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, api: API | None = None) -> Customer:
        """Parse a customer profile from grocery API JSON."""
        return cls(
            user_id=str(data.get("user_id", "")),
            customer_id=data.get("customer_id"),
            identity_id=data.get("identity_id"),
            email=data.get("email"),
            family_name=data.get("family_name"),
            given_name=data.get("given_name"),
            primary_phone=data.get("primary_phone"),
            postcode=data.get("postcode"),
            title=data.get("title"),
            is_very_important_customer=bool(
                data.get("is_very_important_customer", False)
            ),
            delivery_pass_expiry_date=data.get("delivery_pass_expiry_date"),
            personalization_id=data.get("personalization_id"),
            has_nectar_associated=bool(data.get("has_nectar_associated", False)),
            has_nectar_linked=bool(data.get("has_nectar_linked", False)),
            is_digital_nectar=bool(data.get("is_digital_nectar", False)),
            _api=api,
        )

    def _require_api(self) -> API:
        if self._api is None:
            msg = "Customer is not bound to a Sainsburys client."
            raise NotBoundError(msg)
        return self._api

    @property
    def favourites(self) -> Favourites:
        """Favourites list and add/remove helpers for this customer."""
        from ...favourites import Favourites

        if self._favourites is None:
            self._favourites = Favourites(self._require_api())
        return self._favourites

    @property
    def basket(self) -> BasketAccess:
        """Basket fetch and clear helpers for this customer."""
        from ...basket import BasketAccess

        if self._basket_access is None:
            self._basket_access = BasketAccess(self._require_api())
        return self._basket_access

    @property
    def orders(self) -> Orders:
        """Order history, latest order, and per-order status."""
        from ...orders import Orders

        if self._orders is None:
            self._orders = Orders(self._require_api())
        return self._orders

    @property
    def nectar(self) -> Nectar:
        """Nectar bonus offers and Your Nectar Price helpers."""
        from ...nectar import Nectar

        if self._nectar is None:
            self._nectar = Nectar(self._require_api())
        return self._nectar

    @property
    def slots(self) -> Slots:
        """Delivery and collection slot listing helpers."""
        from ...slots import Slots

        if self._slots is None:
            self._slots = Slots(self._require_api())
        return self._slots

    @property
    def display_name(self) -> str:
        """Return a human-friendly display name."""
        parts = [part for part in (self.given_name, self.family_name) if part]
        if parts:
            return " ".join(parts)
        return self.email or self.user_id

    def to_dict(self) -> dict[str, Any]:
        """Serialise the customer profile to a plain dictionary."""
        return {
            "user_id": self.user_id,
            "customer_id": self.customer_id,
            "identity_id": self.identity_id,
            "email": self.email,
            "family_name": self.family_name,
            "given_name": self.given_name,
            "primary_phone": self.primary_phone,
            "postcode": self.postcode,
            "title": self.title,
            "is_very_important_customer": self.is_very_important_customer,
            "delivery_pass_expiry_date": self.delivery_pass_expiry_date,
            "personalization_id": self.personalization_id,
            "has_nectar_associated": self.has_nectar_associated,
            "has_nectar_linked": self.has_nectar_linked,
            "is_digital_nectar": self.is_digital_nectar,
            "display_name": self.display_name,
        }

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        """Allow ``dict(customer)`` conversion."""
        return iter(self.to_dict().items())
