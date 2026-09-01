"""Connection settings for Sainsbury's GOL API."""

from __future__ import annotations

from dataclasses import dataclass

from .const import GOL_APP_USER_AGENT, GOL_BASE_URL

COMM_PROTOCOL = "http"


@dataclass(slots=True)
class Config:
    """Where and how to connect to the grocery API."""

    base_url: str = GOL_BASE_URL
    app_version: str = GOL_APP_USER_AGENT.removeprefix("GOLAppAndroid/")
