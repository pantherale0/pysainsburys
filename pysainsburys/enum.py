"""Enumerations for Sainsbury's GOL API."""

from enum import Enum


class AuthChannel(str, Enum):
    """OAuth client channel for grocery authentication."""

    WEB = "web"
    ANDROID = "android"
