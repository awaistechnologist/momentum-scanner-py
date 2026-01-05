"""Alpaca Markets data provider implementation."""

import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import requests
from scanner.core.data_providers.base import (
    MarketDataProvider,
    ProviderError,
    RateLimitError,
    SymbolNotFoundError,
    DataUnavailableError
)
from scanner.core.models import Bar, Quote, TickerMeta


class AlpacaProvider(MarketDataProvider):
    """Alpaca Markets data provider.

    Alpaca provides free real-time and historical market data for US stocks.
    API Documentation: https://alpaca.markets/docs/api-references/market-data-api/

    Features:
    - Free market data (no subscription required with basic account)
    - Real-time quotes via IEX
    - Historical bars (1min, 5min, 15min, 1hour, 1day)
    - Good rate limits
    - US stocks only

    Note: Free tier uses IEX data feed, not SIP.
    """

    BASE_URL = "https://data.alpaca.markets/v2"
    IEX_URL = "https://data.alpaca.markets/v1beta1/iex"

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """Initialize Alpaca provider with API credentials.

        Args:
            api_key: Alpaca API Key (or set ALPACA_API_KEY env var)
            api_secret: Alpaca API Secret (or set ALPACA_API_SECRET env var)
        """
        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.api_secret = api_secret or os.getenv("ALPACA_API_SECRET")

        if not self.api_key or not self.api_secret:
            raise ProviderError("Alpaca API credentials not found. Set ALPACA_API_KEY and ALPACA_API_SECRET environment variables.")

        self.headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret
        }

    def _make_request(self, endpoint: str, params: dict = None) -> dict:
        """Make authenticated request to Alpaca API."""
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)

            if response.status_code == 429:
                raise RateLimitError("Alpaca API rate limit exceeded")
            elif response.status_code == 404:
                raise SymbolNotFoundError(f"Symbol not found")
            elif response.status_code != 200:
                raise ProviderError(f"Alpaca API error: {response.status_code} - {response.text}")

            return response.json()
        except requests.exceptions.RequestException as e:
            raise DataUnavailableError(f"Network error: {str(e)}")

    def _convert_interval(self, interval: str) -> tuple:
        """Convert standard interval to Alpaca timeframe and multiplier.

        Args:
            interval: Standard interval ('1d', '60m', '15m', '5m', '1m')

        Returns:
            Tuple of (timeframe, multiplier) for Alpaca API
        """
        interval_map = {
            "1m": ("1Min", 1),
            "5m": ("5Min", 1),
            "15m": ("15Min", 1),
            "30m": ("30Min", 1),
            "60m": ("1Hour", 1),
            "1h": ("1Hour", 1),
            "1d": ("1Day", 1),
        }

        if interval not in interval_map:
            # Default to daily
            return ("1Day", 1)

        return interval_map[interval]

    def get_bars(
        self,
        symbol: str,
        interval: str = "1d",
        lookback: int = 200
    ) -> List[Bar]:
        """Fetch historical OHLCV bars from Alpaca.

        Args:
            symbol: Ticker symbol (e.g., 'AAPL')
            interval: Time interval ('1d', '60m', '15m', '5m', '1m')
            lookback: Number of bars to fetch

        Returns:
            List of Bar objects, sorted by timestamp ascending
        """
        symbol = self.normalize_symbol(symbol)
        timeframe, _ = self._convert_interval(interval)

        # Calculate date range
        # Free tier has 15-minute delay, so go back a bit further
        end_date = datetime.now() - timedelta(days=1)

        # Estimate start date based on interval and lookback
        if interval == "1d":
            start_date = end_date - timedelta(days=lookback * 2)  # Extra buffer for weekends
        elif "m" in interval:
            # For intraday, go back more days to ensure we get enough bars
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=lookback)

        params = {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
            "timeframe": timeframe,
            "limit": 10000,  # Max allowed
            "adjustment": "split"  # Adjust for splits
        }

        endpoint = f"stocks/{symbol}/bars"
        data = self._make_request(endpoint, params)

        if not data.get("bars"):
            raise DataUnavailableError(f"No bar data available for {symbol}")

        bars = []
        for bar_data in data["bars"]:
            bar = Bar(
                timestamp=datetime.fromisoformat(bar_data["t"].replace("Z", "+00:00")),
                open=float(bar_data["o"]),
                high=float(bar_data["h"]),
                low=float(bar_data["l"]),
                close=float(bar_data["c"]),
                volume=int(bar_data["v"])
            )
            bars.append(bar)

        # Sort by timestamp and limit to requested lookback
        bars.sort(key=lambda x: x.timestamp)
        return bars[-lookback:] if len(bars) > lookback else bars

    def get_bars_batch(
        self,
        symbols: List[str],
        interval: str = "1d",
        lookback: int = 200
    ) -> Dict[str, List[Bar]]:
        """Fetch historical bars for multiple symbols in one API call.

        This is much more efficient than calling get_bars() for each symbol.

        Args:
            symbols: List of ticker symbols (e.g., ['AAPL', 'MSFT', 'TSLA'])
            interval: Time interval ('1d', '60m', '15m', '5m', '1m')
            lookback: Number of bars to fetch

        Returns:
            Dict mapping symbol to list of Bar objects
        """
        if not symbols:
            return {}

        # Normalize symbols
        symbols = [self.normalize_symbol(s) for s in symbols]
        timeframe, _ = self._convert_interval(interval)

        # Calculate date range
        end_date = datetime.now() - timedelta(days=1)

        if interval == "1d":
            start_date = end_date - timedelta(days=lookback * 2)
        elif "m" in interval:
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=lookback)

        # Batch request - comma-separated symbols
        params = {
            "symbols": ",".join(symbols),
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
            "timeframe": timeframe,
            "limit": 10000,
            "adjustment": "all"  # Includes splits and dividends
        }

        endpoint = "stocks/bars"

        # Handle pagination - collect all bars from all pages
        result = {}
        page_token = None

        while True:
            if page_token:
                params["page_token"] = page_token

            data = self._make_request(endpoint, params)

            if not data.get("bars"):
                break

            # Process response - Alpaca returns {symbol: [bars]}
            for symbol, bar_list in data["bars"].items():
                if symbol not in result:
                    result[symbol] = []

                for bar_data in bar_list:
                    bar = Bar(
                        timestamp=datetime.fromisoformat(bar_data["t"].replace("Z", "+00:00")),
                        open=float(bar_data["o"]),
                        high=float(bar_data["h"]),
                        low=float(bar_data["l"]),
                        close=float(bar_data["c"]),
                        volume=int(bar_data["v"])
                    )
                    result[symbol].append(bar)

            # Check for next page
            page_token = data.get("next_page_token")
            if not page_token:
                break

        # Sort and limit bars for each symbol
        for symbol in result:
            result[symbol].sort(key=lambda x: x.timestamp)
            result[symbol] = result[symbol][-lookback:] if len(result[symbol]) > lookback else result[symbol]

        return result

    def get_quote(self, symbol: str) -> Quote:
        """Fetch current quote from Alpaca.

        For free tier, uses the latest bar close price instead of real-time quotes.

        Args:
            symbol: Ticker symbol

        Returns:
            Quote object with current price and metadata
        """
        symbol = self.normalize_symbol(symbol)

        # Get the most recent bar (last close price)
        bars = self.get_bars(symbol, interval="1d", lookback=1)

        if not bars:
            raise DataUnavailableError(f"No quote data available for {symbol}")

        latest_bar = bars[-1]

        return Quote(
            symbol=symbol,
            price=latest_bar.close,
            timestamp=latest_bar.timestamp,
            volume=latest_bar.volume
        )

    def get_meta(self, symbol: str) -> TickerMeta:
        """Fetch ticker metadata.

        Note: Alpaca doesn't provide detailed company metadata in their free tier.
        This returns basic information without making an API call (assumes symbol is valid).

        Args:
            symbol: Ticker symbol

        Returns:
            TickerMeta object with basic information
        """
        symbol = self.normalize_symbol(symbol)

        # Alpaca doesn't have a dedicated metadata endpoint in the free tier
        # Return basic info without making an API call (symbol validation happens in get_bars)
        return TickerMeta(
            symbol=symbol,
            name=symbol,  # No company name available
            exchange="US",  # Alpaca only supports US stocks
            currency="USD",
            asset_type="Stock"
        )

    def supports_symbol(self, symbol: str) -> bool:
        """Check if Alpaca supports this symbol.

        Alpaca supports US stocks only. Symbols with exchange suffixes (e.g., '.L')
        are not supported.

        Args:
            symbol: Ticker symbol

        Returns:
            True if supported (US stock), False otherwise
        """
        # Alpaca only supports US stocks
        # Reject symbols with exchange suffixes
        if '.' in symbol:
            return False

        # Basic validation - should be alphanumeric
        if not symbol.replace('-', '').isalnum():
            return False

        return True

    def normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol for Alpaca (uppercase, no exchange suffix).

        Args:
            symbol: Input symbol

        Returns:
            Normalized symbol
        """
        return symbol.upper().split('.')[0]
