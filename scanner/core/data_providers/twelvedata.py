"""Twelve Data provider implementation."""

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


class TwelveDataProvider(MarketDataProvider):
    """Twelve Data market data provider (supports global markets including LSE)."""

    BASE_URL = "https://api.twelvedata.com"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Twelve Data provider."""
        super().__init__(api_key)
        if not api_key:
            raise ProviderError("Twelve Data API key is required")

    def normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol for Twelve Data."""
        # Twelve Data uses colon notation for exchanges: VOD:LSE or AAPL:NASDAQ
        # We'll keep .L notation and convert when needed
        return symbol.upper()

    def _parse_symbol_exchange(self, symbol: str) -> tuple[str, Optional[str]]:
        """Parse symbol and exchange from input."""
        if ".L" in symbol:
            return symbol.replace(".L", ""), "LSE"
        elif ":" in symbol:
            parts = symbol.split(":")
            return parts[0], parts[1]
        else:
            # US symbols default to no exchange suffix
            return symbol, None

    def supports_symbol(self, symbol: str) -> bool:
        """Check if symbol is supported."""
        return True

    @retry_with_backoff(max_retries=3, exceptions=(requests.RequestException,))
    def _make_request(self, endpoint: str, params: dict) -> dict:
        """Make HTTP request to Twelve Data API."""
        params["apikey"] = self.api_key
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 429:
                raise RateLimitError("Twelve Data rate limit exceeded")
            elif response.status_code == 404:
                raise SymbolNotFoundError("Symbol not found")
            elif response.status_code != 200:
                raise ProviderError(f"Twelve Data API error: {response.status_code}")

            data = response.json()

            # Check for API errors
            if isinstance(data, dict):
                if data.get("status") == "error":
                    error_msg = data.get("message", "Unknown error")
                    if "not found" in error_msg.lower():
                        raise SymbolNotFoundError(error_msg)
                    raise ProviderError(f"Twelve Data error: {error_msg}")

            return data

        except requests.RequestException as e:
            logger.error(f"Twelve Data request failed: {e}")
            raise ProviderError(f"Request failed: {e}")

    @cached(ttl_seconds=60)
    def get_quote(self, symbol: str) -> Quote:
        """Fetch current quote from Twelve Data."""
        symbol_clean = self.normalize_symbol(symbol)
        base_symbol, exchange = self._parse_symbol_exchange(symbol_clean)

        params = {"symbol": base_symbol}
        if exchange:
            params["exchange"] = exchange

        data = self._make_request("price", params)

        if not data or not data.get("price"):
            raise DataUnavailableError(f"No quote data for {symbol}")

        price = float(data["price"])

        return Quote(
            symbol=symbol,
            price=price,
            timestamp=datetime.now(timezone.utc)
        )

    def get_bars(
        self,
        symbol: str,
        interval: str = "1d",
        lookback: int = 200
    ) -> List[Bar]:
        """Fetch historical bars from Twelve Data."""
        symbol_clean = self.normalize_symbol(symbol)
        base_symbol, exchange = self._parse_symbol_exchange(symbol_clean)

        # Twelve Data intervals: 1min, 5min, 15min, 30min, 1h, 1day, 1week, 1month
        interval_map = {
            "1d": "1day",
            "60m": "1h",
            "15m": "15min"
        }
        td_interval = interval_map.get(interval, "1day")

        params = {
            "symbol": base_symbol,
            "interval": td_interval,
            "outputsize": lookback,
            "format": "JSON"
        }
        if exchange:
            params["exchange"] = exchange

        data = self._make_request("time_series", params)

        if not data or not data.get("values"):
            raise DataUnavailableError(f"No bar data for {symbol}")

        bars = []
        for item in data["values"]:
            try:
                bars.append(Bar(
                    timestamp=datetime.fromisoformat(item["datetime"].replace('Z', '+00:00')),
                    open=float(item["open"]),
                    high=float(item["high"]),
                    low=float(item["low"]),
                    close=float(item["close"]),
                    volume=float(item.get("volume", 0))
                ))
            except (KeyError, ValueError) as e:
                logger.warning(f"Skipping invalid bar data: {e}")
                continue

        # Twelve Data returns newest first, so reverse
        bars.reverse()
        return bars

    @cached(ttl_seconds=3600)
    def get_meta(self, symbol: str) -> TickerMeta:
        """Fetch ticker metadata from Twelve Data."""
        symbol_clean = self.normalize_symbol(symbol)
        base_symbol, exchange = self._parse_symbol_exchange(symbol_clean)

        try:
            params = {"symbol": base_symbol}
            if exchange:
                params["exchange"] = exchange

            data = self._make_request("profile", params)

            return TickerMeta(
                symbol=symbol,
                name=data.get("name"),
                exchange=data.get("exchange"),
                currency=data.get("currency"),
                sector=data.get("sector"),
                industry=data.get("industry")
            )
        except Exception as e:
            logger.warning(f"Failed to fetch metadata for {symbol}: {e}")
            return TickerMeta(symbol=symbol)
