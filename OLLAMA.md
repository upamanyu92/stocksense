# Ollama Integration - Getting Started

## What Changed

Your StockSense app now uses **Ollama + phi-mini** (local AI) instead of Google Gemini API.

| Feature | Before (Gemini) | After (Ollama) |
|---------|---|---|
| **Cost** | $$$ per call | FREE |
| **Privacy** | Data to Google | 100% Local |
| **Internet** | Required | Not needed |
| **Setup** | API key | Just download |
| **Speed** | Network dependent | 10-30 sec |

---

## 5-Minute Setup

### Terminal 1: Start Ollama
```bash
ollama serve
```

### Terminal 2: Get Model
```bash
ollama pull phi-mini
```

### Terminal 3: Run App
```bash
cd /Users/commandcenter/pycharmprojects/stocksense

# Create .env
cat > .env << 'EOF'
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL_NAME=phi-mini
FLASK_PORT=5005
DEBUG=False
EOF

# Test
python test_ollama_integration.py

# Run
python -m app.main
```

**Open**: http://localhost:5005

---

## Configuration Options

```bash
# Required (defaults provided)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL_NAME=phi-mini

# Optional (defaults shown)
OLLAMA_TEMPERATURE=0.7          # Response creativity (0-1)
OLLAMA_TOP_P=0.9
OLLAMA_TOP_K=40
OLLAMA_NUM_PREDICT=500          # Max tokens
OLLAMA_MIN_CONFIDENCE=0.5
OLLAMA_HIGH_CONFIDENCE_THRESHOLD=0.8
OLLAMA_MAX_RETRIES=3
OLLAMA_RETRY_DELAY=2

# Application
FLASK_PORT=5005
DEBUG=False
```

---

## Testing

```bash
# Run full test
python test_ollama_integration.py

# Quick checks
curl http://localhost:11434/api/tags
ollama list
```

---

## Switch Models

```bash
ollama pull mistral
# Update .env: OLLAMA_MODEL_NAME=mistral
```

Available: phi-mini (default) → phi2 → neural-chat → mistral → llama2

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Cannot connect | Run `ollama serve` |
| Model not found | Run `ollama pull phi-mini` |
| Slow | Normal for first request |
| High memory | Close other apps |

---

## System Requirements

- **RAM**: 4GB min (8GB recommended)
- **Disk**: 3GB
- **CPU**: Any modern processor
- **Internet**: Not needed

---

## Files Modified

**Created**: `app/config/ollama_config.py`, `app/models/ollama_model.py`

**Updated**: `requirements.txt`, `app/config_settings.py`, `app/main.py`, `app/services/prediction_service.py`, `app/services/llm_advisor.py`

**Unchanged**: All APIs, database, frontend

---

## Resources

- Ollama: https://ollama.ai
- Models: https://ollama.ai/library
- GitHub: https://github.com/ollama/ollama

