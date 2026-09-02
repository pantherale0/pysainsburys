"""Enumerations for Sainsbury's GOL API."""

from enum import StrEnum


class SlotType(StrEnum):
    """Delivery or click-and-collect slot listing type."""

    DELIVERY = "delivery"
    COLLECTION = "collection"

    @property
    def api_value(self) -> str:
        """Return the grocery API ``slot_type`` query value."""
        if self is SlotType.COLLECTION:
            return "CLICK_AND_COLLECT"
        return "DELIVERY"
