"""
Production-ready visualization utilities for StockSense.

All functions return base64-encoded PNG strings (ready for embedding in HTML
``<img src="data:image/png;base64,...">`` tags) or save to a file path.

Depends on: matplotlib, seaborn, pandas, numpy (all in requirements.txt)
"""
import base64
import io
import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Lazy import guard — allow server startup even when display is unavailable
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend (no X11 required)
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import matplotlib.gridspec as gridspec
    import seaborn as sns
    _MATPLOTLIB_AVAILABLE = True
except ImportError:
    _MATPLOTLIB_AVAILABLE = False
    logger.warning("matplotlib/seaborn not installed — visualizations disabled")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fig_to_base64(fig) -> str:
    """Encode a matplotlib Figure as a base64 PNG data-URI."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor=fig.get_facecolor())
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return encoded


def _apply_dark_theme():
    """Apply a dark finance-style theme to all subsequent plots."""
    plt.style.use('dark_background')
    sns.set_palette('husl')


# ---------------------------------------------------------------------------
# 1. Historical Price Chart with Volume
# ---------------------------------------------------------------------------

def plot_price_history(
    df: pd.DataFrame,
    symbol: str,
    title: Optional[str] = None,
) -> Optional[str]:
    """
    Generate a two-panel OHLCV chart:
      * Upper panel: Close price + 20-day SMA + 50-day SMA
      * Lower panel: Volume bars colour-coded by price direction

    Args:
        df: DataFrame with columns [Open, High, Low, Close, Volume] indexed by date.
        symbol: Ticker symbol (used in the title).
        title: Optional chart title override.

    Returns:
        base64-encoded PNG string, or None if matplotlib is unavailable.
    """
    if not _MATPLOTLIB_AVAILABLE:
        return None

    _apply_dark_theme()
    df = df.tail(180).copy()  # Last 6 months for readability

    # Calculate moving averages
    df['SMA_20'] = df['Close'].rolling(20).mean()
    df['SMA_50'] = df['Close'].rolling(50).mean()

    fig = plt.figure(figsize=(14, 8), facecolor='#0d1117')
    gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1], hspace=0.06)

    # --- Price panel ---
    ax1 = fig.add_subplot(gs[0])
    ax1.set_facecolor('#0d1117')
    ax1.plot(df.index, df['Close'], color='#58a6ff', linewidth=1.5, label='Close')
    ax1.plot(df.index, df['SMA_20'], color='#f0883e', linewidth=1.0, linestyle='--', label='SMA 20')
    ax1.plot(df.index, df['SMA_50'], color='#3fb950', linewidth=1.0, linestyle='--', label='SMA 50')
    ax1.fill_between(df.index, df['Close'], df['Close'].min(), alpha=0.08, color='#58a6ff')
    ax1.set_ylabel('Price (₹)', color='#8b949e')
    ax1.tick_params(colors='#8b949e')
    ax1.xaxis.set_visible(False)
    ax1.legend(loc='upper left', facecolor='#161b22', edgecolor='#30363d', labelcolor='#c9d1d9', fontsize=9)
    ax1.grid(axis='y', color='#21262d', linewidth=0.5)
    ax1.set_title(title or f'{symbol} — Price History', color='#c9d1d9', fontsize=13, pad=12)
    ax1.spines[:].set_color('#30363d')

    # --- Volume panel ---
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax2.set_facecolor('#0d1117')
    colours = ['#3fb950' if c >= o else '#f85149'
               for c, o in zip(df['Close'], df['Open'])]
    ax2.bar(df.index, df['Volume'], color=colours, alpha=0.8, width=0.8)
    ax2.set_ylabel('Volume', color='#8b949e')
    ax2.tick_params(colors='#8b949e')
    ax2.grid(axis='y', color='#21262d', linewidth=0.5)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %y'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator())
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha='right', color='#8b949e')
    ax2.spines[:].set_color('#30363d')

    return _fig_to_base64(fig)


# ---------------------------------------------------------------------------
# 2. KPI Dashboard (Fundamental Metrics)
# ---------------------------------------------------------------------------

def plot_kpi_dashboard(
    overview: Dict[str, Any],
    symbol: str,
) -> Optional[str]:
    """
    Generate a KPI summary card chart showing key fundamental metrics
    sourced from Alpha Vantage COMPANY_OVERVIEW.

    Metrics displayed:
      P/E, EPS, Market Cap, 52-week High/Low, Dividend Yield,
      Beta, Sector, Revenue TTM, Gross Profit TTM.

    Returns:
        base64-encoded PNG string, or None if matplotlib is unavailable.
    """
    if not _MATPLOTLIB_AVAILABLE or not overview:
        return None

    _apply_dark_theme()

    kpis = [
        ('P/E Ratio', overview.get('PERatio', 'N/A')),
        ('EPS (TTM)', overview.get('EPS', 'N/A')),
        ('Beta', overview.get('Beta', 'N/A')),
        ('Div. Yield', overview.get('DividendYield', 'N/A')),
        ('52W High', overview.get('52WeekHigh', 'N/A')),
        ('52W Low', overview.get('52WeekLow', 'N/A')),
        ('Mkt Cap', _human_number(overview.get('MarketCapitalization', 'N/A'))),
        ('Rev. TTM', _human_number(overview.get('RevenueTTM', 'N/A'))),
        ('Profit Margin', _percent(overview.get('ProfitMargin', 'N/A'))),
        ('ROE', _percent(overview.get('ReturnOnEquityTTM', 'N/A'))),
    ]

    sector = overview.get('Sector', 'Unknown')
    industry = overview.get('Industry', '')
    description = overview.get('Description', '')[:200] + '...' if overview.get('Description') else ''

    fig, axes = plt.subplots(2, 5, figsize=(16, 6), facecolor='#0d1117')
    fig.suptitle(
        f"{overview.get('Name', symbol)}  [{symbol}]  —  {sector}",
        color='#c9d1d9', fontsize=13, fontweight='bold', y=1.01,
    )

    for ax, (label, value) in zip(axes.flat, kpis):
        ax.set_facecolor('#161b22')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        ax.text(0.5, 0.65, str(value), ha='center', va='center',
                color='#58a6ff', fontsize=16, fontweight='bold')
        ax.text(0.5, 0.25, label, ha='center', va='center',
                color='#8b949e', fontsize=9)
        for spine in ax.spines.values():
            spine.set_edgecolor('#30363d')

    plt.tight_layout()
    return _fig_to_base64(fig)


# ---------------------------------------------------------------------------
# 3. Sentiment Analysis Chart
# ---------------------------------------------------------------------------

def plot_sentiment_analysis(
    sentiment_data: Dict[str, Any],
    symbol: str,
) -> Optional[str]:
    """
    Visualise news sentiment distribution from Alpha Vantage NEWS_SENTIMENT.

    Left panel  – Pie chart of Bullish / Neutral / Bearish article counts.
    Right panel – Time-series scatter of per-article sentiment scores.

    Confidence Score: 80% (ML-derived from aggregated news feeds)

    Returns:
        base64-encoded PNG string, or None if data/matplotlib unavailable.
    """
    if not _MATPLOTLIB_AVAILABLE or not sentiment_data:
        return None

    _apply_dark_theme()

    summary = sentiment_data.get('sentiment_summary', {})
    feed = sentiment_data.get('feed', [])

    bullish = summary.get('bullish_count', 0)
    bearish = summary.get('bearish_count', 0)
    neutral = summary.get('neutral_count', 0)
    avg_score = summary.get('average_sentiment_score', 0.0)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), facecolor='#0d1117')
    fig.suptitle(f'{symbol} — News Sentiment Analysis  (avg score: {avg_score:+.3f})',
                 color='#c9d1d9', fontsize=13, fontweight='bold')

    # --- Pie chart ---
    ax1.set_facecolor('#0d1117')
    sizes = [bullish, neutral, bearish]
    colours = ['#3fb950', '#8b949e', '#f85149']
    labels_pie = [f'Bullish\n{bullish}', f'Neutral\n{neutral}', f'Bearish\n{bearish}']
    non_zero = [(s, c, l) for s, c, l in zip(sizes, colours, labels_pie) if s > 0]
    if non_zero:
        s, c, lbl = zip(*non_zero)
        wedges, texts, autotexts = ax1.pie(
            s, colors=c, labels=lbl, autopct='%1.0f%%',
            startangle=140, pctdistance=0.75,
        )
        for t in texts + autotexts:
            t.set_color('#c9d1d9')
            t.set_fontsize(9)
    else:
        ax1.text(0.5, 0.5, 'No sentiment data', ha='center', va='center',
                 color='#8b949e', transform=ax1.transAxes)
    ax1.set_title('Sentiment Distribution', color='#c9d1d9', fontsize=11)

    # --- Time-series scatter ---
    ax2.set_facecolor('#0d1117')
    if feed:
        dates, scores, colours_s = [], [], []
        for article in feed[-40:]:  # Last 40 articles
            try:
                ts = article.get('time_published', '')
                date = pd.to_datetime(ts[:8], format='%Y%m%d') if ts else None
                score = float(article.get('overall_sentiment_score', 0))
                if date:
                    dates.append(date)
                    scores.append(score)
                    colours_s.append('#3fb950' if score > 0.1 else '#f85149' if score < -0.1 else '#8b949e')
            except (ValueError, TypeError):
                pass

        if dates:
            ax2.scatter(dates, scores, c=colours_s, s=50, alpha=0.8, zorder=3)
            ax2.axhline(0, color='#30363d', linewidth=0.8)
            ax2.axhline(avg_score, color='#f0883e', linewidth=1.2, linestyle='--',
                        label=f'Avg {avg_score:+.3f}')
            ax2.fill_between(dates, scores, 0,
                             where=[s > 0 for s in scores], alpha=0.12, color='#3fb950')
            ax2.fill_between(dates, scores, 0,
                             where=[s < 0 for s in scores], alpha=0.12, color='#f85149')
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha='right', color='#8b949e')
            ax2.tick_params(colors='#8b949e')
            ax2.legend(facecolor='#161b22', edgecolor='#30363d', labelcolor='#c9d1d9', fontsize=9)

    ax2.set_ylabel('Sentiment Score', color='#8b949e')
    ax2.set_title('Per-Article Sentiment Over Time', color='#c9d1d9', fontsize=11)
    ax2.grid(axis='y', color='#21262d', linewidth=0.5)
    ax2.spines[:].set_color('#30363d')

    plt.tight_layout()
    return _fig_to_base64(fig)


# ---------------------------------------------------------------------------
# 4. ML Forecast Chart
# ---------------------------------------------------------------------------

def plot_forecast(
    df: pd.DataFrame,
    predicted_price: float,
    symbol: str,
    confidence: float = 0.5,
    horizon_days: int = 5,
) -> Optional[str]:
    """
    Overlay a simple linear ML forecast on the recent price history.

    Args:
        df: Historical OHLCV DataFrame.
        predicted_price: Forecasted next-day (or n-day) close.
        symbol: Ticker symbol.
        confidence: Model confidence (0-1), used to shade prediction band.
        horizon_days: Forecast horizon for the shaded band.

    Returns:
        base64-encoded PNG string, or None if matplotlib is unavailable.
    """
    if not _MATPLOTLIB_AVAILABLE:
        return None

    _apply_dark_theme()

    recent = df.tail(60).copy()
    last_date = recent.index[-1]
    last_price = float(recent['Close'].iloc[-1])

    future_dates = pd.bdate_range(start=last_date, periods=horizon_days + 1)[1:]
    spread = abs(predicted_price - last_price) * (1 - confidence) * 0.5
    pred_high = [predicted_price + spread] * len(future_dates)
    pred_low = [predicted_price - spread] * len(future_dates)
    pred_mid = np.linspace(last_price, predicted_price, len(future_dates))

    fig, ax = plt.subplots(figsize=(13, 6), facecolor='#0d1117')
    ax.set_facecolor('#0d1117')

    ax.plot(recent.index, recent['Close'], color='#58a6ff', linewidth=1.5, label='Historical Close')
    ax.plot(future_dates, pred_mid, color='#f0883e', linewidth=1.5, linestyle='--',
            label=f'Forecast ₹{predicted_price:.2f}')
    ax.fill_between(future_dates, pred_low, pred_high, alpha=0.2, color='#f0883e',
                    label=f'Confidence band ({confidence * 100:.0f}%)')

    # Mark last actual close
    ax.scatter([last_date], [last_price], color='#58a6ff', s=60, zorder=5)
    ax.scatter(future_dates[-1:], [predicted_price], color='#f0883e', marker='*', s=120, zorder=5)

    ax.set_title(f'{symbol} — ML Price Forecast  (Confidence: {confidence * 100:.0f}%)',
                 color='#c9d1d9', fontsize=13)
    ax.set_ylabel('Price (₹)', color='#8b949e')
    ax.tick_params(colors='#8b949e')
    ax.legend(facecolor='#161b22', edgecolor='#30363d', labelcolor='#c9d1d9', fontsize=9)
    ax.grid(axis='y', color='#21262d', linewidth=0.5)
    ax.spines[:].set_color('#30363d')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha='right', color='#8b949e')

    plt.tight_layout()
    return _fig_to_base64(fig)


# ---------------------------------------------------------------------------
# 5. Financial Statement Bar Chart
# ---------------------------------------------------------------------------

def plot_income_trends(
    income_data: Dict[str, Any],
    symbol: str,
    metric: str = 'totalRevenue',
    label: str = 'Total Revenue',
) -> Optional[str]:
    """
    Bar chart of annual income-statement metrics over reporting periods.

    Args:
        income_data: Dict returned by ``get_income_statement()``.
        symbol: Ticker symbol.
        metric: Key name within each annualReport dict.
        label: Human-readable label for the metric.

    Returns:
        base64-encoded PNG string, or None if data/matplotlib unavailable.
    """
    if not _MATPLOTLIB_AVAILABLE or not income_data:
        return None

    _apply_dark_theme()

    reports = income_data.get('annualReports', [])[:5]  # Last 5 years
    if not reports:
        return None

    dates = [r.get('fiscalDateEnding', '')[:4] for r in reports]
    values = [_parse_float_safe(r.get(metric)) for r in reports]
    dates, values = zip(*[(d, v) for d, v in zip(dates, values) if v is not None]) if any(v is not None for v in values) else ([], [])

    if not dates:
        return None

    fig, ax = plt.subplots(figsize=(10, 5), facecolor='#0d1117')
    ax.set_facecolor('#0d1117')

    bar_colours = ['#3fb950' if v >= 0 else '#f85149' for v in values]
    bars = ax.bar(dates, [abs(v) for v in values], color=bar_colours, alpha=0.85, width=0.5)

    # Value labels on bars
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                _human_number(val), ha='center', va='bottom', color='#c9d1d9', fontsize=9)

    ax.set_title(f'{symbol} — {label} (Annual)', color='#c9d1d9', fontsize=13)
    ax.set_ylabel(label, color='#8b949e')
    ax.tick_params(colors='#8b949e')
    ax.grid(axis='y', color='#21262d', linewidth=0.5)
    ax.spines[:].set_color('#30363d')

    plt.tight_layout()
    return _fig_to_base64(fig)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _human_number(value: Any) -> str:
    """Format a large number as human-readable string (e.g., 1.23B)."""
    try:
        n = float(str(value).replace(',', ''))
        if abs(n) >= 1e12:
            return f'{n / 1e12:.2f}T'
        if abs(n) >= 1e9:
            return f'{n / 1e9:.2f}B'
        if abs(n) >= 1e6:
            return f'{n / 1e6:.2f}M'
        if abs(n) >= 1e3:
            return f'{n / 1e3:.2f}K'
        return f'{n:.2f}'
    except (ValueError, TypeError):
        return str(value)


def _percent(value: Any) -> str:
    """Format a decimal as a percentage string."""
    try:
        return f'{float(value) * 100:.2f}%'
    except (ValueError, TypeError):
        return str(value)


def _parse_float_safe(value: Any) -> Optional[float]:
    """Return float or None if value cannot be converted."""
    try:
        return float(str(value).replace(',', ''))
    except (ValueError, TypeError):
        return None
