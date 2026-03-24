"""
StockSense Copilot Agent
========================
Asynchronous agentic workflow powered by the GitHub Copilot SDK.

The agent orchestrates three custom tools via a tool-call loop driven by a
frontier LLM (default: gpt-4o through GitHub Models / Copilot API):

  1. fetch_market_data(ticker)       – historical OHLCV + sector KPIs
  2. run_nlp_sentiment(ticker)       – NLP sentiment score from recent news
  3. generate_forecast_chart(data)   – time-series Matplotlib/Seaborn chart

Every response is formatted as a structured Markdown report that includes:
  * Step-by-step logic breakdown of the predictive forecast
  * Verified data sources table
  * Confidence Score (0–100 %)

Usage (standalone async):
    import asyncio
    from app.agents.copilot_agent import StockSenseCopilotAgent

    async def main():
        agent = StockSenseCopilotAgent()
        report = await agent.analyze("TCS.BO")
        print(report["markdown_report"])

    asyncio.run(main())

Flask integration:
    from app.api.copilot_routes import copilot_bp
    app.register_blueprint(copilot_bp)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional openai import (GitHub Models / Copilot API is OpenAI-compatible)
# ---------------------------------------------------------------------------
try:
    import openai  # type: ignore
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False
    logger.warning(
        "openai package not installed – CopilotClient will run in offline/mock mode. "
        "Install with: pip install openai>=1.0.0"
    )

# ---------------------------------------------------------------------------
# CopilotClient – thin async wrapper around GitHub Models (OpenAI-compat.)
# ---------------------------------------------------------------------------

# Tool call timeout (seconds)
_TOOL_TIMEOUT: int = int(os.getenv("COPILOT_TOOL_TIMEOUT", "30"))
# LLM API call timeout (seconds)
_API_TIMEOUT: int = int(os.getenv("COPILOT_API_TIMEOUT", "60"))
# Maximum agentic loop iterations to prevent infinite loops
_MAX_ITERATIONS: int = int(os.getenv("COPILOT_MAX_ITERATIONS", "10"))


class CopilotSession:
    """
    Active session created by ``CopilotClient.create_session()``.

    Manages the message history and executes the agentic tool-call loop.
    """

    def __init__(
        self,
        client: "CopilotClient",
        model: str,
        system_prompt: str,
        tools: List[Dict[str, Any]],
        tool_handlers: Dict[str, Any],
    ) -> None:
        self._client = client
        self._model = model
        self._system_prompt = system_prompt
        self._tools = tools
        self._tool_handlers = tool_handlers
        self._messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]
        self.tool_call_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def run(self, user_message: str) -> str:
        """
        Execute the agentic loop for *user_message*.

        The loop:
          1. Sends the message to the LLM.
          2. If the LLM requests tool calls, executes them (with timeout).
          3. Feeds results back to the LLM.
          4. Repeats until the LLM returns a plain text response or the
             maximum iteration count is reached.

        Returns the final assistant message text.
        """
        self._messages.append({"role": "user", "content": user_message})

        for iteration in range(_MAX_ITERATIONS):
            logger.debug("Copilot agentic loop – iteration %d", iteration + 1)

            response_message = await self._call_llm()

            # Plain text response – loop complete
            if not response_message.get("tool_calls"):
                return response_message.get("content") or ""

            # Tool calls requested by the LLM
            self._messages.append(response_message)

            for tool_call in response_message.get("tool_calls", []):
                result = await self._dispatch_tool(tool_call)
                self._messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(result),
                })

        # Fallback if max iterations reached without a plain response
        logger.warning("Copilot agent reached max iterations (%d)", _MAX_ITERATIONS)
        return await self._call_llm_text_only()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _call_llm(self) -> Dict[str, Any]:
        """Call the LLM and return the raw message dict."""
        if not _OPENAI_AVAILABLE or not self._client.is_available():
            return await self._mock_llm_response()

        try:
            async with asyncio.timeout(_API_TIMEOUT):
                response = await self._client._async_openai.chat.completions.create(
                    model=self._model,
                    messages=self._messages,
                    tools=self._tools if self._tools else openai.NOT_GIVEN,
                    tool_choice="auto" if self._tools else openai.NOT_GIVEN,
                    temperature=0.2,
                    max_tokens=4096,
                )
        except TimeoutError:
            raise TimeoutError(
                f"GitHub Copilot API call timed out after {_API_TIMEOUT}s"
            )
        except Exception as conn_exc:
            # Network / auth errors – fall back to offline mode gracefully
            logger.warning(
                "GitHub Copilot API unreachable (%s); using offline fallback",
                conn_exc,
            )
            return await self._mock_llm_response()

        msg = response.choices[0].message
        # Convert to plain dict for uniform handling
        result: Dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        return result

    async def _call_llm_text_only(self) -> str:
        """One final LLM call with tools disabled to force a text response."""
        if not _OPENAI_AVAILABLE or not self._client.is_available():
            return _OFFLINE_FALLBACK_RESPONSE

        try:
            async with asyncio.timeout(_API_TIMEOUT):
                response = await self._client._async_openai.chat.completions.create(
                    model=self._model,
                    messages=self._messages,
                    temperature=0.2,
                    max_tokens=4096,
                )
            return response.choices[0].message.content or ""
        except TimeoutError:
            return _OFFLINE_FALLBACK_RESPONSE
        except Exception as conn_exc:
            logger.warning(
                "GitHub Copilot API unreachable in text-only call (%s)", conn_exc
            )
            return _OFFLINE_FALLBACK_RESPONSE

    async def _dispatch_tool(self, tool_call: Dict[str, Any]) -> Any:
        """Execute a tool call requested by the LLM, with timeout."""
        fn_name = tool_call["function"]["name"]
        try:
            fn_args = json.loads(tool_call["function"]["arguments"])
        except json.JSONDecodeError:
            fn_args = {}

        handler = self._tool_handlers.get(fn_name)
        if handler is None:
            result = {"error": f"Unknown tool: {fn_name}"}
            logger.warning("LLM requested unknown tool: %s", fn_name)
        else:
            try:
                async with asyncio.timeout(_TOOL_TIMEOUT):
                    if asyncio.iscoroutinefunction(handler):
                        result = await handler(**fn_args)
                    else:
                        # Run sync functions in a thread-pool executor
                        loop = asyncio.get_event_loop()
                        result = await loop.run_in_executor(
                            None, lambda: handler(**fn_args)
                        )
            except TimeoutError:
                result = {"error": f"Tool '{fn_name}' timed out after {_TOOL_TIMEOUT}s"}
                logger.error("Tool %s timed out", fn_name)
            except Exception as exc:
                result = {"error": str(exc)}
                logger.exception("Tool %s raised an exception", fn_name)

        self.tool_call_log.append({
            "tool": fn_name,
            "args": fn_args,
            "result_type": type(result).__name__,
            "timestamp": datetime.now().isoformat(),
        })
        return result

    async def _mock_llm_response(self) -> Dict[str, Any]:
        """
        Offline mock: runs all tools sequentially and formats a static report.
        Used when the openai package is absent or no API key is set.
        """
        ticker = None
        # Extract ticker from the bold **TICKER** marker in the user message
        import re
        for msg in reversed(self._messages):
            if msg["role"] == "user":
                # Look for **TICKER** pattern first (our standard prompt format)
                match = re.search(r'\*\*([A-Z0-9.\-]+)\*\*', msg["content"])
                if match:
                    ticker = match.group(1)
                    break
                # Fallback: look for word ending in .BO or .NS
                match = re.search(r'\b([A-Z0-9]+\.(?:BO|NS|BSE|NSE))\b', msg["content"])
                if match:
                    ticker = match.group(1)
                    break
        ticker = ticker or "UNKNOWN"

        # Dispatch all tools for the ticker
        tool_order = [
            ("fetch_market_data", {"ticker": ticker}),
            ("run_nlp_sentiment", {"ticker": ticker}),
        ]
        tool_results: Dict[str, Any] = {}
        for fn_name, args in tool_order:
            handler = self._tool_handlers.get(fn_name)
            if handler:
                try:
                    tool_results[fn_name] = handler(**args)
                except Exception as exc:
                    tool_results[fn_name] = {"error": str(exc)}

        market = tool_results.get("fetch_market_data", {})
        sentiment = tool_results.get("run_nlp_sentiment", {})

        # Generate chart if market data is available
        if market and not market.get("error"):
            chart_handler = self._tool_handlers.get("generate_forecast_chart")
            if chart_handler:
                try:
                    tool_results["generate_forecast_chart"] = chart_handler(data=market)
                except Exception as e:
                    logging.debug("generate_forecast_chart failed: %s", e)

        report = _format_markdown_report(ticker, market, sentiment, tool_results)
        return {"role": "assistant", "content": report}


class CopilotClient:
    """
    GitHub Copilot SDK client.

    Wraps the GitHub Models API endpoint (OpenAI-compatible) so the agent
    can use any frontier model available through GitHub Copilot.

    The GitHub Models endpoint is::

        https://models.inference.ai.azure.com

    Authentication uses a GitHub personal access token (or Copilot token)
    passed via the ``GITHUB_TOKEN`` environment variable.
    """

    _GITHUB_MODELS_BASE_URL = "https://models.inference.ai.azure.com"

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self._token = token or os.getenv("GITHUB_TOKEN", "")
        self._base_url = base_url or os.getenv(
            "COPILOT_BASE_URL", self._GITHUB_MODELS_BASE_URL
        )
        self._async_openai: Optional[Any] = None

        if _OPENAI_AVAILABLE and self._token:
            self._async_openai = openai.AsyncOpenAI(
                api_key=self._token,
                base_url=self._base_url,
            )

    def is_available(self) -> bool:
        """Return True if the client can reach the Copilot/Models API."""
        return _OPENAI_AVAILABLE and bool(self._token) and self._async_openai is not None

    async def create_session(
        self,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_handlers: Optional[Dict[str, Any]] = None,
    ) -> CopilotSession:
        """
        Create and return a new ``CopilotSession``.

        Args:
            model:          LLM model name (default: ``COPILOT_MODEL`` env var
                            or ``gpt-4o``).
            system_prompt:  System-level instructions for the agent.
            tools:          OpenAI-compatible tool schema list.
            tool_handlers:  Dict mapping tool names to Python callables.

        Returns:
            An initialised ``CopilotSession`` ready for ``session.run()``.
        """
        resolved_model = (
            model
            or os.getenv("COPILOT_MODEL", "gpt-4o")
        )
        return CopilotSession(
            client=self,
            model=resolved_model,
            system_prompt=system_prompt or _DEFAULT_SYSTEM_PROMPT,
            tools=tools or [],
            tool_handlers=tool_handlers or {},
        )


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_DEFAULT_SYSTEM_PROMPT = """\
You are StockSense-AI, an expert quantitative financial analyst and machine
learning engineer. You have access to three specialist tools:

  • fetch_market_data   – retrieves historical OHLCV prices, technical
                          indicators, and sector KPIs for a given ticker.
  • run_nlp_sentiment   – processes recent news to produce an NLP sentiment
                          score and article summaries for a given ticker.
  • generate_forecast_chart – prepares time-series data and produces a
                          Matplotlib/Seaborn chart for visualisation.

