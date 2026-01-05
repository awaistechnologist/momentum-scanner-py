#!/bin/bash
# Setup script for Momentum Scanner

set -e

echo "======================================"
echo "⏳ Kairos: Momentum Scanner Setup"
echo "======================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python 3.10 or higher required (found $python_version)"
    exit 1
fi
echo "✅ Python $python_version found"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "ℹ️  Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null
echo "✅ pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies..."
echo "This may take a few minutes..."
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Check TA-Lib
echo "Checking TA-Lib installation..."
if python -c "import talib" 2>/dev/null; then
    echo "✅ TA-Lib is installed"
else
    echo "⚠️  TA-Lib not found. The scanner will use pandas-based calculations."
    echo "   For better performance, install TA-Lib:"
    echo "   - macOS: brew install ta-lib"
    echo "   - Ubuntu/Debian: sudo apt-get install ta-lib-dev"
    echo "   Then run: pip install ta-lib"
fi
echo ""

# Create directories
echo "Creating output directories..."
mkdir -p output logs
echo "✅ Directories created"
echo ""

# Copy config example if config doesn't exist
if [ ! -f "config.json" ]; then
    echo "Creating config file..."
    cp scanner/config/config.example.json config.json
    echo "✅ config.json created from example"
    echo "   ⚠️  Edit config.json with your API keys before running"
else
    echo "ℹ️  config.json already exists"
fi
echo ""

# Copy .env example if .env doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "✅ .env created from example"
    echo "   ⚠️  Edit .env with your API keys (optional, can use config.json)"
else
    echo "ℹ️  .env already exists"
fi
echo ""

echo "======================================"
echo "✅ Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Edit your configuration:"
echo "   nano config.json"
echo ""
echo "2. Add your API keys (optional, free Yahoo Finance works without keys):"
echo "   - Get Finnhub key: https://finnhub.io"
echo "   - Get Twelve Data key: https://twelvedata.com"
echo ""
echo "3. Run your first scan:"
echo "   source venv/bin/activate"
echo "   python -m scanner.modes.cli --symbols AAPL,MSFT,GOOGL"
echo ""
echo "4. Or launch the UI:"
echo "   python scripts/run_ui.py"
echo ""
echo "5. Get help:"
echo "   python -m scanner.modes.cli --help"
echo ""
echo "Happy scanning! 📈"
