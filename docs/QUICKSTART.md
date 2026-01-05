# Quick Start Guide

## Running the Scanner

### 1. CLI Mode (Command Line)

```bash
# Basic scan
python -m scanner.modes.cli

# Scan specific symbols
python -m scanner.modes.cli --symbols AAPL,MSFT,GOOGL

# With debug logging
python -m scanner.modes.cli --debug

# Export results
python -m scanner.modes.cli --export csv
```

### 2. Web UI Mode (Streamlit)

```bash
# Option 1: Use helper script (recommended)
./start_ui.sh

# Option 2: Manual with PYTHONPATH
PYTHONPATH=. streamlit run scanner/modes/ui_app.py

# Option 3: Using Python module
python run_ui.py
```

Then open **http://localhost:8501** in your browser.

---

## Actionable Filter

The scanner has a **two-stage filtering system**:

### Stage 1: Scanner
- Finds momentum signals based on technical indicators
- Applies base quality filters
- **Result:** ~8-14 signals from 96 stocks

### Stage 2: Actionable Filter (Optional)
- Applies stricter safety rules
- Calculates position sizing
- Shows rejection reasons
- **Result:** ~2-6 actionable trades with exact share counts

### Enable/Disable Actionable Filter

**In config.json:**
```json
{
  "actionable": {
    "enabled": true   // ← Set to false to disable
  }
}
```

**In Streamlit UI:**
- Check/uncheck "Enable Actionable Filter" in sidebar
- Adjust parameters with sliders

---

## Configuration Examples

### Conservative Trading (Low Risk)
Edit `config.json`:
```json
{
  "actionable": {
    "enabled": true,
    "risk": {
      "account_size": 10000,
      "risk_percent_per_trade": 0.5    // Only 0.5% risk per trade
    },
    "technical": {
      "min_rr": 3.0,                    // Higher R/R requirement
      "min_volume_ratio": 1.5,          // Higher volume requirement
      "require_rsi_slope_non_negative": true
    }
  }
}
```

### Aggressive Trading (More Signals)
```json
{
  "actionable": {
    "enabled": true,
    "risk": {
      "risk_percent_per_trade": 2.0    // Higher risk per trade
    },
    "technical": {
      "min_rr": 1.5,                    // Lower R/R threshold
      "min_volume_ratio": 1.0,          // Lower volume requirement
      "require_rsi_slope_non_negative": false  // Allow falling RSI
    }
  }
}
```

### Scanner Only (No Position Sizing)
```json
{
  "actionable": {
    "enabled": false   // Disable actionable filter entirely
  }
}
```

---

## Understanding the Output

### CLI Output (With Actionable Filter)

```
📈 MOMENTUM SCANNER RESULTS
Mode: Momentum | Scan Time: 2025-10-16 08:28:35 UTC
Scanned: 96 symbols | Found: 8 signals
✅ Actionable: 2 trades | Avg R/R: 2.7

#  Symbol  Price    Score  RSI   Vol      MACD       Stop         Target      R/R  Size  Risk$  Reward$  Notes
1  WFC     $86.46   98     56↑   1.5×20d  ↑+2bars    $84.28(1.0×  $92.51(+7%) 2.8  45    $100   $272     🔥 High score, RSI rising
2  BLK     $1202.59 93     62↑   1.6×20d  ↑+2bars    $1171.66(1.  $1286.77(+  2.7  3     $100   $253     🔥 High score, RSI rising

Total Risk: $200 | Total Potential Reward: $525 | Avg R/R: 2.7

❌ REJECTED SIGNALS (6)
  AVGO  - R/R 1.7 < 2.0, RSI slope ↓ (falling), Volume 1.0× < 1.2× and not rising 3d
  CSCO  - Volume 0.8× < 1.2× and not rising 3d
  ...
```

**Key Columns:**
- **Symbol:** Stock ticker
- **Score:** Composite momentum score (0-100)
- **RSI:** RSI value with slope indicator (↑/↓/→)
- **Vol:** Volume ratio vs 20-day average
- **MACD:** Histogram status
- **Size:** Number of shares to buy
- **Risk$:** Dollar amount at risk (based on account size × risk %)
- **Reward$:** Potential dollar profit if target hit
- **Notes:** Why this trade is good

### Web UI (Streamlit)

**Metrics Row:**
- Symbols Scanned
- Signals Found
- ✅ Actionable (number of actionable trades)
- Avg R/R
- Total Risk

**Tabs:**
1. **✅ Actionable Trades:** Shows only trades that passed all filters with position sizing
2. **❌ Rejected:** Shows signals that failed actionable filter with reasons

---

## Troubleshooting

### "No signals found"
- Try lowering `score_threshold` in config (e.g., from 60 to 50)
- Check if `actionable.enabled = true` - disable it to see all scanner signals
- Market might be in pullback - this is normal

### "No actionable trades" (but signals found)
- Actionable filter is stricter - this is expected
- Try lowering `min_rr` from 2.0 to 1.5
- Try lowering `min_volume_ratio` from 1.2 to 1.0
- Set `require_rsi_slope_non_negative = false`

### "ModuleNotFoundError: No module named 'scanner'"
For Streamlit UI, use:
```bash
PYTHONPATH=. streamlit run scanner/modes/ui_app.py
```
Or use the helper script:
```bash
./start_ui.sh
```

### API Rate Limits
- Scanner uses batch API (2-3 calls for 96 symbols)
- Alpaca free tier: 200 requests/minute
- You're well within limits

---

## What's Next?

1. **Review Results:** Check which signals passed actionable filter
2. **Tune Parameters:** Adjust R/R, volume, risk % based on your style
3. **Export Data:** Use `--export csv` or export from UI
4. **Schedule Scans:** Set up worker mode for daily scans
5. **Telegram Alerts:** Configure notifications (optional)

See [ACTIONABLE_IMPLEMENTATION.md](ACTIONABLE_IMPLEMENTATION.md) for technical details.
