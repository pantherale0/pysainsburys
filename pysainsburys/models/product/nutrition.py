"""
Nutrition models and parsers for product detail pages.

Sainsbury's embeds nutrition tables inside the base64-encoded ``details_html``
field on product detail responses. The helpers in this module decode that HTML
and expose structured :class:`NutritionInfo` objects.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

_LOZENGE_ITEM_RE = re.compile(
    r'<li class="lozenge[^"]*">(.*?)</li>',
    re.DOTALL | re.IGNORECASE,
)
_LOZENGE_TITLE_RE = re.compile(
    r'<h3 class="lozengeTitle">([^<]+)</h3>',
    re.IGNORECASE,
)
_LOZENGE_VALUE_RE = re.compile(
    r'<div class="lozengeHeaderSection">.*?'
    r'<h3 class="lozengeTitle">[^<]+</h3>(.*?)</div>',
    re.DOTALL | re.IGNORECASE,
)
_LOZENGE_PERCENT_RE = re.compile(
    r'<div class="percentage">\s*<p>([^<]*)</p>',
    re.IGNORECASE,
)
_LOZENGE_ACCESS_RE = re.compile(
    r'<p class="access">([^<]*)</p>',
    re.IGNORECASE,
)
_LOZENGE_FOOTER_RE = re.compile(
    r'<div class="lozengeFooter">(.*?)</div>',
    re.DOTALL | re.IGNORECASE,
)
_TABLE_TITLE_RE = re.compile(
    r"<strong>([^<]+)</strong>\s*</p>\s*"
    r'(?:<div[^>]*>\s*)?<table class="nutritionTable">',
    re.IGNORECASE,
)
_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(slots=True)
class NutrientSummary:
    """Traffic-light style nutrition summary for a single nutrient."""

    name: str
    values: list[str]
    reference_intake_percent: str | None = None
    level: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the nutrient summary as a dictionary."""
        return {
            "name": self.name,
            "values": self.values,
            "reference_intake_percent": self.reference_intake_percent,
            "level": self.level,
        }


@dataclass(slots=True)
class NutritionTableRow:
    """A single row in a nutrition facts table."""

    name: str
    values: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Return the table row as a dictionary."""
        return {
            "name": self.name,
            "values": self.values,
        }


@dataclass(slots=True)
class NutritionTable:
    """A nutrition facts table from a product detail page."""

    columns: list[str]
    rows: list[NutritionTableRow]
    title: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the nutrition table as a dictionary."""
        return {
            "title": self.title,
            "columns": self.columns,
            "rows": [row.to_dict() for row in self.rows],
        }


@dataclass(slots=True)
class NutritionInfo:
    """Parsed nutrition information for a product."""

    summary: list[NutrientSummary] = field(default_factory=list)
    tables: list[NutritionTable] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return nutrition information as a dictionary."""
        return {
            "summary": [item.to_dict() for item in self.summary],
            "tables": [table.to_dict() for table in self.tables],
            "notes": self.notes,
        }


class _NutritionTableParser(HTMLParser):
    """Extract columns and rows from Sainsbury's nutrition tables."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.columns: list[str] = []
        self.rows: list[NutritionTableRow] = []
        self._in_thead = False
        self._in_tbody = False
        self._in_row = False
        self._current_row_name: str | None = None
        self._current_row_values: list[str] = []
        self._last_row_name: str | None = None
        self._cell_text: list[str] = []
        self._capture_cell = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "thead":
            self._in_thead = True
        elif tag == "tbody":
            self._in_tbody = True
        elif tag == "tr" and (self._in_thead or self._in_tbody):
            self._in_row = True
            self._current_row_name = None
            self._current_row_values = []
        elif tag in {"th", "td"} and self._in_row:
            self._capture_cell = True
            self._cell_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "thead":
            self._in_thead = False
        elif tag == "tbody":
            self._in_tbody = False
        elif tag in {"th", "td"} and self._capture_cell:
            text = " ".join(self._cell_text).strip()
            if self._in_thead:
                if text:
                    self.columns.append(text)
            elif self._in_tbody:
                if tag == "th" and text:
                    self._current_row_name = text
                elif text:
                    self._current_row_values.append(text)
            self._capture_cell = False
            self._cell_text = []
        elif tag == "tr" and self._in_tbody and self._in_row:
            row_name = self._current_row_name
            if row_name is None and self._current_row_values:
                row_name = self._last_row_name
            if row_name is not None:
                self.rows.append(
                    NutritionTableRow(
                        name=row_name,
                        values=self._current_row_values,
                    )
                )
                self._last_row_name = row_name
            self._in_row = False
            self._current_row_name = None
            self._current_row_values = []

    def handle_data(self, data: str) -> None:
        if self._capture_cell:
            stripped = data.strip()
            if stripped:
                self._cell_text.append(stripped)