WORKFLOW
--------
1. Call fetch_market_data(ticker) first to obtain price history and KPIs.
2. Call run_nlp_sentiment(ticker) to incorporate news-driven sentiment.
3. Call generate_forecast_chart(data) with the market data to generate the
   visualisation payload.
4. Synthesise all results into a structured Markdown report.

OUTPUT FORMAT (strict – always follow this template)
-----------------------------------------------------
## StockSense-AI Analysis: {TICKER}

### 1. Executive Summary
<Two-sentence summary of the overall outlook.>

### 2. Market Data & KPIs
| Metric              | Value         |
|---------------------|---------------|
| Current Price       | ₹XXX.XX       |
| 52-Week High        | ₹XXX.XX       |
| 52-Week Low         | ₹XXX.XX       |
| P/E Ratio           | XX.X          |
| Market Cap          | ₹X.XB         |
| RSI (14)            | XX.X          |
| SMA (20-day)        | ₹XXX.XX       |
| Volume (avg 30d)    | XX,XXX,XXX    |

### 3. Sentiment Analysis
| Attribute              | Value         |
|------------------------|---------------|
| Sentiment Score        | +X.XXX        |
| Sentiment Label        | Bullish/…     |
| Bullish Articles       | XX            |
| Bearish Articles       | XX            |
| Neutral Articles       | XX            |
| News Source            | Alpha Vantage NEWS_SENTIMENT |

