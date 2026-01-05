# Momentum Stock Scanner

High-performance momentum scanner for US stocks using technical analysis and batch API optimization.

## Features

- 📊 **Technical Analysis**: RSI, EMA, MACD, Volume, ADX-based momentum scoring
- 🚀 **Batch API**: Scans 96 symbols in 2-3 API calls (97% reduction)
- ⚡ **Fast**: Complete scan in ~3 seconds
- 🎯 **Risk Management**: ATR-based stops, profit targets, R/R ratios
- ✅ **Actionable Filter**: Second-stage filtering with position sizing
- 📈 **Multiple Interfaces**: CLI, Web UI (Streamlit), Scheduled scans
- 🔔 **Alerts**: Telegram notifications (optional)

## Quick Start

### 1. Prerequisites
- Python 3.10 or higher
- Free Alpaca API account (recommended) - [Sign up here](https://alpaca.markets)
- Git

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/awaistechnologist/momentum-scanner-py.git
cd share-tracker

# Run the setup script (creates venv, installs dependencies)
./setup.sh
```

The setup script will:
- Create a virtual environment
- Install all dependencies
- Create `.env` and `config.json` from examples
- Set up output directories

### 3. Configure API Keys

**Important:** You MUST configure your API keys before running the scanner.

#### Option A: Using .env file (Recommended)
1. Open `.env` in your text editor
2. Replace placeholder values with your actual API keys:

```bash
# Get free API key from https://alpaca.markets
ALPACA_API_KEY=your_actual_alpaca_key_here
ALPACA_API_SECRET=your_actual_alpaca_secret_here

# Optional: Additional providers
ALPHAVANTAGE_API_KEY=your_key_here  # https://www.alphavantage.co
FINNHUB_API_KEY=your_key_here       # https://finnhub.io
TWELVEDATA_API_KEY=your_key_here    # https://twelvedata.com
```

#### Option B: Using config.json
Alternatively, you can configure in `config.json`:
```json
{
  "data": {
    "provider": "alpaca",
    "api_key": "your_actual_key",
    "api_secret": "your_actual_secret"
  }
}
```

**🔐 Security Note:** Never commit `.env` or `config.json` files to git. They are already in `.gitignore`.

### 4. Run Your First Scan

```bash
# Activate virtual environment
source venv/bin/activate

# Run CLI scanner
python -m scanner.modes.cli
```

**Expected Output:**
```
📡 Fetching data for 96 symbols in 1 API call...
✅ Scan complete: 14 signals found in 3 seconds

#  Symbol  Price    Score  Entry    Stop     Target   R/R
1  GILD    $117.18  87.5   $117.18  $113.99  $125.38  2.6
2  COIN    $357.01  79.6   $357.01  $338.93  $382.00  1.4
...
```

## Usage Modes

### CLI (Quick Scan)
```bash
python -m scanner.modes.cli
```

### Web UI (Streamlit)
```bash
# Option 1: Use helper script
# Option 1: Use convenience script (auto-activates venv)
./run.sh

# Option 2: Manual
source venv/bin/activate
python scripts/run_ui.py
# Option 2: Manual
PYTHONPATH=. streamlit run scanner/modes/ui_app.py

# Then open http://localhost:8501 in your browser
```

### Scheduled Scans
```bash
python -m scanner.modes.worker
```

## Configuration

Edit `config.json`:
```json
{
  "universe": {
    "lists": ["US_LIQUID_TECH", "US_BLUE_CHIP", "US_GROWTH"],
    "custom_symbols": []
  },
  "strategy": {
    "score_threshold": 60,
    "top_n": 15
  }
}
```

### Available Universes
- `US_LIQUID_TECH` - Tech stocks (24 symbols)
- `US_BLUE_CHIP` - Blue chips (20 symbols)
- `US_GROWTH` - Growth stocks (20 symbols)
- `US_FINANCIAL` - Financials (10 symbols)
- `US_HEALTHCARE` - Healthcare (22 symbols)

## Strategy

### Entry Signals
- ✅ Price > 50-day SMA (uptrend)
- ✅ 9-EMA > 21-EMA (momentum)
- ✅ RSI 50-65 (not overbought)
- ✅ MACD bullish crossover
- ✅ Volume > 20-day average
- ✅ ADX confirming trend

### Scoring (0-100)
- EMA: 25%
- RSI: 20%
- MACD: 25%
- Volume: 20%
- Breakout: 10%

**Threshold:** Signals with score > 60

### Risk Management
- **Stop Loss**: ATR-based (dynamic)
- **Take Profit**: 7% target
- **Risk/Reward**: Minimum 1.5:1

## Performance

**Current (Optimized):**
- 96 symbols scanned in ~3 seconds
- 2-3 API calls total (batch requests)
- 97% reduction in API usage
- Zero rate limit issues

## Getting API Keys

### Alpaca (Recommended - Free)
1. Go to [https://alpaca.markets](https://alpaca.markets)
2. Sign up for a free account (no credit card required)
3. Navigate to "Your API Keys" in the dashboard
4. Copy your API Key and Secret Key
5. Paste them into `.env` file

**Free tier includes:**
- 200 requests/minute
- Real-time & historical data
- US stocks
- Batch API (100 symbols/call)

### Alternative Providers (Optional)

#### Alpha Vantage
- Free tier: 25 API calls/day
- Sign up: [https://www.alphavantage.co/support/#api-key](https://www.alphavantage.co/support/#api-key)

#### Finnhub
- Free tier: 60 API calls/minute
- Sign up: [https://finnhub.io](https://finnhub.io)

#### Twelve Data
- Free tier: 8 API calls/minute
- Sign up: [https://twelvedata.com](https://twelvedata.com)

## Documentation

- **[Publishing Guide](docs/PUBLISH.md)** - How to safely publish to GitHub
- **[Quick Start](docs/QUICKSTART.md)** - Installation & basic usage
- **[UI Guide](docs/UI_GUIDE.md)** - Streamlit web interface guide

## Data Providers

**Primary:** Alpaca Markets (batch API)
- 200 requests/minute (free tier)
- US stocks only
- Split-adjusted data
- Batch support (100 symbols/call)

**Backups:** AlphaVantage, Finnhub, TwelveData (available)

## Requirements

- Python 3.13+
- Alpaca API account (free)
- See `requirements.txt` for dependencies

## File Structure

```
share-tracker/
├── .env                    # API keys
├── config.json             # Scanner configuration
├── README.md               # This file
├── docs/                   # Documentation
│   ├── QUICKSTART.md
│   ├── ARCHITECTURE.md
│   └── PROVIDERS.md
├── scanner/
│   ├── core/              # Core engine
│   ├── modes/             # CLI, UI, Worker
│   ├── config/            # Configuration
│   └── integrations/      # Exports, alerts
└── test_installation.py   # Installation test
```

## Testing

```bash
source venv/bin/activate
python scripts/test_installation.py
```

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Important:** Never commit API keys or sensitive data. See [SECURITY.md](SECURITY.md) for details.

## Security

See [SECURITY.md](SECURITY.md) for important security guidelines about protecting your API keys.

## License

MIT - See [LICENSE](LICENSE) for details

## Support

- 📖 [Documentation](docs/)
- 🐛 [Report Issues](https://github.com/YOUR_USERNAME/share-tracker/issues)
- 💬 [Discussions](https://github.com/YOUR_USERNAME/share-tracker/discussions)

## Disclaimer

This tool is for educational and informational purposes only. It is not financial advice. Always do your own research before making investment decisions. Past performance does not guarantee future results.

---

**Built with:** Python, Alpaca API, Pandas, TA-Lib, Streamlit

**⭐ If you find this useful, please star the repository!**
