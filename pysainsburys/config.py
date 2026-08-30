"""Connection settings for Sainsburys API."""

from __future__ import annotations

from dataclasses import dataclass

COMM_PROTOCOL = "http"


@dataclass(slots=True)
class Config:
    """Where and how to connect.

    The defaults are placeholders. Update them for your device, bridge, or API
    before creating a `Client`.
    """
    base_url: str = "http://127.0.0.1:8080"
