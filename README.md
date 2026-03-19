# StockSense — AI-Powered Indian Stock Prediction Platform

StockSense is a production-ready Flask web application that delivers real-time BSE/NSE stock
data, ML-based price predictions (using a local Ollama LLM), and intelligent alerts with a
WebSocket-driven UI.

---

## Architecture Overview

```
stocksense/
├── app/
│   ├── main.py                  # Flask app entry point, SocketIO, blueprint registration
│   ├── config_settings.py       # Centralised settings (DB path, Ollama host/model, …)
│   ├── config/
│   │   ├── ollama_config.py     # Ollama LLM parameters & prompts
│   │   └── gemini_config.py     # Gemini parameters (optional, not used by default)
│   ├── api/                     # Flask blueprints – one file per feature domain
│   │   ├── auth_routes.py       # Login / logout / register
│   │   ├── dashboard_routes.py  # Main UI pages
│   │   ├── watchlist_routes.py  # Watchlist CRUD
│   │   ├── prediction_routes.py # Batch & single-stock prediction triggers
│   │   ├── stock_routes.py      # Stock list / detail / search
│   │   ├── alert_routes.py      # User-defined price alerts
│   │   ├── notification_routes.py
│   │   ├── nse_routes.py        # NSE securities management
│   │   ├── backtest_routes.py   # Simple backtesting
│   │   ├── chat_routes.py       # AI chat interface
│   │   ├── llm_routes.py        # Direct LLM queries
│   │   ├── price_stream_routes.py
│   │   ├── system_routes.py     # Admin / system health
│   │   └── agentic_routes.py    # Agentic prediction API (/api/agentic)
│   ├── agents/                  # Agentic ML prediction pipeline
│   │   ├── base_agent.py
│   │   ├── data_enrichment_agent.py
│   │   ├── ensemble_agent.py
│   │   ├── adaptive_learning_agent.py
│   │   ├── prediction_coordinator.py
│   │   └── chat_agent.py        # NLP chat agent (Ollama-backed)
│   ├── db/
│   │   ├── session_manager.py   # Thread-safe SQLite connection pool (WAL mode)
│   │   ├── data_models.py       # Dataclasses (StockQuote, Prediction, User, …)
│   │   └── services/            # Single-table CRUD services
│   │       ├── user_service.py
│   │       ├── stock_quote_service.py
│   │       ├── prediction_service.py
│   │       ├── watchlist_service.py
│   │       ├── alert_service.py
│   │       ├── chat_service.py
│   │       └── model_configuration_service.py
│   ├── features/
│   │   └── feature_factory.py   # Technical indicators (SMA, EMA, RSI, MACD, …)
│   ├── models/
│   │   ├── ollama_model.py      # Ollama LLM wrapper – stock prediction
│   │   └── gemini_model.py      # Gemini AI wrapper (optional)
│   ├── services/
│   │   ├── auth_service.py      # Flask-Login User & WatchlistService
│   │   ├── background_worker.py # Automated daily download + prediction worker
│   │   ├── prediction_service.py# prediction_executor – runs the agentic pipeline
│   │   ├── alert_service.py     # Alert evaluation (Ollama-based)
│   │   ├── price_streamer.py    # Real-time price WebSocket streamer
│   │   ├── backtester.py        # Lightweight backtesting against stored predictions
│   │   ├── configuration_service.py
│   │   ├── digest_service.py    # Daily email digest
│   │   ├── inactive_stock_worker.py  # Retry inactive stocks
│   │   ├── llm_advisor.py
│   │   ├── news_service.py      # Stub – future NewsAPI integration
│   │   ├── nse_securities_service.py
│   │   ├── ollama_chat_service.py
│   │   ├── options_service.py
│   │   ├── portfolio_service.py # Stub – future portfolio tracking
│   │   └── worker_config.py
│   ├── utils/
│   │   ├── util.py              # get_db_connection() shim (delegates to pool)
│   │   ├── yfinance_utils.py    # yfinance helpers – quotes, search, retry
│   │   ├── bse_utils.py
│   │   ├── disk_monitor.py      # Disk-space monitoring & model cleanup
│   │   └── websocket_manager.py # SocketIO event helpers
│   ├── static/                  # CSS / JS / images
│   └── templates/               # Jinja2 HTML templates
├── scripts/
│   ├── init_db_schema.py        # DB initialisation & reset CLI tool
│   ├── download_stk_json.py
│   ├── reset_db.py
│   ├── create_admin.py
│   └── make_admin.py
├── stk.json                     # BSE/NSE scrip code → company name mapping
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── OLLAMA.md                    # Ollama setup guide
```

---

## ⚡ Quick Start

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.ai) (local LLM for predictions)
- SQLite (bundled with Python)

### Local Development

```bash
# 1. Clone and install
git clone <repo-url>
cd stocksense
pip install -r requirements.txt

# 2. Copy and edit environment variables
cp .env.example .env          # set SECRET_KEY at minimum

# 3. Initialise database schema
python scripts/init_db_schema.py --init --load-stk

# 4. Start Ollama and pull the prediction model
ollama serve &
ollama pull phi4-mini          # or whichever model is set in OLLAMA_MODEL_NAME

# 5. Run the app
python -m app.main
```

