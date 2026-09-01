"""Monetary amount models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Price:
    """
    A monetary amount with an optional unit of measure.

    Attributes:
        price: Amount in pounds sterling.
        measure: Unit label returned by the API (for example ``ea`` or ``kg``).
        measure_amount: Quantity associated with ``measure`` when provided.

    """

    price: float
    measure: str | None = None
    measure_amount: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Price | None:
        """Parse a price object from grocery API JSON."""
        if not data:
            return None
        return cls(
            price=float(data.get("price", 0)),
            measure=data.get("measure"),
            measure_amount=(
                float(data["measure_amount"])
                if data.get("measure_amount") is not None
                else None
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the price to a plain dictionary."""
        return {
            "price": self.price,
            "measure": self.measure,
            "measure_amount": self.measure_amount,
        }
