"""Pagination metadata models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class PageControls:
    """
    Pagination metadata returned by grocery list endpoints.

    Attributes:
        total_record_count: Total items available across all pages.
        returned_record_count: Items included in the current response.
        active_page: One-based index of the current page.
        first_page: One-based index of the first page.
        last_page: One-based index of the last page.
        page_size: Requested page size.

    """

    total_record_count: int
    returned_record_count: int
    active_page: int
    first_page: int
    last_page: int
    page_size: int

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> PageControls:
        """Parse pagination controls from grocery API JSON."""
        data = data or {}
        page = data.get("page") or {}
        return cls(
            total_record_count=int(data.get("total_record_count", 0)),
            returned_record_count=int(data.get("returned_record_count", 0)),
            active_page=int(page.get("active", 1)),
            first_page=int(page.get("first", 1)),
            last_page=int(page.get("last", 1)),
            page_size=int(page.get("size", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise pagination controls to a plain dictionary."""
        return {
            "total_record_count": self.total_record_count,
            "returned_record_count": self.returned_record_count,
            "active_page": self.active_page,
            "first_page": self.first_page,
            "last_page": self.last_page,
            "page_size": self.page_size,
        }
