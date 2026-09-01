"""Tests for HTTP exception parsing."""

import json

from pysainsburys.exceptions import (
    HttpException,
    UnknownEndpointError,
    format_http_error_message,
    parse_error_response,
)


def test_parse_error_response_parses_json_object() -> None:
    """JSON error bodies are parsed into structured data."""
    parsed = parse_error_response(
        '{"errors":[{"code":"INVALID_POSTCODE","title":"Invalid postcode",'
        '"detail":"Invalid postcode given in request."}]}'
    )
    assert isinstance(parsed, dict)
    assert parsed["errors"][0]["code"] == "INVALID_POSTCODE"


def test_parse_error_response_returns_plain_text() -> None:
    """Non-JSON error bodies are returned unchanged."""
    assert parse_error_response("Bad gateway") == "Bad gateway"


def test_format_http_error_message_from_gol_errors() -> None:
    """GOL error arrays produce concise messages."""
    message = format_http_error_message(
        400,
        "",
        parsed={
            "errors": [
                {
                    "code": "INVALID_POSTCODE",
                    "title": "Invalid postcode",
                    "detail": "Invalid postcode given in request.",
                }
            ]
        },
    )
    assert message == "HTTP 400: INVALID_POSTCODE: Invalid postcode given in request."


def test_http_exception_exposes_parsed_json() -> None:
    """HttpException stores parsed JSON separately from the raw body."""
    body = json.dumps(
        {
            "errors": [
                {
                    "code": "INVALID_POSTCODE",
                    "detail": "Invalid postcode given in request.",
                }
            ]
        }
    )
    exc = HttpException(400, body)

    assert exc.response_json == json.loads(body)
    assert exc.errors[0]["code"] == "INVALID_POSTCODE"
    assert str(exc) == "HTTP 400: INVALID_POSTCODE: Invalid postcode given in request."


def test_unknown_endpoint_error_is_http_exception() -> None:
    """UnknownEndpointError inherits structured HTTP error parsing."""
    exc = UnknownEndpointError(502, "upstream failed")
    assert exc.status == 502
    assert exc.response == "upstream failed"
    assert exc.response_json == "upstream failed"
    assert exc.errors == []
    assert str(exc) == "HTTP 502: upstream failed"