def decode_details_html(details_html: str | None) -> str | None:
    """Decode the base64 product ``details_html`` field."""
    if not details_html:
        return None
    try:
        return base64.b64decode(details_html).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def _parse_lozenge_values(fragment: str) -> list[str]:
    match = _LOZENGE_VALUE_RE.search(fragment)
    if not match:
        return []
    values: list[str] = []
    for part in _TAG_RE.sub("\n", match.group(1)).split("\n"):
        text = part.strip()
        if text:
            values.append(text)
    return values


def _parse_summary(html: str) -> tuple[list[NutrientSummary], list[str]]:
    summary: list[NutrientSummary] = []
    notes: list[str] = []
    block_match = re.search(
        r'<ul class="lozengeBlock">(.*?)</ul>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if not block_match:
        return summary, notes

    block = block_match.group(1)
    for item_html in _LOZENGE_ITEM_RE.findall(block):
        title_match = _LOZENGE_TITLE_RE.search(item_html)
        if not title_match:
            continue
        percent_match = _LOZENGE_PERCENT_RE.search(item_html)
        access_match = _LOZENGE_ACCESS_RE.search(item_html)
        percent = percent_match.group(1).strip() if percent_match else None
        level = access_match.group(1).strip() if access_match else None
        if level and level.lower() == title_match.group(1).strip().lower():
            level = None
        summary.append(
            NutrientSummary(
                name=title_match.group(1).strip(),
                values=_parse_lozenge_values(item_html),
                reference_intake_percent=percent or None,
                level=level or None,
            )
        )

    footer_match = _LOZENGE_FOOTER_RE.search(html)
    if footer_match:
        for part in _TAG_RE.sub("\n", footer_match.group(1)).split("\n"):
            text = part.strip()
            if text:
                notes.append(text)
    return summary, notes


def _parse_table(html: str, table_html: str) -> NutritionTable:
    title: str | None = None
    table_start = html.find(table_html)
    if table_start >= 0:
        prefix = html[max(0, table_start - 250) : table_start]
        title_match = _TABLE_TITLE_RE.search(prefix + table_html[:120])
        if title_match:
            title = title_match.group(1).strip()

    parser = _NutritionTableParser()
    parser.feed(table_html)
    return NutritionTable(
        title=title,
        columns=parser.columns,
        rows=parser.rows,
    )


def parse_nutrition(html: str | None) -> NutritionInfo | None:
    """Parse nutrition information from decoded product detail HTML."""
    if not html or (
        "nutritionTable" not in html and "nutritionalContentSummary" not in html
    ):
        return None

    summary, notes = _parse_summary(html)
    tables: list[NutritionTable] = []
    for table_html in re.findall(
        r'<table class="nutritionTable">.*?</table>',
        html,
        re.DOTALL | re.IGNORECASE,
    ):
        tables.append(_parse_table(html, table_html))

    if not summary and not tables and not notes:
        return None
    return NutritionInfo(summary=summary, tables=tables, notes=notes)


def parse_nutrition_from_details_html(details_html: str | None) -> NutritionInfo | None:
    """Parse nutrition information from a product ``details_html`` field."""
    return parse_nutrition(decode_details_html(details_html))
