"""DocCheck Gemini Service Module

Integrates with the official Google GenAI Python SDK (google-genai).
Provides structured JSON generation, authentication verification, model switching,
automatic retry with exponential backoff for transient 503 / 429 load spikes,
fallback model recovery, and error handling.
"""

import json
import os
import re
import time
from typing import Dict, Any, Optional, List

from google import genai
from google.genai import types
from google.genai.errors import APIError

import config


class GeminiServiceError(Exception):
    """Base exception for Gemini service operations."""
    pass


class GeminiAuthError(GeminiServiceError):
    """Raised when the Gemini API key is missing or invalid."""
    pass


class GeminiQuotaError(GeminiServiceError):
    """Raised when Gemini API rate limits or quota are exhausted."""
    pass


class GeminiModelError(GeminiServiceError):
    """Raised when the requested Gemini model is unsupported or unavailable."""
    pass


class GeminiUnavailableError(GeminiServiceError):
    """Raised when Gemini returns 503 UNAVAILABLE due to temporary server load spike."""
    pass


class GeminiResponseError(GeminiServiceError):
    """Raised when Gemini returns an empty or unparseable JSON response."""
    pass


def get_effective_api_key(api_key: Optional[str] = None) -> str:
    """Returns the effective API key from argument, environment, or config."""
    key = (api_key or os.getenv("GEMINI_API_KEY", "") or config.GEMINI_API_KEY).strip()
    if not key or key == "your_gemini_api_key_here":
        raise GeminiAuthError(
            "Gemini API Key is not configured. Please provide a valid Gemini API key "
            "in your .env file or enter it in the Streamlit application sidebar."
        )
    return key


def get_effective_model(model_name: Optional[str] = None) -> str:
    """Returns the effective Gemini model name."""
    return (model_name or os.getenv("GEMINI_MODEL", "") or config.DEFAULT_MODEL).strip()


def get_gemini_client(api_key: Optional[str] = None) -> genai.Client:
    """Instantiates a Google GenAI client with validated credentials."""
    effective_key = get_effective_api_key(api_key)
    try:
        return genai.Client(api_key=effective_key)
    except Exception as e:
        raise GeminiAuthError(f"Failed to initialize Gemini Client: {str(e)}")


def clean_json_response(raw_text: str) -> Dict[str, Any]:
    """Cleans markdown formatting and parses JSON safely.

    Handles fenced code blocks (```json ... ```) and whitespace.
    """
    if not raw_text or not raw_text.strip():
        raise GeminiResponseError("Gemini returned an empty response.")

    text = raw_text.strip()

    # Strip markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    # Attempt standard JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: attempt to find the first '{' and last '}'
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError as e:
                raise GeminiResponseError(f"Failed to parse model JSON output: {str(e)}\nRaw output: {text[:300]}")
        raise GeminiResponseError(f"Invalid JSON returned by Gemini: {text[:300]}")


def _execute_with_retry_and_fallback(
    client: genai.Client,
    models_to_try: List[str],
    prompt: str,
    temperature: float,
    max_retries: int = 2,
    retry_delay_seconds: float = 1.5,
) -> tuple[types.GenerateContentResponse, str]:
    """Executes generate_content with retry on transient 503/429 errors and fallback models.

    Returns:
        Tuple of (response, model_that_succeeded).
    """
    last_error: Optional[Exception] = None

    for model in models_to_try:
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        response_mime_type="application/json",
                    ),
                )
                return response, model
            except APIError as e:
                error_msg = str(e).lower()
                last_error = e

                # Hard authentication errors - do not retry
                if "api_key" in error_msg or "unauthenticated" in error_msg or "permission_denied" in error_msg or "403" in error_msg:
                    raise GeminiAuthError(f"Authentication failed: {str(e)}. Please check your GEMINI_API_KEY.")

                # Model not found (404) - try next model immediately
                if "not_found" in error_msg or "404" in error_msg:
                    break

                # Transient 503 Unavailable / 429 Rate Limit - retry with backoff
                if "503" in error_msg or "unavailable" in error_msg or "high demand" in error_msg or "429" in error_msg or "resource_exhausted" in error_msg:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay_seconds * (attempt + 1))
                        continue
                    else:
                        # Move to fallback model
                        break

                # Other API errors
                break

            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                if "api key" in err_str or "unauthorized" in err_str:
                    raise GeminiAuthError(f"Gemini authentication error: {str(e)}")
                break

    # If all models and retries were exhausted
    if last_error:
        err_str = str(last_error).lower()
        if "503" in err_str or "unavailable" in err_str or "high demand" in err_str:
            raise GeminiUnavailableError(
                f"Google Gemini is currently experiencing a temporary server demand spike (HTTP 503) "
                f"across requested models ({', '.join(models_to_try)}). "
                "Please retry in a few moments, or select an alternative model (e.g., 'gemini-2.0-flash') in the sidebar."
            )
        elif "resource_exhausted" in err_str or "429" in err_str or "quota" in err_str:
            raise GeminiQuotaError(f"Gemini API rate limit exceeded: {str(last_error)}. Please wait a moment and retry.")
        elif "not_found" in err_str or "404" in err_str:
            raise GeminiModelError(f"Model not found or unsupported: {str(last_error)}.")
        else:
            raise GeminiServiceError(f"Gemini API error: {str(last_error)}")

    raise GeminiServiceError("Failed to obtain a response from Gemini.")


