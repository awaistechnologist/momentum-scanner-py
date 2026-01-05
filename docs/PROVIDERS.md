# Data Providers

## Current Setup

**Primary:** Alpaca Markets (batch API, optimized)
**Backups:** AlphaVantage, Finnhub, TwelveData

## Alpaca Markets (Default) ✅

### Features
- ✅ **Batch API**: 100 symbols per request
- ✅ **Rate Limit**: 200 requests/minute (free tier)
- ✅ **Coverage**: All US stocks
- ✅ **Data Quality**: Split-adjusted OHLCV
- ✅ **Performance**: 96 symbols in 2-3 API calls

### Setup
Configure in `.env`:
```bash
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_API_SECRET=your_alpaca_api_secret_here
```

Get your free API key at [alpaca.markets](https://alpaca.markets)

### API Limits
- 200 requests/minute
- No daily limit (free tier)
- Delayed data (~15 min)

## Backup Providers

### AlphaVantage
```bash
ALPHAVANTAGE_API_KEY=your_key_here
```
- **Rate Limit**: 5 calls/min, 25 calls/day
- **Coverage**: Global stocks, forex, crypto
- **Best for**: Fundamental data

### Finnhub
```bash
FINNHUB_API_KEY=your_key_here
```
- **Rate Limit**: 60 calls/min
- **Coverage**: Global stocks
- **Best for**: Real-time backup

### TwelveData
```bash
TWELVEDATA_API_KEY=your_key_here
```
- **Rate Limit**: 8 calls/min
- **Coverage**: Global stocks, crypto
- **Best for**: Alternative data

## Switching Providers

Edit `config.json`:
```json
{
  "data": {
    "provider": "alpaca",
    "fallback_provider": null
  }
}
```

Options: `alpaca`, `alphavantage`, `finnhub`, `twelvedata`

## Provider Comparison

| Provider | Batch API | Rate Limit | US | Global | Status |
|----------|-----------|------------|-------|--------|---------|
| **Alpaca** | ✅ Yes | 200/min | ✅ | ❌ | **Primary** |
| AlphaVantage | ❌ No | 5/min | ✅ | ✅ | Backup |
| Finnhub | ❌ No | 60/min | ✅ | ✅ | Backup |
| TwelveData | ❌ No | 8/min | ✅ | ✅ | Backup |

## Performance

**With Alpaca (current):**
- 96 symbols = 2-3 API calls
- ~3 second scan time
- 97.9% data success rate
- Zero rate limit issues

**Note:** Only Alpaca supports batch API. Other providers fetch 1 symbol per call.
