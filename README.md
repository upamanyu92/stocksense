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

## 📖 Documentation

- **`OLLAMA.md`** - Ollama setup, configuration, troubleshooting
- **`README.md`** - This file

---

## 🐳 Docker Deployment

```bash
docker-compose up
```

---

## 📊 API Endpoints

### Predictions
- `POST /api/predictions` - Make stock prediction
- `GET /api/predictions` - List predictions

### Stock Data
- `GET /api/stocks` - Get stock information
