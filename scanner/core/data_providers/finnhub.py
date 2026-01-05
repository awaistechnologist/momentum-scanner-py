"""Finnhub data provider implementation."""

import logging
from datetime import datetime, timedelta, timezone
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


class FinnhubProvider(MarketDataProvider):
    """Finnhub market data provider (supports LSE and US markets)."""

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Finnhub provider."""
        super().__init__(api_key)
        if not api_key:
            raise ProviderError("Finnhub API key is required")

    def normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol for Finnhub (LSE symbols need .L suffix)."""
        symbol = symbol.upper()
        # Finnhub uses .L for LSE symbols
        return symbol

    def supports_symbol(self, symbol: str) -> bool:
        """Check if symbol is supported (basic check)."""
        # Finnhub supports most global symbols
        return True

    @retry_with_backoff(max_retries=3, exceptions=(requests.RequestException,))
    def _make_request(self, endpoint: str, params: dict) -> dict:
        """Make HTTP request to Finnhub API."""
        params["token"] = self.api_key
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 429:
                raise RateLimitError("Finnhub rate limit exceeded")
            elif response.status_code == 404:
                raise SymbolNotFoundError(f"Symbol not found")
            elif response.status_code != 200:
                raise ProviderError(f"Finnhub API error: {response.status_code}")

            data = response.json()

            # Check for error in response
            if isinstance(data, dict) and data.get("error"):
                raise ProviderError(f"Finnhub error: {data['error']}")

            return data

        except requests.RequestException as e:
            logger.error(f"Finnhub request failed: {e}")
            raise ProviderError(f"Request failed: {e}")

    @cached(ttl_seconds=60)
    def get_quote(self, symbol: str) -> Quote:
        """Fetch current quote from Finnhub."""
        symbol = self.normalize_symbol(symbol)
        data = self._make_request("quote", {"symbol": symbol})

        if not data or data.get("c") == 0:
            raise DataUnavailableError(f"No quote data for {symbol}")

        return Quote(
            symbol=symbol,
            price=data["c"],  # current price
            change=data.get("d"),  # change
            change_pct=data.get("dp"),  # change percent
            timestamp=datetime.fromtimestamp(data.get("t", 0), tz=timezone.utc)
        )

    def get_bars(
        self,
        symbol: str,
        interval: str = "1d",
        lookback: int = 200
    ) -> List[Bar]:
        """Fetch historical bars from Finnhub."""
        symbol = self.normalize_symbol(symbol)

        # Finnhub uses resolution: 1, 5, 15, 30, 60, D, W, M
        resolution_map = {
            "1d": "D",
            "60m": "60",
            "15m": "15"
        }
        resolution = resolution_map.get(interval, "D")

        # Calculate date range
        end_time = int(datetime.now(timezone.utc).timestamp())

        # Estimate start time based on lookback
        days_multiplier = {
            "D": 1,
            "60": 1 / 6.5,  # ~6.5 trading hours per day
            "15": 1 / 26    # ~26 15-min bars per day
        }
        days_back = int(lookback * days_multiplier.get(resolution, 1) * 1.5)  # Add buffer
        start_time = int((datetime.now(timezone.utc) - timedelta(days=days_back)).timestamp())

        data = self._make_request(
            "stock/candle",
            {
                "symbol": symbol,
                "resolution": resolution,
                "from": start_time,
                "to": end_time
            }
        )

        if data.get("s") != "ok" or not data.get("t"):
            raise DataUnavailableError(f"No bar data for {symbol}")

        bars = []
        for i in range(len(data["t"])):
            bars.append(Bar(
                timestamp=datetime.fromtimestamp(data["t"][i], tz=timezone.utc),
                open=data["o"][i],
                high=data["h"][i],
                low=data["l"][i],
                close=data["c"][i],
                volume=data["v"][i]
            ))

        # Return most recent lookback bars
        return sorted(bars, key=lambda x: x.timestamp)[-lookback:]

    @cached(ttl_seconds=3600)
    def get_meta(self, symbol: str) -> TickerMeta:
        """Fetch ticker metadata from Finnhub."""
        symbol = self.normalize_symbol(symbol)

        try:
            # Get company profile
            data = self._make_request("stock/profile2", {"symbol": symbol})

            return TickerMeta(
                symbol=symbol,
                name=data.get("name"),
                exchange=data.get("exchange"),
                currency=data.get("currency"),
                market_cap=data.get("marketCapitalization"),
                sector=data.get("finnhubIndustry"),
                industry=data.get("finnhubIndustry")
            )
        except Exception as e:
            logger.warning(f"Failed to fetch metadata for {symbol}: {e}")
            # Return minimal metadata
            return TickerMeta(symbol=symbol)
