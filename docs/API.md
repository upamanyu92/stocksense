# Agentic Prediction System API

REST API endpoints for the agentic prediction system.

## Base URL

All endpoints are prefixed with: `/api/agentic`

## Endpoints

### 1. Make Prediction

**Endpoint:** `GET /api/agentic/predict/<symbol>`

**Description:** Make an intelligent prediction for a stock symbol using the multi-agent system.

**Parameters:**
- `symbol` (path): Stock symbol (e.g., 'AAPL', 'MSFT')
- `validate` (query, optional): Whether to validate prediction (default: true)
- `min_confidence` (query, optional): Minimum confidence threshold 0-1 (default: 0.6)

**Example Request:**
```bash
curl "http://localhost:5000/api/agentic/predict/AAPL?validate=true&min_confidence=0.6"
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "symbol": "AAPL",
    "prediction": 175.50,
    "confidence": 0.78,
    "base_confidence": 0.75,
    "confidence_adjustment": 0.03,
    "prediction_interval": [173.20, 177.80],
    "uncertainty": 2.30,
    "data_quality": 0.95,
    "market_regime": "bull",
    "decision": "accept",
    "recommendation": "High confidence prediction (confidence: 0.78). Recommended for use.",
    "agents_used": [
      "DataEnrichmentAgent",
      "AdaptiveLearningAgent",
      "EnsembleAgent"
    ],
    "model_details": [
      {
        "model_type": "transformer",
        "prediction": 176.20,
        "confidence": 0.80
      },
      {
        "model_type": "lstm",
        "prediction": 174.80,
        "confidence": 0.70
      }
    ],
    "adaptive_weights": {
      "transformer": 0.55,
      "lstm": 0.45
    },
    "processing_time": 2.45,
    "timestamp": "2025-10-11T17:30:00Z"
  }
}
```

### 2. Provide Feedback

**Endpoint:** `POST /api/agentic/feedback`

**Description:** Provide actual results for adaptive learning.

**Request Body:**
```json
{
  "symbol": "AAPL",
  "predicted": 175.50,
  "actual": 177.25
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:5000/api/agentic/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "predicted": 175.50,
    "actual": 177.25
  }'
```

**Example Response:**
```json
{
  "success": true,
  "message": "Feedback received and processed"
}
```

### 3. Performance Report

**Endpoint:** `GET /api/agentic/performance`

**Description:** Get comprehensive performance metrics for the agentic system.

**Example Request:**
```bash
curl "http://localhost:5000/api/agentic/performance"
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "metrics": {
      "total_predictions": 42,
      "high_confidence_predictions": 28,
      "validated_predictions": 38,
      "average_confidence": 0.73
    },
    "agent_performance": {
      "data_enrichment_agent": {
        "accuracy": 0.85,
        "predictions_made": 42
      },
      "ensemble_agent": {
        "accuracy": 0.82,
        "predictions_made": 42
      },
      "adaptive_learning_agent": {
        "accuracy": 0.88,
        "learning_report": {
          "model_performance": {
            "transformer": {
              "weight": 0.55,
              "avg_error": 0.03
            },
            "lstm": {
              "weight": 0.45,
              "avg_error": 0.04
            }
          }
        }
      }
    },
    "recent_decisions": [
      {
        "timestamp": "2025-10-11T17:30:00Z",
        "symbol": "AAPL",
        "prediction": 175.50,
        "confidence": 0.78,
        "decision": "accept"
      }
    ]
  }
}
```

### 4. Health Check

**Endpoint:** `GET /api/agentic/health`

**Description:** Check system health and status.

**Example Request:**
```bash
curl "http://localhost:5000/api/agentic/health"
```

**Example Response:**
```json
{
  "success": true,
  "status": "healthy",
  "metrics": {
    "total_predictions": 42,
    "average_confidence": 0.73,
    "agents_initialized": true
  }
}
```

## Decision Values

The `decision` field in predictions can have the following values:

- **accept**: High confidence (>75% trust score) - Recommended for use
- **caution**: Moderate confidence (60-75% trust score) - Use with care
- **reject**: Low confidence (<60% trust score) - Not recommended

## Market Regimes

The `market_regime` field indicates the detected market condition:

- **bull**: Upward trending market
- **bear**: Downward trending market
- **sideways**: Range-bound market
- **volatile**: High volatility market

## Error Responses

All endpoints return standard error responses:

```json
{
  "success": false,
  "error": "Error description"
}
```

HTTP Status Codes:
- `200`: Success
- `400`: Bad request (missing/invalid parameters)
- `500`: Internal server error

## Integration

To integrate the API into your Flask app:

```python
from app.api.agentic_routes import register_agentic_api

app = Flask(__name__)
register_agentic_api(app)
```

## Rate Limiting

Consider implementing rate limiting for production use to prevent abuse and manage computational resources.

## Authentication

In production, add authentication middleware to secure these endpoints.
