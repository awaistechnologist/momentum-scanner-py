"""Alpha Vantage data provider implementation (free tier friendly)."""

import logging
from datetime import datetime, timezone
from typing import List, Optional
import requests

from scanner.core.data_providers.base import (
    MarketDataProvider,
    ProviderError,
    RateLimitError,
    SymbolNotFoundError,
    DataUnavailableError
)
from scanner.core.models import Bar, Quote, TickerMeta
from scanner.core.utils import retry_with_backoff, cached

logger = logging.getLogger(__name__)


class AlphaVantageProvider(MarketDataProvider):
    """
    Alpha Vantage data provider (excellent free tier).

    Free tier: 25 calls/day or 5 calls/minute
    Includes: 20+ years historical data
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Alpha Vantage provider."""
        super().__init__(api_key)
        if not api_key:
            raise ProviderError("Alpha Vantage API key is required")
        logger.info("Using Alpha Vantage provider (free tier: 5 calls/min, 25/day)")

    def normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol for Alpha Vantage."""
        symbol = symbol.upper()
        # Alpha Vantage uses different notation for LSE
        if symbol.endswith(".L"):
            # Convert VOD.L to VOD.LON
            return symbol.replace(".L", ".LON")
        return symbol

    def supports_symbol(self, symbol: str) -> bool:
        """Check if symbol is supported."""
        return True

    @retry_with_backoff(max_retries=2, exceptions=(requests.RequestException,))
    def _make_request(self, params: dict) -> dict:
        """Make HTTP request to Alpha Vantage API."""
        params["apikey"] = self.api_key

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)

            if response.status_code == 429:
                raise RateLimitError("Alpha Vantage rate limit exceeded")
            elif response.status_code != 200:
                raise ProviderError(f"Alpha Vantage API error: {response.status_code}")

            data = response.json()

            # Check for API errors
            if "Error Message" in data:
                raise SymbolNotFoundError(data["Error Message"])

            if "Note" in data:
                # Rate limit message
                raise RateLimitError("Alpha Vantage API rate limit reached")

            if "Information" in data:
                raise RateLimitError(data["Information"])

            return data

        except requests.RequestException as e:
            logger.error(f"Alpha Vantage request failed: {e}")
            raise ProviderError(f"Request failed: {e}")

    @cached(ttl_seconds=60)
    def get_quote(self, symbol: str) -> Quote:
        """Fetch current quote from Alpha Vantage."""
        symbol = self.normalize_symbol(symbol)

        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol
        }

        data = self._make_request(params)

        if "Global Quote" not in data or not data["Global Quote"]:
            raise DataUnavailableError(f"No quote data for {symbol}")

        quote_data = data["Global Quote"]

        return Quote(
            symbol=symbol,
            price=float(quote_data["05. price"]),
            change=float(quote_data.get("09. change", 0)),
            change_pct=float(quote_data.get("10. change percent", "0").replace("%", "")),
            volume=float(quote_data.get("06. volume", 0)),
            timestamp=datetime.now(timezone.utc)
        )

    def get_bars(
        self,
        symbol: str,
        interval: str = "1d",
        lookback: int = 200
    ) -> List[Bar]:
        """Fetch historical bars from Alpha Vantage."""
        symbol = self.normalize_symbol(symbol)

        # Alpha Vantage uses TIME_SERIES_DAILY for daily data
        if interval == "1d":
            function = "TIME_SERIES_DAILY"
            outputsize = "full" if lookback > 100 else "compact"

            params = {
                "function": function,
                "symbol": symbol,
                "outputsize": outputsize
            }
        else:
            # For intraday data
            interval_map = {
                "15m": "15min",
                "60m": "60min"
            }
            av_interval = interval_map.get(interval, "60min")

            params = {
                "function": "TIME_SERIES_INTRADAY",
                "symbol": symbol,
                "interval": av_interval,
                "outputsize": "full"
            }

        data = self._make_request(params)

        # Get the time series data
        time_series_key = None
        for key in data.keys():
            if "Time Series" in key:
                time_series_key = key
                break

        if not time_series_key or not data[time_series_key]:
            raise DataUnavailableError(f"No bar data for {symbol}")

        time_series = data[time_series_key]

        bars = []
        for timestamp_str, values in time_series.items():
            try:
                # Parse timestamp
                if interval == "1d":
                    dt = datetime.strptime(timestamp_str, "%Y-%m-%d")
                else:
                    dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                dt = dt.replace(tzinfo=timezone.utc)

                bars.append(Bar(
                    timestamp=dt,
                    open=float(values["1. open"]),
                    high=float(values["2. high"]),
                    low=float(values["3. low"]),
                    close=float(values["4. close"]),
                    volume=float(values["5. volume"])
                ))
            except (KeyError, ValueError) as e:
                logger.warning(f"Skipping invalid bar data: {e}")
                continue

        # Sort by timestamp (oldest first) and return most recent lookback bars
        bars.sort(key=lambda x: x.timestamp)
        return bars[-lookback:]

    @cached(ttl_seconds=3600)
    def get_meta(self, symbol: str) -> TickerMeta:
        """
        Fetch ticker metadata from Alpha Vantage.

        Note: Overview endpoint also counts toward rate limit.
        """
        symbol_clean = self.normalize_symbol(symbol)

        try:
            params = {
                "function": "OVERVIEW",
                "symbol": symbol_clean
            }

            data = self._make_request(params)

            if not data or "Symbol" not in data:
                return TickerMeta(symbol=symbol)

            return TickerMeta(
                symbol=symbol,
                name=data.get("Name"),
                exchange=data.get("Exchange"),
                currency=data.get("Currency"),
                market_cap=float(data.get("MarketCapitalization", 0)) if data.get("MarketCapitalization") else None,
                sector=data.get("Sector"),
                industry=data.get("Industry")
            )
        except Exception as e:
            logger.warning(f"Failed to fetch metadata for {symbol}: {e}")
            return TickerMeta(symbol=symbol)