Access: http://localhost:5005

### Docker (Production)

```bash
docker-compose up
```

---

## Configuration

All runtime settings are loaded from environment variables (`.env` file or OS environment).

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-key-change-in-production` | Flask session key – **change in production** |
| `FLASK_PORT` | `5005` | HTTP port |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API base URL |
| `OLLAMA_MODEL_NAME` | `phi4-mini` | Model to use for predictions |
| `GEMINI_API_KEY` | *(empty)* | Optional Gemini key – not used by default |
| `DEBUG` | `false` | Enable Flask debug mode |
| `ADMIN_ALERT_EMAILS` | *(empty)* | Comma-separated list for daily digest emails |

---

## REST API Reference

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/login` | Obtain session |
| `POST` | `/auth/register` | Create account |
| `GET` | `/auth/logout` | Invalidate session |

### Stocks
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/stocks/list` | Paginated stock list with optional sorting |
| `GET` | `/api/stocks/<security_id>` | Single stock detail |
| `GET` | `/api/stocks/search?q=<name>` | yfinance company search |
| `GET` | `/api/stocks/quote-by-name?q=<name>` | Fetch live quote by company name |
| `GET` | `/api/stocks/suggestions?q=<name>` | Autocomplete from local STK table |

### Predictions
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/predictions/trigger` | Run batch predictions |
| `POST` | `/api/predictions/trigger_watchlist` | Predict for watchlist stocks |
| `POST` | `/api/predictions/trigger_single` | Predict for one stock |
| `GET` | `/api/predictions/stock/<security_id>` | Latest prediction for a stock |
| `GET` | `/api/predictions/stream` | SSE stream of live prediction events |

### Agentic API
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/agentic/predict/<symbol>` | Multi-agent prediction with confidence scoring |
| `POST` | `/api/agentic/feedback` | Submit actual price to improve adaptive learning |
| `GET` | `/api/agentic/performance` | Agent performance report |
| `GET` | `/api/agentic/health` | Agentic system health check |

### Alerts & Notifications
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/alerts` | List alerts |
| `POST` | `/api/alerts` | Create alert |
| `DELETE` | `/api/alerts/<id>` | Delete alert |
| `GET` | `/api/notifications` | List notifications |

---

## Database

StockSense uses a single **SQLite** database at `app/db/stock_predictions.db`.

Key tables:

| Table | Purpose |
|---|---|
| `users` | Authentication, subscription tier |
| `watchlists` | Per-user stock watchlists |
| `stock_quotes` | Latest BSE/NSE market data |
| `predictions` | AI price predictions history |
| `alerts` | User-defined price alert rules |
| `notifications` | Triggered alert notifications |
| `model_configurations` | Per-symbol ML hyperparameters |
| `STK` | Scrip code → company name master table |

All database access goes through `app/db/session_manager.DatabaseSessionManager` which
provides a **thread-safe WAL-mode connection pool** with automatic retry on transient locks.

### Schema Management

```bash
# Initialise (safe – won't overwrite existing data)
python scripts/init_db_schema.py --init

# Load stock master data from stk.json
python scripts/init_db_schema.py --init --load-stk

# Reset (wipe all data except users)
python scripts/init_db_schema.py --reset
```

---

## Background Worker

The `BackgroundWorker` runs once per calendar day and:
1. **Downloads** fresh quotes for all stocks in `stk.json` using yfinance (4 parallel threads).
2. **Predicts** future prices for every stock in user watchlists via the agentic pipeline.
3. **Evaluates alerts** and persists notifications.
4. **Sends a daily email digest** if `digest_email_enabled` is set in worker config and
   `ADMIN_ALERT_EMAILS` env var is configured.

Enable/disable the worker from the admin UI or system API.

---

## WebSocket Events

Real-time updates are pushed via SocketIO.

| Event (server → client) | Payload |
|---|---|
| `prediction_update` | New prediction result |
| `prediction_progress` | Batch progress status |
| `stock_price_update` | Live price tick |
| `background_worker_status` | Download / prediction progress |
| `system_alert` | Disk space warnings |

| Event (client → server) | Description |
|---|---|
| `subscribe_predictions` | Start receiving prediction events |
| `subscribe_watchlist` | Watchlist update stream |
| `subscribe_stock_prices` | Live price stream for given symbols |
| `unsubscribe_stock_prices` | Stop price stream |
| `request_system_status` | One-shot system status |

---

## Technical Indicators (feature_factory)

`calculate_technical_indicators()` computes the following features for ML models:

- **Trend**: SMA and EMA for configurable periods (default 5, 10, 20, 50)
- **Volatility**: ATR, Bollinger Bands, Returns Volatility
- **Momentum**: RSI (14), MACD (12/26/9), Rate of Change (12)
- **Volume**: OBV, Volume SMA (20), Volume Ratio

---

## Contributing

1. Fork → feature branch → pull request.
2. Follow `pyproject.toml` formatting (Black, line-length 120).
3. Run `flake8` before submitting.

---

## License

MIT
