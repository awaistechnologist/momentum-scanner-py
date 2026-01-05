# Architecture & Design

## System Overview

```
┌─────────────┐
│   Config    │ → Universe, Strategy, Risk params
└─────────────┘
       ↓
┌─────────────────────────────────────────┐
│           Scanner Engine                │
│                                         │
│  ┌──────────────┐   ┌───────────────┐  │
│  │ Data Provider│───│ Batch API     │  │
│  │ (Alpaca)     │   │ (96 symbols   │  │
│  └──────────────┘   │  in 1-3 calls)│  │
│                     └───────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │   Technical Analysis Engine      │  │
│  │   - RSI, EMA, MACD, Volume, ADX  │  │
│  │   - Momentum scoring (0-100)     │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │   Risk Management                │  │
│  │   - ATR-based stops & targets    │  │
│  │   - Risk/Reward calculation      │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────┐
│           Output & Export               │
│   - CLI results                         │
│   - Web UI (Streamlit)                  │
│   - CSV/JSON export                     │
│   - Telegram alerts                     │
└─────────────────────────────────────────┘
```

## Core Components

### 1. Data Layer
- **Provider**: Alpaca Markets (batch API)
- **Backups**: AlphaVantage, Finnhub, TwelveData
- **Optimization**: Batch requests (1 call for ~100 symbols)
- **Coverage**: US stocks, 200-day history

### 2. Strategy Layer
- **Type**: Momentum-based scoring
- **Indicators**: RSI, EMA (9/21), MACD, Volume, ADX
- **Weights**:
  - EMA: 25%
  - RSI: 20%
  - MACD: 25%
  - Volume: 20%
  - Breakout: 10%
- **Threshold**: Score > 60

### 3. Risk Layer
- **Stop Loss**: ATR-based (1.0x multiplier)
- **Take Profit**: 7% fixed or dynamic
- **Entry**: Current price or pullback
- **R/R**: Minimum 1.5:1

## Data Flow

1. **Initialization**
   - Load config from `config.json`
   - Initialize Alpaca provider with API keys
   - Load universe symbols

2. **Data Fetch** (Optimized)
   ```python
   # Batch request - 96 symbols in 1 API call
   bars_dict = provider.get_bars_batch(symbols, interval='1d', lookback=200)
   # Returns: {symbol: [bars]}
   ```

3. **Analysis** (Per Symbol)
   ```python
   for symbol, bars in bars_dict.items():
       indicators = calculate_indicators(bars)
       score = calculate_score(indicators, weights)
       if score > threshold:
           signal = generate_signal(symbol, indicators, score)
   ```

4. **Risk Management**
   ```python
   atr = calculate_atr(bars)
   stop_loss = current_price - (atr * multiplier)
   take_profit = current_price * 1.07  # 7%
   risk_reward = (take_profit - current_price) / (current_price - stop_loss)
   ```

5. **Output**
   - Rank signals by score
   - Export top N (default: 15)
   - Send notifications (optional)

## File Structure

```
scanner/
├── core/
│   ├── data_providers/
│   │   ├── base.py              # Abstract provider interface
│   │   ├── alpaca.py            # Alpaca (batch API) ✅
│   │   ├── alphavantage.py      # Backup
│   │   ├── finnhub.py           # Backup
│   │   └── twelvedata.py        # Backup
│   ├── models.py                # Data models (Bar, Quote, Signal)
│   ├── indicators.py            # Technical indicators
│   ├── strategy.py              # Momentum strategy logic
│   ├── scanner.py               # Main scanner engine
│   ├── ranking.py               # Signal ranking
│   └── utils.py                 # Utilities
├── config/
│   ├── __init__.py              # Config management
│   └── universes.py             # Pre-defined stock lists
├── modes/
│   ├── cli.py                   # CLI interface
│   ├── ui_app.py                # Web UI (Streamlit)
│   └── worker.py                # Scheduled scanner
└── integrations/
    ├── telegram.py              # Telegram alerts
    └── export.py                # CSV/JSON export
```

## Optimization Details

### Batch API (Key Innovation)
**Before:** 1 API call per symbol
```python
for symbol in symbols:
    bars = provider.get_bars(symbol)  # 96 calls
```

**After:** 1 API call for all symbols
```python
bars_dict = provider.get_bars_batch(symbols)  # 1-3 calls (with pagination)
```

**Result:** 97% reduction in API calls

### Performance Metrics
- **96 symbols**: 2-3 API calls, ~3 seconds
- **500 symbols**: 5-10 API calls, ~10 seconds
- **Rate limit**: 200/min (Alpaca) - plenty of headroom

## Strategy Principles

### Entry Conditions
- Price > 50-day SMA (uptrend)
- 9-EMA > 21-EMA (momentum)
- RSI 50-65 (not overbought)
- MACD > Signal (bullish)
- Volume > 20-day average (confirmation)
- ADX > 0 (trend strength)

### Scoring System
Each indicator contributes to final score (0-100):
- **EMA crossover**: 25 points max
- **RSI position**: 20 points max
- **MACD strength**: 25 points max
- **Volume surge**: 20 points max
- **Breakout proximity**: 10 points max

**Threshold**: Signals with score > 60 are flagged

### Risk Management
- **ATR-based stops**: Dynamic based on volatility
- **Fixed targets**: 7% profit target
- **R/R filter**: Minimum 1.5:1 risk/reward
- **Position sizing**: Not implemented (user discretion)

## Extensibility

### Adding New Provider
1. Create `scanner/core/data_providers/newprovider.py`
2. Inherit from `MarketDataProvider`
3. Implement: `get_bars()`, `get_quote()`, `get_meta()`
4. Add to `scanner.py` provider initialization

### Adding New Indicator
1. Add calculation to `scanner/core/indicators.py`
2. Update `strategy.py` to use indicator
3. Adjust weights in config

### Adding New Universe
Edit `scanner/config/universes.py`:
```python
MY_CUSTOM_LIST = [
    "SYMBOL1",
    "SYMBOL2",
    ...
]

UNIVERSE_LISTS["MY_CUSTOM_LIST"] = MY_CUSTOM_LIST
```

## Configuration Reference

See `config.json` for all options:
- **universe**: Stock lists and custom symbols
- **data**: Provider, interval, lookback
- **strategy**: Indicators, weights, thresholds
- **risk**: ATR, stop loss, take profit
- **notifications**: Telegram alerts
- **export**: Output paths
- **scheduler**: Automated scans