def generate_structured_json(
    prompt: str,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: float = 0.1,
) -> Dict[str, Any]:
    """Generates structured JSON using Gemini with the official google-genai SDK.

    Includes automatic exponential backoff on 503/429 spikes and fallback model recovery.
    """
    client = get_gemini_client(api_key)
    effective_model = get_effective_model(model_name)

    # Build fallback cascade
    models_to_try = [effective_model]
    for fallback in ["gemini-3.8-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.0-flash-lite"]:
        if fallback not in models_to_try:
            models_to_try.append(fallback)

    response, _ = _execute_with_retry_and_fallback(
        client=client,
        models_to_try=models_to_try,
        prompt=prompt,
        temperature=temperature,
    )

    if not response or not hasattr(response, "text") or not response.text:
        raise GeminiResponseError("Gemini returned an empty response without text.")

    return clean_json_response(response.text)


def test_gemini_connection(api_key: Optional[str] = None, model_name: Optional[str] = None) -> Dict[str, Any]:
    """Tests the connection to Gemini with retry and fallback awareness.

    Returns:
        Dict with status, model, and diagnostic feedback.
    """
    effective_model = get_effective_model(model_name)
    try:
        client = get_gemini_client(api_key)
        
        # Test the chosen model with retries
        models_to_try = [effective_model]
        # Also include other popular models if the chosen one is experiencing a 503 spike
        for m in ["gemini-2.0-flash", "gemini-3.8-flash", "gemini-1.5-flash"]:
            if m not in models_to_try:
                models_to_try.append(m)

        response, succeeded_model = _execute_with_retry_and_fallback(
            client=client,
            models_to_try=models_to_try,
            prompt="Respond with JSON: {\"status\": \"ok\", \"ping\": \"pong\"}",
            temperature=0.0,
            max_retries=2,
            retry_delay_seconds=1.0,
        )
        data = clean_json_response(response.text)
        
        msg = f"Connected successfully to Google Gemini ({succeeded_model})!"
        if succeeded_model != effective_model:
            msg += f" Note: '{effective_model}' experienced a 503 spike; successfully connected via fallback '{succeeded_model}'."

        return {
            "success": True,
            "model": succeeded_model,
            "message": msg,
            "details": data,
        }
    except GeminiUnavailableError as e:
        return {
            "success": False,
            "model": effective_model,
            "message": (
                f"HTTP 503 High Demand: {str(e)}.\n"
                "💡 Quick Tip: Switch 'Gemini Flash Model' to 'gemini-2.0-flash' in the dropdown above and test again."
            ),
        }
    except Exception as e:
        err_msg = str(e)
        if "503" in err_msg or "unavailable" in err_msg.lower():
            err_msg = (
                f"Google Gemini is currently under heavy traffic (HTTP 503 UNAVAILABLE). "
                f"Spikes are usually temporary (1-2 minutes). "
                f"💡 Try switching to 'gemini-2.0-flash' in the dropdown above."
            )
        return {
            "success": False,
            "model": effective_model,
            "message": err_msg,
        }
