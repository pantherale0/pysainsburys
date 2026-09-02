"""Enumerations for Sainsbury's GOL API."""

from enum import StrEnum


class SlotType(StrEnum):
    """Delivery or click-and-collect slot listing type."""

    DELIVERY = "delivery"
    COLLECTION = "collection"