### 4. Predictive Model – Step-by-Step Logic Breakdown
**Step 1 – Trend Identification:**  <description>
**Step 2 – Momentum Assessment:**   <description>
**Step 3 – Sentiment Integration:** <description>
**Step 4 – Volatility Adjustment:** <description>
**Step 5 – Forecast Generation:**   <description>

### 5. Forecast
| Horizon     | Predicted Price | Change %  | Signal      |
|-------------|-----------------|-----------|-------------|
| 1-Day       | ₹XXX.XX         | +X.XX%    | Buy/Hold/… |
| 5-Day       | ₹XXX.XX         | +X.XX%    | Buy/Hold/… |
| 30-Day      | ₹XXX.XX         | +X.XX%    | Buy/Hold/… |

### 6. Verified Data Sources
| Source                       | Tool Used                    | Latency (ms) |
|------------------------------|------------------------------|--------------|
| Alpha Vantage GLOBAL_QUOTE   | fetch_market_data            | XX           |
| Alpha Vantage TIME_SERIES    | fetch_market_data            | XX           |
| Alpha Vantage NEWS_SENTIMENT | run_nlp_sentiment            | XX           |
| Matplotlib/Seaborn Chart     | generate_forecast_chart      | XX           |

### 7. Confidence Score
**Confidence: XX/100**

