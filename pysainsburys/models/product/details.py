"""
Product-text sections parsed from ``details_html``.

Sainsbury's product detail responses embed description, storage, and related
copy in the same base64 HTML blob as nutrition tables. Nutrition stays on
:class:`~pysainsburys.models.product.nutrition.NutritionInfo`; this module
keeps the other ``h3.partHead`` sections.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

from .nutrition import decode_details_html

_BODY_CLASSES = frozenset(
    {
        "memo",
        "nameLookups",
        "longTextItems",
        "nameTextItems",
        "nameTextLookups",
        "statements",
    }
)
_VOID_TAGS = frozenset({"br", "img", "hr", "meta", "link"})
_HEADING_FIELDS = {
    "description": "description",
    "storage": "storage",
    "dietary information": "dietary_information",
    "ingredients": "ingredients",
    "manufacturer": "manufacturer",
    "preparation": "preparation",
    "country of origin": "country_of_origin",
    "packaging": "packaging",
}
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(slots=True)
class ProductDetails:
    """
    Catalogue copy parsed from a product detail page.

    Each field is a list of paragraphs. A heading the page does not include
    is ``None``.

    Attributes:
        description: Product description paragraphs.
        storage: Storage instructions.
        dietary_information: Dietary and allergen statements.
        ingredients: Ingredient list paragraphs.
        manufacturer: Manufacturer or packer details.
        preparation: Preparation or serving instructions.
        country_of_origin: Origin or packing-country statements.
        packaging: Packaging description.

    """

    description: list[str] | None = None
    storage: list[str] | None = None
    dietary_information: list[str] | None = None
    ingredients: list[str] | None = None
    manufacturer: list[str] | None = None
    preparation: list[str] | None = None
    country_of_origin: list[str] | None = None
    packaging: list[str] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ProductDetails | None:
        """Parse product detail sections from a serialised mapping."""
        if not data:
            return None
        details = cls(
            description=_string_list(data.get("description")),
            storage=_string_list(data.get("storage")),
            dietary_information=_string_list(data.get("dietary_information")),
            ingredients=_string_list(data.get("ingredients")),
            manufacturer=_string_list(data.get("manufacturer")),
            preparation=_string_list(data.get("preparation")),
            country_of_origin=_string_list(data.get("country_of_origin")),
            packaging=_string_list(data.get("packaging")),
        )
        if details.is_empty():
            return None
        return details

    def is_empty(self) -> bool:
        """Return whether every section is missing."""
        return all(
            value is None
            for value in (
                self.description,
                self.storage,
                self.dietary_information,
                self.ingredients,
                self.manufacturer,
                self.preparation,
                self.country_of_origin,
                self.packaging,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the detail sections to a plain dictionary."""
        return {
            "description": self.description,
            "storage": self.storage,
            "dietary_information": self.dietary_information,
            "ingredients": self.ingredients,
            "manufacturer": self.manufacturer,
            "preparation": self.preparation,
            "country_of_origin": self.country_of_origin,
            "packaging": self.packaging,
        }


class _ProductTextParser(HTMLParser):
    """Collect known product-text sections from decoded detail HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sections: dict[str, list[str]] = {}
        self._in_heading = False
        self._heading: list[str] = []
        self._title: str | None = None
        self._stack: list[tuple[str, bool]] = []
        self._body_depth = 0
        self._paragraph: list[str] = []
        self._paragraphs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = set(_attr(attrs, "class").split())
        if tag == "h3" and "partHead" in classes:
            self._finish_section()
            self._in_heading = True
            self._heading = []
            return
        if self._in_heading:
            return
        is_body = bool(classes & _BODY_CLASSES)
        if tag not in _VOID_TAGS and (self._body_depth or is_body):
            self._stack.append((tag, is_body))
            if is_body:
                self._body_depth += 1
        if tag == "br" and self._body_depth:
            self._end_paragraph()

    def handle_endtag(self, tag: str) -> None:
        if self._in_heading and tag == "h3":
            self._title = _normalise(" ".join(self._heading))
            self._in_heading = False
            return
        if not self._stack or self._stack[-1][0] != tag:
            return
        _, is_body = self._stack.pop()
        if tag == "p" and self._body_depth:
            self._end_paragraph()
        if is_body:
            self._body_depth -= 1
            self._end_paragraph()

    def handle_data(self, data: str) -> None:
        if self._in_heading:
            self._heading.append(data)
            return
        if self._body_depth and data.strip():
            self._paragraph.append(data)

    def close(self) -> None:
        self._finish_section()
        super().close()

    def _end_paragraph(self) -> None:
        text = _normalise(" ".join(self._paragraph))
        self._paragraph = []
        if text:
            self._paragraphs.append(text)

    def _finish_section(self) -> None:
        self._end_paragraph()
        title = self._title
        paragraphs = self._paragraphs
        self._title = None
        self._paragraphs = []
        self._paragraph = []
        self._stack.clear()
        self._body_depth = 0
        self._in_heading = False
        if not title or not paragraphs:
            return
        field_name = _HEADING_FIELDS.get(title.casefold())
        if field_name is None:
            return
        existing = self.sections.get(field_name)
        if existing is None:
            self.sections[field_name] = paragraphs
        else:
            existing.extend(paragraphs)


def parse_product_details(html: str | None) -> ProductDetails | None:
    """Parse product-text sections from decoded product detail HTML."""
    if not html or "partHead" not in html:
        return None
    parser = _ProductTextParser()
    parser.feed(html)
    parser.close()
    if not parser.sections:
        return None
    return ProductDetails(**parser.sections)


def parse_product_details_from_details_html(
    details_html: str | None,
) -> ProductDetails | None:
    """Parse product-text sections from a base64 ``details_html`` field."""
    return parse_product_details(decode_details_html(details_html))


def product_details_from_api(
    details_html: str | None,
    description: Any,
) -> ProductDetails | None:
    """
    Build product details from a grocery API product payload.

    When the HTML has no Description section, ``description`` falls back to
    the JSON ``description`` list on the same payload.
    """
    details = parse_product_details_from_details_html(details_html)
    description_lines = _string_list(description)
    if not description_lines:
        return details
    if details is None:
        return ProductDetails(description=description_lines)
    if details.description is None:
        details.description = description_lines
    return details


def _string_list(value: Any) -> list[str] | None:
    """Return a list of non-empty strings, or ``None``."""
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else None
    if not isinstance(value, list):
        return None
    lines = [str(item).strip() for item in value if str(item).strip()]
    return lines or None


def _attr(attrs: list[tuple[str, str | None]], name: str) -> str:
    for key, value in attrs:
        if key == name and value:
            return value
    return ""


def _normalise(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()
