"""
Unified cloud LLM adapter for StockSense production mode.

Supports three providers, selected via LLM_PROVIDER env var:
  • anthropic  – Anthropic Claude (via REST API using requests)
  • openai     – OpenAI GPT  (via REST API using requests)
  • gemini     – Google Gemini (via google-genai SDK already in requirements)

All credentials are sourced from environment variables only.
"""
import json
import logging
import re
import time
from typing import Any, Dict

import requests

from app.config.cloud_llm_config import CloudLLMConfig

logger = logging.getLogger(__name__)


# ── Low-level provider calls ──────────────────────────────────────────────────

def _call_anthropic(prompt: str) -> str:
    """Call the Anthropic Messages API and return the assistant text."""
    headers = {
        "x-api-key": CloudLLMConfig.API_KEY,
        "anthropic-version": CloudLLMConfig.ANTHROPIC_API_VERSION,
        "content-type": "application/json",
    }
    payload = {
        "model": CloudLLMConfig.ANTHROPIC_MODEL,
        "max_tokens": CloudLLMConfig.MAX_TOKENS,
        "temperature": CloudLLMConfig.TEMPERATURE,
        "messages": [{"role": "user", "content": prompt}],
    }
    response = requests.post(
        CloudLLMConfig.ANTHROPIC_API_URL,
        headers=headers,
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    return data["content"][0]["text"]


def _call_openai(prompt: str) -> str:
    """Call the OpenAI Chat Completions API and return the assistant text."""
    headers = {
        "Authorization": f"Bearer {CloudLLMConfig.API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": CloudLLMConfig.OPENAI_MODEL,
        "max_tokens": CloudLLMConfig.MAX_TOKENS,
        "temperature": CloudLLMConfig.TEMPERATURE,
        "messages": [{"role": "user", "content": prompt}],
    }
    response = requests.post(
        CloudLLMConfig.OPENAI_API_URL,
        headers=headers,
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def _call_gemini(prompt: str) -> str:
    """Call the Google Gemini API via the google-genai SDK."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=CloudLLMConfig.API_KEY)
    response = client.models.generate_content(
        model=CloudLLMConfig.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=CloudLLMConfig.TEMPERATURE,
            max_output_tokens=CloudLLMConfig.MAX_TOKENS,
        ),
    )
    return response.text


# ── Public call interface ─────────────────────────────────────────────────────

def call_cloud_llm(prompt: str) -> str:
    """
    Call the configured cloud LLM provider with retry logic.

    Returns:
        The raw text response from the provider.

    Raises:
        ValueError: If no provider is configured or credentials are missing.
        Exception:  After all retries are exhausted.
    """
    CloudLLMConfig.validate_config()

    provider = CloudLLMConfig.PROVIDER
    last_error: Exception = RuntimeError("No attempts made")

    for attempt in range(CloudLLMConfig.MAX_RETRIES):
        try:
            if provider == "anthropic":
                return _call_anthropic(prompt)
            elif provider == "openai":
                return _call_openai(prompt)
            elif provider == "gemini":
                return _call_gemini(prompt)
            else:
                raise ValueError(f"Unknown LLM provider: {provider}")
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Cloud LLM call failed (attempt %d/%d, provider=%s): %s",
                attempt + 1,
                CloudLLMConfig.MAX_RETRIES,
                provider,
                exc,
            )
            if attempt < CloudLLMConfig.MAX_RETRIES - 1:
                time.sleep(CloudLLMConfig.RETRY_DELAY)

    raise last_error


# ── Prediction helpers ────────────────────────────────────────────────────────

def _parse_prediction_response(text: str) -> Dict[str, Any]:
    """Extract structured prediction data from an LLM text response."""
    # Prefer a JSON block
    json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            if "predicted_price" in data and "confidence" in data:
                return {
                    "predicted_price": float(data["predicted_price"]),
                    "confidence": float(data["confidence"]),
                    "decision": str(data.get("decision", "caution")),
                    "reasoning": str(data.get("reasoning", "")),
                    "market_sentiment": str(data.get("market_sentiment", "neutral")),
                    "technical_signals": str(data.get("technical_signals", "moderate")),
                    "risk_level": str(data.get("risk_level", "medium")),
                    "model": f"cloud:{CloudLLMConfig.PROVIDER}",
                }
        except (json.JSONDecodeError, ValueError):
            pass

    # Fallback: regex extraction
    price_match = re.search(r'predicted_price["\']?\s*:\s*([0-9.]+)', text, re.IGNORECASE)
    conf_match = re.search(r'confidence["\']?\s*:\s*([0-9.]+)', text, re.IGNORECASE)
    decision_match = re.search(r'decision["\']?\s*:\s*["\']?(\w+)', text, re.IGNORECASE)

    if price_match and conf_match:
        return {
            "predicted_price": float(price_match.group(1)),
            "confidence": float(conf_match.group(1)),
            "decision": decision_match.group(1) if decision_match else "caution",
            "reasoning": text[:200],
            "model": f"cloud:{CloudLLMConfig.PROVIDER}",
        }

    logger.warning("Could not parse structured prediction from cloud LLM response")
    return {
        "predicted_price": 0.0,
        "confidence": 0.0,
        "decision": "reject",
        "reasoning": "Unable to parse response",
        "model": f"cloud:{CloudLLMConfig.PROVIDER}",
    }


def predict_with_details(symbol: str) -> Dict[str, Any]:
    """
    Make a stock prediction using the configured cloud LLM.

    Args:
        symbol: Yahoo Finance ticker symbol (e.g. 'INFY.BO')

    Returns:
        Dict with predicted_price, confidence, decision, reasoning, model.
    """
    try:
        import yfinance as yf

        stock = yf.Ticker(symbol)
        hist = stock.history(period="3mo")
        if hist.empty:
            raise ValueError(f"No market data found for symbol {symbol}")

        current_price = float(hist["Close"].iloc[-1])
        price_change = float(
            (hist["Close"].iloc[-1] - hist["Close"].iloc[-2])
            / hist["Close"].iloc[-2]
            * 100
        )
        volatility = float(hist["Close"].pct_change().std() * 100)
        avg_volume = float(hist["Volume"].mean())

        prompt = (
            f"You are a professional stock analyst. "
            f"Analyze the following data for {symbol} and provide a prediction:\n\n"
            f"Current Price: {current_price:.2f}\n"
            f"Recent Price Change: {price_change:.2f}%\n"
            f"30-day Volatility: {volatility:.2f}%\n"
            f"Average Volume: {avg_volume:.0f}\n"
            f"Recent Prices (last 10 days): {hist['Close'].tail(10).tolist()}\n\n"
            "Respond with a JSON object containing:\n"
            "  predicted_price (number), confidence (0.0-1.0),\n"
            "  decision ('accept'|'caution'|'reject'), reasoning (string)\n\n"
            "JSON Response:"
        )

        response_text = call_cloud_llm(prompt)
        return _parse_prediction_response(response_text)

    except Exception as exc:
        logger.error("Cloud LLM prediction failed for %s: %s", symbol, exc)
        return {
            "predicted_price": 0.0,
            "confidence": 0.0,
            "decision": "reject",
            "reasoning": f"Prediction error: {exc}",
            "model": f"cloud:{CloudLLMConfig.PROVIDER}",
        }
