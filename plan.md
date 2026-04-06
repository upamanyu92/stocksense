# StockSense — Agent Context Plan

> This document is a reference for Claude Sonnet (and other AI agents) working on the StockSense repository.
> It summarises the project structure, conventions, key subsystems, and guardrails needed to make safe, well-scoped changes.

---

## 1. What Is StockSense?

StockSense is a **Flask-based AI-powered stock prediction platform** focused on Indian equity markets (NSE/BSE).  
It combines:

- ML ensemble price-prediction models (scikit-learn, Keras/TensorFlow)
- Local LLM inference via **Ollama** (default: `phi-mini`) or cloud LLMs (Gemini, GitHub Copilot/OpenAI-compatible)
- A multi-agent prediction pipeline with pre-serve and post-outcome evaluator agents
- Real-time WebSocket price streaming (Flask-SocketIO, threading mode)
- Portfolio management, backtesting, alerts, watchlists, and a premium analytics dashboard
- SQLite as the sole persistent store (WAL mode, pooled via `DatabaseSessionManager`)

Run: `python -m app.main` → http://localhost:5005

---

## 2. Directory Map

```
stocksense/
├── app/
│   ├── main.py                  # Flask app factory, blueprint registration, SocketIO setup
│   ├── config.py / config_settings.py  # App config, LLM init
│   ├── agents/                  # Agentic prediction pipeline (see §5)
│   ├── api/                     # Blueprint route handlers (see §4)
│   ├── db/                      # SQLite session manager, schema, migrations, DB services
│   ├── features/                # Feature engineering pipeline
│   ├── models/                  # ML model artifacts and loaders (gemini_model, ollama_model)
│   ├── services/                # Business-logic services (see §6)
│   ├── static/                  # CSS / JS / images
│   ├── templates/               # Jinja2 HTML templates
│   └── utils/                   # Shared utilities (yfinance, disk monitor, websocket manager, …)
├── scripts/                     # DB init/schema, scheduled jobs, ops tooling
├── tests/
│   ├── api/                     # Backend API route tests
│   ├── agents/                  # Evaluative agent unit tests
│   ├── integration/             # End-to-end integration tests
│   ├── ui/                      # UI endpoint smoke tests
│   └── conftest.py              # Shared fixtures (FakeSessionManager, test SQLite DB)
├── Agent.md                     # Detailed agent mission and guardrails (read this too)
├── README.md                    # Quick-start and API reference
├── OLLAMA.md                    # Ollama setup guide
├── requirements.txt
├── docker-compose.yml / Dockerfile
└── plan.md                      # ← this file
```

---

## 3. Database Layer

| Concept | Detail |
|---------|--------|
| Engine | SQLite (WAL mode, connection pool) |
| Session manager | `app/db/session_manager.DatabaseSessionManager` — obtained via `get_session_manager()` |
| Query helpers | `fetch_one()` / `fetch_all()` on the session object |
| Migrations | SQL files in `app/db/migrations/` — executed at startup via `sqlite3.connect().executescript()` using `CREATE TABLE IF NOT EXISTS` (idempotent) |
| DB file | `app/db/stock_predictions.db` |
| DB services | `app/db/services/` — thin query wrappers: `alert_service`, `chat_service`, `prediction_service`, `stock_quote_service`, `system_settings_service`, `user_service`, `watchlist_service`, `model_configuration_service` |

> **Testing note:** `conftest.py` supplies a `_FakeSessionManager` wrapping a test SQLite DB.  
> New services using `get_session_manager()` must be patched **in the session_manager module AND in the service module itself**.

---

## 4. API Blueprints

| Blueprint | Mount | Purpose |
|-----------|-------|---------|
| `auth_bp` | `/` | Login / logout / registration |
| `alpha_vantage_bp` | `/api/av` | yfinance-based market data (Alpha Vantage routes preserved for compatibility) |
| `copilot_bp` | `/api/copilot` | GitHub Copilot / OpenAI-compatible LLM chat |
| `prediction_bp` | `/api/predictions` | Standard ML predictions |
| `agentic_api` | `/api/agentic` | Agentic predict, feedback, performance, health |
| `backtest_bp` | `/api/backtest` | Walk-forward backtesting |
| `stock_bp` | `/api/stocks` | Stock search and info |
| `watchlist_bp` | `/api/watchlist` | User watchlists |
| `alert_bp` | `/api/alerts` | Price / condition alerts |
| `notification_bp` | `/api/notifications` | In-app notifications |
| `dashboard_bp` | `/api/dashboard` | Standard dashboard data |
| `premium_dashboard_bp` | `/premium` + `/api/dashboard/*` | Premium analytics dashboard (10 endpoints) |
| `portfolio_bp` | `/api/portfolio` | Portfolio CRUD, XLSX/CSV import, P&L |
| `settings_bp` | `/api/settings` | User settings / onboarding |
| `llm_bp` | `/api/llm` | LLM advisor endpoints |
| `nse_bp` | `/api/nse` | NSE-specific data |
| `price_stream_bp` | `/api/price-stream` | WebSocket price subscriptions |
| `system_bp` | `/api/system` | System status, background worker control |
| `chat_bp` | `/api/chat` | Chat history |

