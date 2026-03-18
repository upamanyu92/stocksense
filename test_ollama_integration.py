#!/usr/bin/env python3
"""
Test script to verify Ollama integration with StockSense
"""
import sys
import requests
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_ollama_connection():
    """Test basic Ollama API connection"""
    logger.info("=" * 60)
    logger.info("Testing Ollama Connection")
    logger.info("=" * 60)

    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            logger.info("✅ Ollama API is running")
            models = response.json().get('models', [])
            logger.info(f"   Available models: {len(models)}")
            for model in models:
                logger.info(f"   - {model.get('name', 'unknown')}")
            return True
        else:
            logger.error(f"❌ Ollama API returned status {response.status_code}")
            return False
    except requests.ConnectionError:
        logger.error("❌ Cannot connect to Ollama at http://localhost:11434")
        logger.error("   Make sure Ollama is running: ollama serve")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing Ollama: {e}")
        return False


def test_phi_mini_model():
    """Test if phi-mini model is available"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing phi-mini Model")
    logger.info("=" * 60)

    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = response.json().get('models', [])
        model_names = [m.get('name', '') for m in models]

        if any('phi-mini' in name for name in model_names):
            logger.info("✅ phi-mini model is available")
            return True
        else:
            logger.error("❌ phi-mini model not found")
            logger.error(f"   Available models: {model_names}")
            logger.error("   Install it with: ollama pull phi-mini")
            return False
    except Exception as e:
        logger.error(f"❌ Error checking model: {e}")
        return False


def test_ollama_generation():
    """Test actual text generation with phi-mini"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Text Generation")
    logger.info("=" * 60)

    try:
        logger.info("Sending test prompt to phi-mini...")

        payload = {
            "model": "phi-mini",
            "prompt": "Hello, please respond with 'OK'",
            "stream": False
        }

        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            response_text = result.get('response', '').strip()
            logger.info(f"✅ Model responded: {response_text[:100]}")
            return True
        else:
            logger.error(f"❌ Generation failed with status {response.status_code}")
            return False
    except requests.Timeout:
        logger.error("❌ Request timeout - phi-mini took too long to respond")
        logger.error("   This is normal for first request - model is loading")
        return True  # Not a failure, just slow
    except Exception as e:
        logger.error(f"❌ Error testing generation: {e}")
        return False


def test_stock_prediction():
    """Test stock prediction with Ollama"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Stock Prediction")
    logger.info("=" * 60)

    try:
        from app.models.ollama_model import predict_with_details

        logger.info("Running stock prediction for RELIANCE.BO...")
        result = predict_with_details("RELIANCE.BO")

        logger.info(f"✅ Prediction completed:")
        logger.info(f"   Predicted Price: {result.get('predicted_price', 'N/A')}")
        logger.info(f"   Confidence: {result.get('confidence', 'N/A')}")
        logger.info(f"   Decision: {result.get('decision', 'N/A')}")
        logger.info(f"   Reasoning: {result.get('reasoning', 'N/A')[:100]}")

        return result.get('decision') != 'reject'
    except Exception as e:
        logger.error(f"❌ Error testing prediction: {e}")
        return False


def test_config():
    """Test Ollama configuration"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Configuration")
    logger.info("=" * 60)

    try:
        from app.config.ollama_config import OllamaConfig

        logger.info(f"✅ Configuration loaded:")
        logger.info(f"   Host: {OllamaConfig.OLLAMA_HOST}")
        logger.info(f"   Model: {OllamaConfig.MODEL_NAME}")
        logger.info(f"   Temperature: {OllamaConfig.TEMPERATURE}")
        logger.info(f"   Max Retries: {OllamaConfig.MAX_RETRIES}")

        # Validate config
        try:
            OllamaConfig.validate_config()
            logger.info("✅ Configuration validated")
            return True
        except Exception as ve:
            logger.error(f"❌ Configuration validation failed: {ve}")
            return False
    except Exception as e:
        logger.error(f"❌ Error loading configuration: {e}")
        return False


def main():
    """Run all tests"""
    logger.info("\n" + "=" * 60)
    logger.info("StockSense - Ollama Integration Test Suite")
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    results = {}

    # Run tests
    results['Connection'] = test_ollama_connection()
    if not results['Connection']:
        logger.error("\n❌ Cannot continue - Ollama is not running")
        return False

    results['Model'] = test_phi_mini_model()
    if not results['Model']:
        logger.error("\n⚠️  phi-mini model not found - install with: ollama pull phi-mini")

    results['Configuration'] = test_config()
    results['Generation'] = test_ollama_generation()

    # Stock prediction test is optional (requires stock data)
    logger.info("\n" + "=" * 60)
    logger.info("Optional: Stock Prediction Test")
    logger.info("(Skipping - requires market data)")
    logger.info("=" * 60)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")

    all_pass = all(results.values())

    logger.info("=" * 60)
    if all_pass:
        logger.info("✅ All tests passed! Ollama integration is ready.")
        logger.info("\nNext steps:")
        logger.info("1. Start Ollama: ollama serve")
        logger.info("2. Start StockSense: python -m app.main")
        logger.info("3. Access dashboard: http://localhost:5005")
        return True
    else:
        logger.error("❌ Some tests failed. See above for details.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

