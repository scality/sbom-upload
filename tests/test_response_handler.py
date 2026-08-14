"""Unit tests for src/services/response_handler.py"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
import requests

from services.response_handler import APIResponseHandler
from domain.exceptions import APIConnectionError


def _response(status_code, body=""):
    """Build a Response with a real status code and body."""
    response = requests.Response()
    response.status_code = status_code
    response._content = body.encode()
    return response


@pytest.mark.parametrize("status", [400, 401, 403, 404, 409, 500, 502, 503])
def test_error_status_is_reported_with_its_status_code(status):
    """A 4xx/5xx must surface the status code, not a phantom connection error.

    requests.Response.__bool__ returns self.ok, so a truthiness test treats
    every error response as a missing one. That reported HTTP failures as
    "No response received from server ... timeout or connection issue" and
    discarded the status code and body entirely.
    """
    with pytest.raises(APIConnectionError) as excinfo:
        APIResponseHandler.handle_response(
            _response(status, '{"detail":"boom"}'),
            success_status=200,
            operation="Project update",
        )

    message = str(excinfo.value)
    assert f"status: {status}" in message
    assert "boom" in message
    assert "No response received" not in message


def test_missing_response_still_reports_a_connection_error():
    """None genuinely means no response, and must keep the old message."""
    with pytest.raises(APIConnectionError) as excinfo:
        APIResponseHandler.handle_response(
            None, success_status=200, operation="Project update"
        )

    assert "No response received from server" in str(excinfo.value)


def test_success_returns_parsed_body():
    result = APIResponseHandler.handle_response(
        _response(200, '{"uuid":"abc"}'), success_status=200, operation="Lookup"
    )
    assert result == {"uuid": "abc"}


def test_success_with_empty_body_returns_none():
    assert (
        APIResponseHandler.handle_response(
            _response(200), success_status=200, operation="Lookup"
        )
        is None
    )


def test_created_status_is_honoured():
    result = APIResponseHandler.handle_response(
        _response(201, '{"uuid":"abc"}'),
        success_status=201,
        operation="Project creation",
    )
    assert result == {"uuid": "abc"}
