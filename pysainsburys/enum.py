"""Enumerations for Sainsbury's GOL API."""

from enum import Enum


class SlotType(str, Enum):
    """Delivery or click-and-collect slot listing type."""

    DELIVERY = "delivery"
    COLLECTION = "collection"
