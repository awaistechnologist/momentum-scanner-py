"""Base interface for market data providers."""

from abc import ABC, abstractmethod
from typing import List, Optional
from scanner.core.models import Bar, Quote, TickerMeta


class MarketDataProvider(ABC):
    """Abstract base class for market data providers."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize provider with optional API key."""
        self.api_key = api_key

    @abstractmethod
    def get_bars(
        self,
        symbol: str,
        interval: str = "1d",
        lookback: int = 200
    ) -> List[Bar]:
        """
        Fetch historical OHLCV bars.

        Args:
            symbol: Ticker symbol (e.g., 'AAPL', 'VOD.L')
            interval: Time interval ('1d', '60m', '15m')
            lookback: Number of bars to fetch

        Returns:
            List of Bar objects, sorted by timestamp ascending
        """
        pass

    @abstractmethod
    def get_quote(self, symbol: str) -> Quote:
        """
        Fetch current quote/price.

        Args:
            symbol: Ticker symbol

        Returns:
            Quote object with current price and metadata
        """
        pass

    @abstractmethod
    def get_meta(self, symbol: str) -> TickerMeta:
        """
        Fetch ticker metadata.

        Args:
            symbol: Ticker symbol

        Returns:
            TickerMeta object with company/ticker information
        """
        pass

    @abstractmethod
    def supports_symbol(self, symbol: str) -> bool:
        """
        Check if provider supports this symbol.

        Args:
            symbol: Ticker symbol

        Returns:
            True if supported, False otherwise
        """
        pass

    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol format for this provider.

        Override in subclass if provider has specific symbol format requirements.

        Args:
            symbol: Input symbol

        Returns:
            Normalized symbol for this provider
        """
        return symbol.upper()


class ProviderError(Exception):
    """Base exception for provider errors."""
    pass


class RateLimitError(ProviderError):
    """Rate limit exceeded."""
    pass


class SymbolNotFoundError(ProviderError):
    """Symbol not found or not supported."""
    pass


class DataUnavailableError(ProviderError):
    """Data temporarily unavailable."""
    pass