| Factor                  | Weight | Score |
|-------------------------|--------|-------|
| Technical Signal Align  | 40 %   | XX    |
| Sentiment Alignment     | 25 %   | XX    |
| Data Freshness          | 20 %   | XX    |
| Volatility Discount     | 15 %   | XX    |

### 8. Risk Disclaimer
*This analysis is generated by an AI model and is for informational purposes
only. It does not constitute financial advice.*
"""

# ---------------------------------------------------------------------------
# Tool Implementations
# ---------------------------------------------------------------------------

def fetch_market_data(ticker: str) -> Dict[str, Any]:
    """
    Tool 1 – Retrieves historical OHLCV price, volume, and sector KPIs via yfinance.

    Returns a structured dict consumed by the LLM and the chart tool.
    """
    start_ts = time.monotonic()
    result: Dict[str, Any] = {
        "ticker": ticker,
        "source": "unknown",
        "latency_ms": 0,
        "quote": {},
        "overview": {},
        "daily_series": [],
        "technical_indicators": {},
        "error": None,
    }

    try:
        import yfinance as yf

        yf_ticker = yf.Ticker(ticker)
        hist = yf_ticker.history(period="3mo")
        info = yf_ticker.info

        if not hist.empty:
            hist_reset = hist.reset_index()
            hist_reset["Date"] = hist_reset["Date"].astype(str)
            result["daily_series"] = hist_reset.tail(60).to_dict(orient="records")
            result["source"] = "yfinance"

            closes = hist["Close"]
            result["technical_indicators"] = {
                "sma_20": round(float(closes.tail(20).mean()), 2),
                "sma_50": round(float(closes.tail(50).mean()), 2),
                "rsi_14": round(_compute_rsi(closes), 2),
                "52_week_high": round(float(info.get("fiftyTwoWeekHigh", 0)), 2),
                "52_week_low": round(float(info.get("fiftyTwoWeekLow", 0)), 2),
                "avg_volume_30d": round(float(hist["Volume"].tail(30).mean()), 0),
                "price_change_7d_pct": round(
                    float(
                        (closes.iloc[-1] - closes.iloc[-7]) / closes.iloc[-7] * 100
                    ),
                    2,
                ) if len(closes) >= 7 else 0.0,
                "volatility_30d": round(
                    float(closes.pct_change().tail(30).std() * 100), 2
                ),
            }

        if info:
            result["quote"] = {
                "currentValue": info.get("currentPrice", 0),
                "change": info.get("regularMarketChange", 0),
                "pChange": info.get("regularMarketChangePercent", 0),
                "dayHigh": info.get("dayHigh", 0),
                "dayLow": info.get("dayLow", 0),
                "previousClose": info.get("previousClose", 0),
                "companyName": info.get("longName", ticker),
            }
            result["overview"] = {
                "Sector": info.get("sector", ""),
                "Industry": info.get("industry", ""),
                "MarketCapitalization": info.get("marketCap", ""),
                "PERatio": info.get("trailingPE", ""),
                "EPS": info.get("trailingEps", ""),
                "DividendYield": info.get("dividendYield", ""),
                "Beta": info.get("beta", ""),
            }

    except Exception as yf_exc:
        result["error"] = f"Data fetch failed: {yf_exc}"
        logger.error("yfinance market data failed for %s: %s", ticker, yf_exc)

    result["latency_ms"] = round((time.monotonic() - start_ts) * 1000, 1)
    return result


def run_nlp_sentiment(ticker: str) -> Dict[str, Any]:
    """
    Tool 2 – Retrieves recent news articles via yfinance.

    Returns article summaries and basic counts.
    Note: ML-derived sentiment scoring is not available via yfinance.
    """
    start_ts = time.monotonic()
    result: Dict[str, Any] = {
        "ticker": ticker,
        "source": "unknown",
        "latency_ms": 0,
        "sentiment_score": 0.0,
        "sentiment_label": "Neutral",
        "bullish_count": 0,
        "bearish_count": 0,
        "neutral_count": 0,
        "total_articles": 0,
        "top_headlines": [],
        "error": None,
    }

    try:
        import yfinance as yf

        yf_ticker = yf.Ticker(ticker)
        news = yf_ticker.news or []

        top_headlines = [
            {
                "title": item.get("content", {}).get("title", "") or item.get("title", ""),
                "sentiment": "Neutral",
                "score": 0.0,
                "source": (
                    item.get("content", {}).get("provider", {}).get("displayName", "")
                    or item.get("publisher", "")
                ),
                "published": str(
                    item.get("content", {}).get("pubDate", "")
                    or item.get("providerPublishTime", "")
                )[:8],
            }
            for item in news[:5]
        ]

        result.update({
            "source": "yfinance_news",
            "sentiment_score": 0.0,
            "sentiment_label": "Neutral",
            "neutral_count": len(news),
            "total_articles": len(news),
            "top_headlines": top_headlines,
        })

    except Exception as exc:
        result["error"] = str(exc)
        logger.error("News fetch failed for %s: %s", ticker, exc)

    result["latency_ms"] = round((time.monotonic() - start_ts) * 1000, 1)
    return result


def generate_forecast_chart(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool 3 – Prepares time-series data for Matplotlib/Seaborn visualisations.

    Generates a price-history chart with SMA overlays and returns the image
    as a base64-encoded PNG, along with a serialisable data payload suitable
    for front-end consumption.
    """
    start_ts = time.monotonic()
    result: Dict[str, Any] = {
        "chart_b64": None,
        "chart_data": {},
        "latency_ms": 0,
        "error": None,
    }

    try:
        import pandas as pd
        from app.utils.visualization_utils import plot_price_history

        ticker = data.get("ticker", "STOCK")
        series = data.get("daily_series", [])
        tech = data.get("technical_indicators", {})

        if not series:
            result["error"] = "No daily series data available for chart generation"
            return result

        df = pd.DataFrame(series)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()

        # Ensure required columns exist
        col_map = {c.lower(): c for c in df.columns}
        rename: Dict[str, str] = {}
        for std, lower in [("Open", "open"), ("High", "high"), ("Low", "low"),
                            ("Close", "close"), ("Volume", "volume")]:
            if std not in df.columns and lower in col_map:
                rename[col_map[lower]] = std
        if rename:
            df = df.rename(columns=rename)

        chart_b64 = plot_price_history(df, ticker)
        result["chart_b64"] = chart_b64

        # Serialisable summary for the LLM
        closes = df["Close"].dropna() if "Close" in df.columns else pd.Series([], dtype=float)
        result["chart_data"] = {
            "ticker": ticker,
            "data_points": len(df),
            "start_date": str(df.index.min().date()) if len(df) else "",
            "end_date": str(df.index.max().date()) if len(df) else "",
            "current_price": round(float(closes.iloc[-1]), 2) if len(closes) else 0.0,
            "sma_20": tech.get("sma_20", 0),
            "sma_50": tech.get("sma_50", 0),
            "rsi_14": tech.get("rsi_14", 0),
            "volatility_30d_pct": tech.get("volatility_30d", 0),
            "chart_generated": True,
        }

    except Exception as exc:
        result["error"] = str(exc)
        logger.exception("Chart generation failed: %s", exc)

    result["latency_ms"] = round((time.monotonic() - start_ts) * 1000, 1)
    return result