Route to page: root `/` → redirects authenticated users to `/premium` (premium dashboard).

---

## 5. Agentic Pipeline (`app/agents/`)

```
PredictionCoordinator
  ├── DataEnrichmentAgent      — enriches raw price data with features
  ├── EnsembleAgent            — runs ML ensemble prediction
  ├── PredictionEvaluatorAgent — pre-serve quality gate (score, action)
  │     actions: proceed | proceed_with_caution | shadow_only | block_prediction
  ├── AdaptiveLearningAgent    — learns from past errors
  └── OutcomeEvaluatorAgent    — post-outcome scoring after actual prices arrive
```

Base classes: `BaseAgent`, `BaseEvaluativeAgent`.  
Chat-specific agent: `ChatAgent`, `CopilotAgent`.

Agentic API response fields: `evaluation.score`, `evaluation.score_pct`, `evaluation.action`, `serving_action`.

---

## 6. Services (`app/services/`)

| Service | Responsibility |
|---------|---------------|
| `auth_service` | User auth (Flask-Login) |
| `prediction_service` | Core ML prediction orchestration |
| `portfolio_service` | Holdings, transactions, XLSX/CSV import, P&L (CRUD) |
| `portfolio_analysis_service` | Analytics on portfolio data |
| `backtester` | Walk-forward / rolling backtesting |
| `alert_service` | Alert creation, evaluation, notification dispatch |
| `background_worker` | Scheduled background tasks (predictions, alerts) |
| `inactive_stock_worker` | Retry worker for inactive/stale stocks |
| `price_streamer` | WebSocket price streaming via yfinance |
| `news_service` | Stock news fetching |
| `llm_advisor` | LLM-backed advisory responses |
| `ollama_chat_service` | Ollama chat completions |
| `nse_securities_service` | NSE securities data |
| `options_service` | Options chain data |
| `digest_service` | Daily digest generation |
| `user_settings_service` | User preference persistence |
| `configuration_service` | App-level configuration management |
| `worker_config` | Background worker configuration helpers |

---

## 7. Key Conventions

### Stock Symbols
Indian stocks use Yahoo Finance / yfinance format:  
- **NSE**: `SYMBOL.NS` (e.g. `RELIANCE.NS`)  
- **BSE**: `SYMBOL.BO` (e.g. `RELIANCE.BO`)

### Templates
Reference static assets via `{{ url_for('static', filename=...) }}` — never hard-code `/static/` paths.

### Concurrency
Flask-SocketIO is configured with `async_mode='threading'` (not asyncio/eventlet/gevent).

### Security Headers
Set on every response via `@app.after_request set_security_headers`: `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`.

### Secret / Config
`SECRET_KEY` must come from the `SECRET_KEY` environment variable in production.  
Cookie flags (`REMEMBER_COOKIE_SECURE`, `SESSION_COOKIE_SECURE`) are controlled via the `COOKIE_SECURE` env var.

### CORS
Controlled via `CORS_ALLOWED_ORIGINS` env var (comma-separated). Defaults to same-origin only.

---

## 8. LLM / Model Support

| Agent | Config Key | Notes |
|-------|-----------|-------|
| Ollama (default) | `active_llm_agent=ollama` | Local, private, offline; default model `phi-mini` |
| Gemini | `active_llm_agent=gemini` | Google Gemini via `google-genai` |
| Copilot | `active_llm_agent=copilot` | GitHub Models via OpenAI-compatible client |

Active agent is stored in `system_settings` DB table and read at startup via `SystemSettingsService.get_setting('active_llm_agent', 'ollama')`.

---

## 9. Testing

```bash
# All tests
python -m pytest tests/ -q

# By category
python -m pytest tests/api -q        # backend API route tests
python -m pytest tests/agents -q     # evaluative agent unit tests
python -m pytest tests/ui -q         # UI endpoint smoke tests
python -m pytest tests/integration -q
```

Key fixture: `conftest.py` provides a `_FakeSessionManager` and a temp SQLite DB auto-used across all tests.

---

## 10. Agent Guardrails (summary from `Agent.md`)

1. **Small, scoped changes** — no broad refactors unless explicitly requested.
2. **Preserve API contracts** — paths, response keys, and status codes must not change without approval.
3. **No hardcoded secrets or credentials.**
4. **Leakage prevention** — time-aware splits; no random shuffle for time-series; fit scalers on train only.
5. **Reproducibility** — deterministic seeds, pinned data ranges, versioned artifacts.
6. **Backtesting** — walk-forward validation; realistic assumptions (latency, fees, slippage).
7. **Metrics** — report MAE, RMSE, directional accuracy, Sharpe/Sortino, max drawdown, sample size, and evaluation horizon.
8. **Deployment** — go/no-go checklist: metrics met, leakage checks passed, backtest complete, data quality green.

See `Agent.md` for the full handoff template and detailed guardrails.

---

## 11. Quick Reference — Start the App

```bash
# Install dependencies
pip install -r requirements.txt

# Start Ollama (required for local LLM)
ollama serve
ollama pull phi-mini

# Run StockSense
python -m app.main
# → http://localhost:5005
```

Docker:
```bash
docker-compose up
```
