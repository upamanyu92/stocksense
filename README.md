# StockSense - AI-Powered Stock Prediction

A comprehensive stock prediction platform with intelligent analysis, real-time updates, and automated monitoring.

---

## ⚡ Quick Start

### For Ollama Integration (Recommended)
👉 **See**: `OLLAMA.md` for setup and configuration

### For Production Deployment
```bash
docker-compose up
```

---

## 🎯 Core Features

- 🤖 **AI Predictions** - Local Ollama + phi-mini model (free, private, offline)
- 📊 **Real-time Analytics** - Live WebSocket updates
- 📈 **Advanced ML** - Ensemble prediction models
- 🧠 **Adaptive Learning** - Self-improving from errors
- 🧪 **Evaluative Agents** - Deterministic pre-serve and post-outcome scoring for forecast quality
- 🔔 **Smart Alerts** - Automated notifications
- 📱 **Responsive UI** - Mobile, tablet, desktop
- 🐳 **Docker Ready** - Production deployment

---

## 📦 What's Inside

- **`app/`** - Flask application
- **`app/models/`** - ML prediction models
- **`app/config/`** - Configuration
- **`app/services/`** - Business logic
- **`app/api/`** - REST API endpoints
- **`db/`** - Database schema
- **`tests/`** - Test suites

---

## 🔧 Setup

### Prerequisites
- Python 3.8+
- Ollama (for local AI predictions)
- SQLite (included)

### Installation

1. **Clone repository**
   ```bash
   git clone <repo>
   cd stocksense
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup Ollama** (see `OLLAMA.md`)
   ```bash
   ollama serve
   ollama pull phi-mini
   ```

4. **Run application**
   ```bash
   python -m app.main
   ```

Access: http://localhost:5005

---

## 🤖 Evaluative Agents

The agentic prediction pipeline now includes two deterministic evaluator stages:

- **`PredictionEvaluatorAgent`** - scores prediction quality before a forecast is served
- **`OutcomeEvaluatorAgent`** - scores realized prediction quality after actual prices arrive

Agentic prediction responses now include:

- `evaluation.score` / `evaluation.score_pct`
- `evaluation.action` (`proceed`, `proceed_with_caution`, `shadow_only`, `block_prediction`)
- `serving_action` for the final delivery gate
- post-feedback outcome evaluation data from `POST /api/agentic/feedback`

---

## 📖 Documentation

- **`OLLAMA.md`** - Ollama setup, configuration, troubleshooting
- **`README.md`** - This file

---

## 🐳 Docker Deployment

```bash
docker-compose up
```

### Docker Build With Mandatory Tests

Use the pre-build script to run backend API, UI endpoint, and integration tests before image build:

```bash
chmod +x scripts/docker_build_with_tests.sh
./scripts/docker_build_with_tests.sh
```

---

## ✅ Testing

Run all new endpoint and integration tests:

```bash
python -m pytest tests/api tests/ui tests/integration -q
```

Run only backend API tests:

```bash
python -m pytest tests/api -q
```

Run only UI endpoint tests:

```bash
python -m pytest tests/ui -q
```

Run only integration tests:

```bash
python -m pytest tests/integration -q
```

### Makefile Shortcuts

```bash
make test
make test-api
make test-ui
make test-integration
make docker-build
make docker-up
make docker-down
```

---

## 📊 API Endpoints

### Predictions
- `POST /api/predictions` - Make stock prediction
- `GET /api/predictions` - List predictions

### Agentic Predictions
- `GET /api/agentic/predict/<symbol>` - Run agentic prediction with evaluation metadata
- `POST /api/agentic/feedback` - Submit actual prices and receive outcome evaluation
- `GET /api/agentic/performance` - Get coordinator, evaluator, and learning metrics
- `GET /api/agentic/health` - Health status for the agentic subsystem

### Stock Data
- `GET /api/stocks` - Get stock information