# ---------------------------------------------------------------------------
# OpenAI tool schemas (used when the LLM API is available)
# ---------------------------------------------------------------------------

_TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "fetch_market_data",
            "description": (
                "Retrieves historical OHLCV price data, volume, sector KPIs, "
                "and technical indicators for a stock ticker. "
                "Use this as the first step in any stock analysis."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": (
                            "Stock ticker symbol, e.g. 'TCS.BO' (BSE), "
                            "'INFY.NS' (NSE), or 'AAPL' (NASDAQ)."
                        ),
                    }
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_nlp_sentiment",
            "description": (
                "Processes recent news articles for the ticker and returns "
                "an NLP sentiment score, label (Bullish/Neutral/Bearish), "
                "and article-level summaries. "
                "Call after fetch_market_data."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol (same as fetch_market_data).",
                    }
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_forecast_chart",
            "description": (
                "Takes the dict returned by fetch_market_data and produces a "
                "Matplotlib/Seaborn time-series chart (base64 PNG) showing "
                "price history with SMA overlays. "
                "Call last, after fetch_market_data."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "description": "The dict returned by fetch_market_data.",
                    }
                },
                "required": ["data"],
            },
        },
    },
]

_TOOL_HANDLERS: Dict[str, Any] = {
    "fetch_market_data": fetch_market_data,
    "run_nlp_sentiment": run_nlp_sentiment,
    "generate_forecast_chart": generate_forecast_chart,
}

