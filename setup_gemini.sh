#!/bin/bash
# Setup script for Gemini AI integration in StockSense

set -e

echo "=========================================="
echo "StockSense - Gemini AI Integration Setup"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✓ Python $PYTHON_VERSION found"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "✓ .env file created. Please edit it with your API key."
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and set your GEMINI_API_KEY before running the app"
    echo "   Get your API key from: https://aistudio.google.com/app/apikey"
    echo ""
else
    echo "✓ .env file already exists"
fi

# Check if .env has API key set
if grep -q "GEMINI_API_KEY=your_google_generativeai_api_key_here" .env; then
    echo "⚠️  WARNING: GEMINI_API_KEY in .env is not configured!"
    echo "   Please edit .env and set GEMINI_API_KEY"
    echo ""
fi

# Update .gitignore
if ! grep -q "^\.env$" .gitignore 2>/dev/null; then
    echo "📝 Adding .env to .gitignore..."
    echo ".env" >> .gitignore
    echo "✓ .gitignore updated"
else
    echo "✓ .env already in .gitignore"
fi

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Verify key packages
echo ""
echo "🔍 Verifying Gemini AI packages..."

python3 << EOF
try:
    import google.generativeai as genai
    print(f"✓ google-generativeai installed")
except ImportError:
    print("❌ google-generativeai not installed")
    exit(1)

try:
    import dotenv
    print(f"✓ python-dotenv installed")
except ImportError:
    print("❌ python-dotenv not installed")
    exit(1)

try:
    import flask
    print(f"✓ Flask installed")
except ImportError:
    print("❌ Flask not installed")
    exit(1)

try:
    import yfinance
    print(f"✓ yfinance installed")
except ImportError:
    print("❌ yfinance not installed")
    exit(1)

print("")
print("All dependencies verified!")
EOF

echo ""
echo "=========================================="
echo "✓ Setup completed successfully!"
echo "=========================================="
echo ""
echo "📋 Next steps:"
echo "1. Edit .env and set GEMINI_API_KEY"
echo "   Get your key from: https://aistudio.google.com/app/apikey"
echo ""
echo "2. Start the application:"
echo "   python -m app.main"
echo ""
echo "3. Access the dashboard:"
echo "   http://localhost:5005"
echo ""
echo "📖 For more information, see GEMINI_INTEGRATION.md"
echo ""

