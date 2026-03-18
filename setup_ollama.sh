#!/bin/bash
# Setup script for Ollama integration with StockSense

set -e

echo "=========================================="
echo "StockSense - Ollama Integration Setup"
echo "=========================================="
echo ""

# Check if Ollama is installed
echo "1. Checking Ollama installation..."
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed or not in PATH"
    echo "Please install from: https://ollama.ai"
    exit 1
fi
echo "✅ Ollama found"
echo ""

# Check if Ollama service is running
echo "2. Checking if Ollama service is running..."
if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "✅ Ollama service is running"
else
    echo "⚠️  Ollama service is not running"
    echo "Start it with: ollama serve"
    echo "Continue? (y/n)"
    read -r response
    if [ "$response" != "y" ]; then
        exit 1
    fi
fi
echo ""

# Check if phi4-mini model is available
echo "3. Checking if phi4-mini model is available..."
if ollama list | grep -q "phi4-mini"; then
    echo "✅ phi4-mini model is installed"
else
    echo "⚠️  phi4-mini model not found. Installing..."
    ollama pull phi-mini
    echo "✅ phi4-mini model installed"
fi
echo ""

# Create .env file if it doesn't exist
echo "4. Setting up environment configuration..."
if [ ! -f .env ]; then
    echo "Creating .env file with Ollama configuration..."
    cat > .env << 'EOF'
# Ollama Local LLM Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL_NAME=phi4-mini
OLLAMA_TEMPERATURE=0.7
OLLAMA_TOP_P=0.9
OLLAMA_TOP_K=40
OLLAMA_NUM_PREDICT=500
OLLAMA_MIN_CONFIDENCE=0.5
OLLAMA_HIGH_CONFIDENCE_THRESHOLD=0.8
OLLAMA_MAX_RETRIES=3
OLLAMA_RETRY_DELAY=2

# Flask Configuration
FLASK_PORT=5005
DEBUG=False
SECRET_KEY=dev-secret-key-change-in-production
EOF
    echo "✅ .env file created"
else
    echo "✅ .env file already exists"
fi
echo ""

# Install Python dependencies
echo "5. Installing Python dependencies..."
pip install -r requirements.txt
echo "✅ Python dependencies installed"
echo ""

echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Make sure Ollama is running: ollama serve"
echo "2. Start StockSense: python -m app.main"
echo "3. Access the dashboard at: http://localhost:5005"
echo ""
echo "For more info, see OLLAMA_INTEGRATION.md"