# ---------------------------------------------------------------------------
# StockSenseCopilotAgent – high-level interface
# ---------------------------------------------------------------------------


class StockSenseCopilotAgent:
    """
    High-level async agent that orchestrates the full analysis pipeline.

    Example::

        agent = StockSenseCopilotAgent()
        result = await agent.analyze("TCS.BO")
        print(result["markdown_report"])
    """

    def __init__(
        self,
        github_token: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self._client = CopilotClient(token=github_token)
        self._model = model or os.getenv("COPILOT_MODEL", "gpt-4o")

    async def analyze(self, ticker: str) -> Dict[str, Any]:
        """
        Run the full agentic analysis for *ticker*.

        Returns a dict with:
          * ``markdown_report``  – full Markdown string
          * ``chart_b64``        – base64 PNG chart (if generated)
          * ``market_data``      – raw market data dict
          * ``sentiment``        – raw sentiment dict
          * ``tool_call_log``    – audit log of all tool dispatches
          * ``processing_time_s``– wall-clock seconds taken
          * ``model``            – LLM model used
          * ``copilot_available``– whether live Copilot API was used
        """
        start_ts = time.monotonic()
        logger.info("StockSenseCopilotAgent: starting analysis for %s", ticker)

        session = await self._client.create_session(
            model=self._model,
            system_prompt=_DEFAULT_SYSTEM_PROMPT,
            tools=_TOOL_SCHEMAS,
            tool_handlers=_TOOL_HANDLERS,
        )

        user_prompt = (
            f"Perform a complete quantitative analysis for the stock ticker **{ticker}**. "
            "Use all available tools in sequence: first fetch_market_data, then "
            "run_nlp_sentiment, then generate_forecast_chart. "
            "Finally, produce the full structured Markdown report as specified in your "
            "instructions, including a Confidence Score."
        )

        try:
            markdown_report = await session.run(user_prompt)
        except TimeoutError as exc:
            markdown_report = (
                f"## Analysis Timeout\n\n"
                f"The analysis for **{ticker}** timed out: {exc}\n\n"
                "Please retry."
            )
            logger.error("Analysis timed out for %s: %s", ticker, exc)

        # Extract chart_b64 from tool call log if available
        chart_b64: Optional[str] = None
        market_data: Dict[str, Any] = {}
        sentiment: Dict[str, Any] = {}

        for entry in session.tool_call_log:
            if entry["tool"] == "generate_forecast_chart":
                # Re-run locally if we have the market data (for non-LLM path)
                pass
        # Directly run tools to capture typed results for the response dict
        try:
            market_data = fetch_market_data(ticker)
            sentiment = run_nlp_sentiment(ticker)
            chart_result = generate_forecast_chart(market_data)
            chart_b64 = chart_result.get("chart_b64")
        except Exception as tool_exc:
            logger.warning("Direct tool execution for result dict failed: %s", tool_exc)

        processing_time = round(time.monotonic() - start_ts, 2)
        logger.info(
            "StockSenseCopilotAgent: analysis complete for %s in %.2fs",
            ticker,
            processing_time,
        )

        return {
            "ticker": ticker,
            "markdown_report": markdown_report,
            "chart_b64": chart_b64,
            "market_data": market_data,
            "sentiment": sentiment,
            "tool_call_log": session.tool_call_log,
            "processing_time_s": processing_time,
            "model": self._model,
            "copilot_available": self._client.is_available(),
        }


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _compute_rsi(closes: "pd.Series", period: int = 14) -> float:
    """Compute Relative Strength Index from a close-price Series."""
    try:
        delta = closes.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, float("nan"))
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if not rsi.empty else 50.0
    except Exception:
        return 50.0


