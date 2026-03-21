"""
Flask API routes for the StockSense Copilot Agent.

Endpoints:
    POST /api/copilot/analyze          – run full async analysis for a ticker
    GET  /api/copilot/analyze/<ticker> – convenience GET wrapper
    GET  /api/copilot/health           – status / configuration check
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from flask import Blueprint, jsonify, request
from flask_login import login_required

logger = logging.getLogger(__name__)

copilot_bp = Blueprint("copilot", __name__, url_prefix="/api/copilot")


def _run_async(coro) -> Any:
    """
    Execute an async coroutine from a synchronous Flask request handler.

    Flask's WSGI server is synchronous, so we create (or reuse) an event
    loop via ``asyncio.run()`` which is the idiomatic way to bridge sync and
    async code in Python 3.10+.
    """
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# POST /api/copilot/analyze
# ---------------------------------------------------------------------------

@copilot_bp.route("/analyze", methods=["POST"])
@login_required
def analyze_post():
    """
    Run the full agentic Copilot analysis for a stock ticker.

    Request body (JSON)::

        {
          "ticker": "TCS.BO",
          "include_chart": true       // optional, default true
        }

    Response (JSON)::

        {
          "success": true,
          "ticker": "TCS.BO",
          "markdown_report": "## StockSense-AI ...",
          "chart_b64": "<base64 PNG or null>",
          "confidence_score": 72,
          "sentiment_label": "Bullish",
          "processing_time_s": 4.21,
          "model": "gpt-4o",
          "copilot_available": false,
          "tool_call_log": [...]
        }
    """
    body = request.get_json(silent=True) or {}
    ticker = (body.get("ticker") or "").strip().upper()
    include_chart = body.get("include_chart", True)

    if not ticker:
        return jsonify({"success": False, "error": "Missing required field: ticker"}), 400

    return _execute_analysis(ticker, include_chart)


# ---------------------------------------------------------------------------
# GET /api/copilot/analyze/<ticker>
# ---------------------------------------------------------------------------

@copilot_bp.route("/analyze/<ticker>", methods=["GET"])
@login_required
def analyze_get(ticker: str):
    """
    Convenience GET endpoint – runs the same analysis as the POST endpoint.

    Query params:
        include_chart: 'true' | 'false' (default 'true')
    """
    ticker = ticker.strip().upper()
    include_chart = request.args.get("include_chart", "true").lower() != "false"
    return _execute_analysis(ticker, include_chart)


# ---------------------------------------------------------------------------
# GET /api/copilot/health
# ---------------------------------------------------------------------------

@copilot_bp.route("/health", methods=["GET"])
@login_required
def health():
    """
    Return the status of the Copilot agent configuration.

    Response::

        {
          "success": true,
          "copilot_api_available": false,
          "github_token_set": false,
          "alpha_vantage_configured": true,
          "openai_package_installed": true,
          "model": "gpt-4o",
          "tools": ["fetch_market_data", "run_nlp_sentiment", "generate_forecast_chart"]
        }
    """
    try:
        import os

        try:
            import openai as _openai  # noqa: F401
            openai_available = True
        except ImportError:
            openai_available = False

        from app.agents.copilot_agent import CopilotClient, _TOOL_HANDLERS
        from app.config.alpha_vantage_config import AlphaVantageConfig

        client = CopilotClient()

        return jsonify({
            "success": True,
            "copilot_api_available": client.is_available(),
            "github_token_set": bool(os.getenv("GITHUB_TOKEN")),
            "alpha_vantage_configured": AlphaVantageConfig.is_configured(),
            "openai_package_installed": openai_available,
            "model": os.getenv("COPILOT_MODEL", "gpt-4o"),
            "tools": list(_TOOL_HANDLERS.keys()),
            "endpoints": {
                "analyze_post": "POST /api/copilot/analyze",
                "analyze_get": "GET  /api/copilot/analyze/<ticker>",
                "health": "GET  /api/copilot/health",
            },
        })

    except Exception as exc:
        logger.error("Copilot health check failed: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _execute_analysis(ticker: str, include_chart: bool) -> Any:
    """Shared logic for both POST and GET analysis endpoints."""
    try:
        from app.agents.copilot_agent import StockSenseCopilotAgent

        agent = StockSenseCopilotAgent()
        result: Dict[str, Any] = _run_async(agent.analyze(ticker))

        # Strip chart if the caller didn't ask for it (saves bandwidth)
        if not include_chart:
            result["chart_b64"] = None

        # Extract confidence from the market data for the top-level response
        market = result.get("market_data", {})
        sentiment = result.get("sentiment", {})
        sent_score = float(sentiment.get("sentiment_score", 0) or 0)
        tech = market.get("technical_indicators", {})
        rsi = float(tech.get("rsi_14", 50) or 50)

        tech_score = min(40, int((1 if 40 < rsi < 70 else 0.5) * 40))
        sent_weight = min(25, int(abs(sent_score) * 100))
        freshness = 20 if market.get("source") not in ("unknown", None, "") else 5
        vol_pct = float(tech.get("volatility_30d", 0) or 0)
        vol_discount = max(0, 15 - int(vol_pct))
        confidence = tech_score + sent_weight + freshness + vol_discount

        return jsonify({
            "success": True,
            "ticker": ticker,
            "markdown_report": result.get("markdown_report", ""),
            "chart_b64": result.get("chart_b64"),
            "confidence_score": confidence,
            "sentiment_label": sentiment.get("sentiment_label", "Neutral"),
            "processing_time_s": result.get("processing_time_s", 0),
            "model": result.get("model", "unknown"),
            "copilot_available": result.get("copilot_available", False),
            "tool_call_log": result.get("tool_call_log", []),
        })

    except Exception as exc:
        logger.exception("Copilot analysis failed for %s: %s", ticker, exc)
        return jsonify({
            "success": False,
            "ticker": ticker,
            "error": str(exc),
        }), 500
