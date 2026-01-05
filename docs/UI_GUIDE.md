# Streamlit UI Guide

## Starting the UI

```bash
cd /Users/awaistahir/Documents/share-tracker
source venv/bin/activate
./start_ui.sh
```

Then open: **http://localhost:8501**

---

## Default Settings (Matches CLI)

When you open the UI, it will be pre-configured with:

### 🌍 Universe
**Pre-selected:**
- ✅ US_LIQUID_TECH (24 stocks)
- ✅ US_BLUE_CHIP (20 stocks)
- ✅ US_GROWTH (20 stocks)
- ✅ US_FINANCIAL (10 stocks)
- ✅ US_HEALTHCARE (22 stocks)

**Total: 96 US stocks**

### 📊 Data Provider
**Selected:** `alpaca` (recommended for US stocks)

**Available options:**
- alpaca - Best for US stocks (batch API, fast)
- alphavantage - Alternative (slower)
- finnhub - Alternative (supports international)
- twelvedata - Alternative (supports international)

### 📊 Strategy Parameters
- RSI Min: 50
- RSI Max: 65
- Score Threshold: 60
- Top N Results: 15

### ✅ Actionable Filter
**Enabled by default** with:
- Account Size: $10,000
- Risk % Per Trade: 1.0%
- Min R/R Ratio: 2.0
- Min Volume Ratio: 1.2
- ✅ Require RSI Rising/Flat (no ↓)

---

## How to Use

### 1. Quick Scan (Use Defaults)

Just click **🔍 Run Scan** in the sidebar!

The scanner will:
1. Fetch data for 96 US stocks (2-3 API calls)
2. Find momentum signals (8-14 typically)
3. Apply actionable filter (2-6 trades typically)
4. Show results with position sizing

### 2. Custom Universe

**Option A: Select different lists**
- Uncheck some lists to scan fewer stocks
- Example: Only scan US_LIQUID_TECH (24 stocks)

**Option B: Enter custom symbols**
```
AAPL, MSFT, GOOGL, NVDA, TSLA
```

### 3. Adjust Strategy

Use sliders in sidebar:
- **RSI Min/Max:** Widen range (e.g., 45-70) for more signals
- **Score Threshold:** Lower (e.g., 50) for more signals
- **Top N:** Increase to show more results

### 4. Tune Actionable Filter

**For more actionable trades:**
- Lower "Min R/R Ratio" to 1.5
- Lower "Min Volume Ratio" to 1.0
- Uncheck "Require RSI Rising/Flat"

**For higher quality (fewer trades):**
- Raise "Min R/R Ratio" to 3.0
- Raise "Min Volume Ratio" to 1.5
- Keep "Require RSI Rising/Flat" checked

**To disable position sizing:**
- Uncheck "Enable Actionable Filter"
- Will show all scanner signals without filtering

---

## Understanding the Results

### Metrics Row (with Actionable Filter)
```
Symbols Scanned: 96
Signals Found: 8
✅ Actionable: 2
Avg R/R: 2.7
Total Risk: $200
```

### Tab 1: ✅ Actionable Trades

Table shows:
| # | Symbol | Price | Score | RSI | Entry | Stop | Target | R/R | Size | Risk$ | Reward$ | Notes |
|---|--------|-------|-------|-----|-------|------|--------|-----|------|-------|---------|-------|
| 1 | WFC | $86.46 | 98 | 56↑ | $86.46 | $84.28 | $92.51 | 2.8 | 45 | $100 | $272 | 🔥 High score, RSI rising |

**Key Columns:**
- **Size:** Number of shares to buy (based on your risk %)
- **Risk$:** Dollar amount at risk ($10k × 1% = $100)
- **Reward$:** Potential profit if target hit
- **Notes:** Why this is a good trade

### Tab 2: ❌ Rejected

Shows signals that didn't pass actionable filter:

| Symbol | Rejection Reasons |
|--------|-------------------|
| CSCO | Volume 0.8× < 1.2× and not rising 3d |
| AVGO | R/R 1.7 < 2.0, RSI slope ↓ (falling) |

**Why This Matters:**
- Helps you understand why good signals were filtered out
- Helps you tune parameters if rejecting too many

---

## Signal Detail View

Below the table, select a signal to see:
- **Candlestick chart** with indicators
- **RSI chart** with 50/65 levels
- **MACD chart** with histogram
- **Volume chart** with 20-day average

---

## Export Options

Three buttons at bottom:

1. **📄 Export CSV** - Saves to `./output/scan_YYYYMMDD_HHMMSS.csv`
2. **📋 Export JSON** - Saves complete data to JSON
3. **📱 Send to Telegram** - Sends summary (if configured)

---

## Common Scenarios

### Scenario 1: No Actionable Trades

```
Signals Found: 8
✅ Actionable: 0
```

**What to do:**
- Click "❌ Rejected" tab to see why signals failed
- Lower "Min R/R Ratio" from 2.0 to 1.5
- Lower "Min Volume Ratio" from 1.2 to 1.0
- Or uncheck "Enable Actionable Filter" to see all signals

### Scenario 2: Too Many Trades

```
✅ Actionable: 12
Total Risk: $1,200
```

**What to do:**
- Raise "Min R/R Ratio" to 3.0
- Raise "Score Threshold" to 70
- Check "Require RSI Rising/Flat"
- Raise "Min Volume Ratio" to 1.5

### Scenario 3: No Signals at All

```
Signals Found: 0
```

**What to do:**
- Lower "Score Threshold" to 50
- Widen "RSI Min/Max" to 45-70
- Check if market is in pullback (this is normal)
- Try different universe (e.g., US_GROWTH only)

---

## Tips

### Speed
- Scanning 96 stocks takes 3-5 seconds (batch API)
- Scanning 10 stocks takes 1-2 seconds
- Charts load on-demand (might be slower)

### Configuration
- Changes in UI are temporary (not saved to config.json)
- To save settings, edit config.json manually
- Reload browser to reset to config.json defaults

### Best Practices
1. Start with defaults - click "Run Scan"
2. Review actionable trades in Tab 1
3. Check rejected signals in Tab 2
4. Adjust parameters based on rejections
5. Re-scan to see changes

### Keyboard Shortcuts
- `Ctrl+R` or `Cmd+R` - Reload page
- Use sliders for fine-tuning
- Type in number inputs for exact values

---

## Troubleshooting

### "No symbols selected"
- Make sure at least one universe list is checked
- Or enter custom symbols in text area

### "Scan failed: Alpaca API error"
- Check .env has ALPACA_API_KEY and ALPACA_API_SECRET
- Verify API keys are valid (not expired)

### "Module not found"
- Make sure you're in project directory
- Use `./start_ui.sh` script (sets PYTHONPATH)
- Or use: `PYTHONPATH=. streamlit run scanner/modes/ui_app.py`

### UI looks different from screenshots
- Clear browser cache and reload
- Try different browser (Chrome/Firefox)
- Check Streamlit version: `streamlit --version`

---

## Comparison: UI vs CLI

| Feature | CLI | Web UI |
|---------|-----|--------|
| Speed | Fast | Slightly slower |
| Configuration | config.json only | Interactive sliders |
| Charts | No | Yes (candlestick, indicators) |
| Export | Command line flag | Click buttons |
| Position Sizing | Yes | Yes |
| Actionable Filter | Yes | Yes (with toggle) |
| Best For | Quick scans, automation | Exploration, parameter tuning |

**Recommendation:**
- Use **CLI** for daily automated scans
- Use **Web UI** for exploring and tuning parameters