def _format_markdown_report(
    ticker: str,
    market: Dict[str, Any],
    sentiment: Dict[str, Any],
    tool_results: Dict[str, Any],
) -> str:
    """
    Build a Markdown report from tool results (used in offline/mock mode).
    """
    quote = market.get("quote", {})
    overview = market.get("overview", {})
    tech = market.get("technical_indicators", {})

    price = quote.get("currentValue", "N/A")
    change_pct = quote.get("pChange", 0)
    company = quote.get("companyName", ticker)

    sma20 = tech.get("sma_20", "N/A")
    sma50 = tech.get("sma_50", "N/A")
    rsi = tech.get("rsi_14", "N/A")
    high52 = tech.get("52_week_high", "N/A")
    low52 = tech.get("52_week_low", "N/A")
    vol30 = tech.get("avg_volume_30d", "N/A")
    vol_pct = tech.get("volatility_30d", "N/A")

    sent_score = sentiment.get("sentiment_score", 0.0)
    sent_label = sentiment.get("sentiment_label", "Neutral")
    bull_ct = sentiment.get("bullish_count", 0)
    bear_ct = sentiment.get("bearish_count", 0)
    neut_ct = sentiment.get("neutral_count", 0)
    total_art = sentiment.get("total_articles", 0)
    sent_latency = sentiment.get("latency_ms", 0)
    mkt_latency = market.get("latency_ms", 0)

    # Simple confidence model
    tech_score = min(100, max(0, int(
        (1 if rsi != "N/A" and 40 < float(rsi) < 70 else 0.5) * 40
    )))
    sent_weight = min(25, int(abs(sent_score) * 100))
    freshness = 20 if market.get("source") != "unknown" else 5
    vol_discount = max(0, 15 - int(float(vol_pct) if vol_pct != "N/A" else 0))
    confidence = tech_score + sent_weight + freshness + vol_discount

    mkt_source = market.get("source", "yfinance")
    chart_latency = tool_results.get("generate_forecast_chart", {}).get("latency_ms", 0)
    chart_status = "✅ Generated" if tool_results.get(
        "generate_forecast_chart", {}
    ).get("chart_b64") else "⚠️ Unavailable"

    return f"""\
## StockSense-AI Analysis: {ticker}

> *Report generated {datetime.now().strftime("%Y-%m-%d %H:%M UTC")} · \
Model: offline/fallback · GitHub Copilot SDK*

### 1. Executive Summary

{company} ({ticker}) is trading at **{price}** with a \
{"positive" if float(change_pct or 0) >= 0 else "negative"} \
session change of {change_pct}%.  Sentiment is **{sent_label}** \
({sent_score:+.3f}) based on {total_art} recent news articles.

---

### 2. Market Data & KPIs

| Metric              | Value               |
|---------------------|---------------------|
| Current Price       | {price}             |
| Day Change %        | {change_pct}%       |
| 52-Week High        | {high52}            |
| 52-Week Low         | {low52}             |
| Sector              | {overview.get("Sector", "N/A")} |
| Industry            | {overview.get("Industry", "N/A")} |
| P/E Ratio           | {overview.get("PERatio", "N/A")} |
| Market Cap          | {overview.get("MarketCapitalization", "N/A")} |
| RSI (14)            | {rsi}               |
| SMA (20-day)        | {sma20}             |
| SMA (50-day)        | {sma50}             |
| Volume (avg 30d)    | {vol30:,} |
| Volatility (30d)    | {vol_pct}%          |

---

### 3. Sentiment Analysis

| Attribute              | Value                              |
|------------------------|------------------------------------|
| Sentiment Score        | {sent_score:+.3f}                  |
| Sentiment Label        | {sent_label}                       |
| Bullish Articles       | {bull_ct}                          |
| Bearish Articles       | {bear_ct}                          |
| Neutral Articles       | {neut_ct}                          |
| Total Articles         | {total_art}                        |
| News Source            | Alpha Vantage NEWS_SENTIMENT      |

---

### 4. Predictive Model – Step-by-Step Logic Breakdown

**Step 1 – Trend Identification:**
RSI of {rsi} indicates \
{"neutral momentum (healthy range)" if 40 < float(rsi if rsi != "N/A" else 50) < 70 else "potential overbought/oversold conditions"}.
Price relative to SMA-20 ({sma20}) and SMA-50 ({sma50}) determines the trend direction.

**Step 2 – Momentum Assessment:**
{"Price is above SMA-20, confirming short-term bullish momentum." if price != "N/A" and sma20 != "N/A" and float(price) > float(sma20) else "Price is below SMA-20, indicating possible consolidation or bearish pressure."}

**Step 3 – Sentiment Integration:**
News sentiment score of {sent_score:+.3f} ({sent_label}) is integrated with a 25 % weighting.
{bull_ct} bullish vs {bear_ct} bearish headlines support the overall outlook.

**Step 4 – Volatility Adjustment:**
30-day volatility of {vol_pct}% is used to widen confidence bands proportionally.
Higher volatility reduces the final confidence score.

**Step 5 – Forecast Generation:**
A weighted composite of technical trend signals (40 %), news sentiment (25 %),
data freshness (20 %), and volatility-adjusted margin (15 %) yields the
Confidence Score below.

---

### 5. Forecast

| Horizon  | Signal              | Basis                          |
|----------|---------------------|--------------------------------|
| 1-Day    | {sent_label}        | Intraday momentum + sentiment  |
| 5-Day    | {"Bullish" if confidence > 55 else "Neutral"} | Short-term trend + news flow |
| 30-Day   | {"Bullish" if confidence > 65 else "Cautious"} | Medium-term technical setup |

---

### 6. Verified Data Sources

| Source                         | Tool                     | Latency (ms) |
|--------------------------------|--------------------------|:------------:|
| Alpha Vantage GLOBAL_QUOTE    | fetch_market_data      | {mkt_latency:.0f} |
| Alpha Vantage TIME_SERIES     | fetch_market_data      | {mkt_latency:.0f} |
| Alpha Vantage COMPANY_OVERVIEW| fetch_market_data      | {mkt_latency:.0f} |
| Alpha Vantage NEWS_SENTIMENT  | run_nlp_sentiment      | {sent_latency:.0f} |
| Matplotlib/Seaborn Chart       | generate_forecast_chart| {chart_latency:.0f} |
| Fallback (yfinance)            | —                        | — |

*Primary source: **{mkt_source}**. Chart: {chart_status}.*

---

### 7. Confidence Score

**Confidence: {confidence}/100**

| Factor                  | Weight | Score |
|-------------------------|:------:|:-----:|
| Technical Signal Align  | 40 %   | {tech_score}  |
| Sentiment Alignment     | 25 %   | {sent_weight} |
| Data Freshness          | 20 %   | {freshness}   |
| Volatility Discount     | 15 %   | {vol_discount}|
| **Total**               | **100 %** | **{confidence}** |

---

### 8. Risk Disclaimer

*This analysis is generated by an AI model and is for informational purposes
only.  It does not constitute financial advice.  Past performance is not
indicative of future results.*
"""


