"""Unit tests for Gemini Service Module

Tests API key validation, JSON response cleaning, and mock API handling.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from modules.gemini_service import (
    clean_json_response,
    get_effective_api_key,
    generate_structured_json,
    GeminiAuthError,
    GeminiResponseError,
    GeminiQuotaError,
)
from google.genai.errors import APIError


def test_clean_json_response_plain():
    """Tests cleaning pure JSON string."""
    raw = '{"name": "DocCheck", "status": "active"}'
    parsed = clean_json_response(raw)
    assert parsed["name"] == "DocCheck"
    assert parsed["status"] == "active"


def test_clean_json_response_markdown_fences():
    """Tests cleaning JSON enclosed in markdown code fences."""
    raw = """```json
{
  "detected_type": "Invoice",
  "score": 95
}
```"""
    parsed = clean_json_response(raw)
    assert parsed["detected_type"] == "Invoice"
    assert parsed["score"] == 95


def test_clean_json_response_invalid():
    """Tests that unparseable text raises GeminiResponseError."""
    with pytest.raises(GeminiResponseError):
        clean_json_response("This is not JSON at all.")


def test_get_effective_api_key_missing(monkeypatch):
    """Tests that missing or placeholder API key raises GeminiAuthError."""
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setattr("config.GEMINI_API_KEY", "")
    with pytest.raises(GeminiAuthError):
        get_effective_api_key("")

    with pytest.raises(GeminiAuthError):
        get_effective_api_key("your_gemini_api_key_here")


def test_get_effective_api_key_valid():
    """Tests that a valid API key is returned as expected."""
    key = "AIzaSyFakeKeyForTesting123"
    assert get_effective_api_key(key) == key


@patch("modules.gemini_service.get_gemini_client")
def test_generate_structured_json_success(mock_get_client):
    """Tests successful structured JSON generation with mocked Gemini client."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "detected_document_type": "Invoice",
        "document_summary": "Apex Cloud invoice",
    })
    mock_client.models.generate_content.return_value = mock_response

    result = generate_structured_json(
        prompt="Test prompt",
        model_name="gemini-3.8-flash",
        api_key="fake-key",
    )

    assert result["detected_document_type"] == "Invoice"
    assert result["document_summary"] == "Apex Cloud invoice"
    mock_client.models.generate_content.assert_called_once()