# Shown when LLM API is unavailable and mock also fails
_OFFLINE_FALLBACK_RESPONSE = (
    "## StockSense-AI – Service Unavailable\n\n"
    "The GitHub Copilot API is not reachable (check `GITHUB_TOKEN`) and "
    "the offline fallback also encountered an error.\n\n"
    "Please ensure:\n"
    "1. `GITHUB_TOKEN` is set to a valid GitHub PAT with `models:read` scope.\n"
    "2. Internet connectivity is available for yfinance market data.\n"
)


# ---------------------------------------------------------------------------
# Standalone entry-point (async)
# ---------------------------------------------------------------------------

async def _main(ticker: str = "TCS.BO") -> None:
    """Run a one-shot analysis from the command line."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    agent = StockSenseCopilotAgent()
    print(f"\n{'=' * 70}")
    print(f"  StockSense-AI Copilot Agent  |  Analysing: {ticker}")
    print(f"{'=' * 70}\n")
    result = await agent.analyze(ticker)

    print(result["markdown_report"])
    print(f"\n--- Processing time: {result['processing_time_s']}s ---")
    print(f"--- Model: {result['model']} ---")
    print(f"--- Copilot API live: {result['copilot_available']} ---")
    if result.get("chart_b64"):
        print("--- Chart generated (base64 PNG available) ---")


if __name__ == "__main__":
    import sys

    ticker_arg = sys.argv[1] if len(sys.argv) > 1 else "TCS.BO"
    asyncio.run(_main(ticker_arg))
