"""Technical indicators for the scanner."""

import logging
from typing import List, Tuple
import numpy as np
import pandas as pd
from scanner.core.models import Bar

logger = logging.getLogger(__name__)


def bars_to_df(bars: List[Bar]) -> pd.DataFrame:
    """Convert list of Bar objects to pandas DataFrame."""
    if not bars:
        return pd.DataFrame()

    data = {
        "timestamp": [b.timestamp for b in bars],
        "open": [b.open for b in bars],
        "high": [b.high for b in bars],
        "low": [b.low for b in bars],
        "close": [b.close for b in bars],
        "volume": [b.volume for b in bars],
    }
    df = pd.DataFrame(data)
    df.set_index("timestamp", inplace=True)
    return df


def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average."""
    return series.rolling(window=period, min_periods=period).mean()


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average."""
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index.

    Args:
        series: Price series (typically close prices)
        period: RSI period (default 14)

    Returns:
        RSI series (0-100)
    """
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    Args:
        series: Price series (typically close prices)
        fast: Fast EMA period
        slow: Slow EMA period
        signal: Signal line EMA period

    Returns:
        Tuple of (macd_line, signal_line, histogram)
    """
    ema_fast = calculate_ema(series, fast)
    ema_slow = calculate_ema(series, slow)

    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range.

    Args:
        df: DataFrame with high, low, close columns
        period: ATR period

    Returns:
        ATR series
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=period).mean()

    return atr


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Average Directional Index (trend strength).

    Args:
        df: DataFrame with high, low, close columns
        period: ADX period

    Returns:
        ADX series
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]

    # Calculate +DM and -DM
    high_diff = high.diff()
    low_diff = -low.diff()

    plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
    minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

    # Calculate ATR
    atr = calculate_atr(df, period)

    # Calculate +DI and -DI
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

    # Calculate DX and ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period, min_periods=period).mean()

    return adx


def calculate_volume_average(series: pd.Series, period: int = 20) -> pd.Series:
    """Calculate average volume over period."""
    return series.rolling(window=period, min_periods=period).mean()


def find_pivot_high(df: pd.DataFrame, lookback: int = 20) -> float:
    """
    Find the highest high in the lookback period.

    Args:
        df: DataFrame with high column
        lookback: Number of periods to look back

    Returns:
        Pivot high value
    """
    if len(df) < lookback:
        return df["high"].max()
    return df["high"].iloc[-lookback:].max()


def find_recent_low(df: pd.DataFrame, lookback: int = 20) -> float:
    """
    Find the lowest low in the lookback period.

    Args:
        df: DataFrame with low column
        lookback: Number of periods to look back

    Returns:
        Recent low value
    """
    if len(df) < lookback:
        return df["low"].min()
    return df["low"].iloc[-lookback:].min()


def is_histogram_rising(histogram: pd.Series, bars: int = 2) -> bool:
    """
    Check if MACD histogram is rising for specified number of bars.

    Args:
        histogram: MACD histogram series
        bars: Number of bars to check

    Returns:
        True if rising, False otherwise
    """
    if len(histogram) < bars + 1:
        return False

    recent = histogram.iloc[-(bars + 1):]
    return all(recent.iloc[i] < recent.iloc[i + 1] for i in range(len(recent) - 1))


def calculate_rsi_slope(rsi: pd.Series, lookback: int = 3) -> str:
    """
    Calculate RSI slope/direction over last N bars.

    Args:
        rsi: RSI series
        lookback: Number of bars to check (default 3)

    Returns:
        String indicator: '↑' (rising), '↓' (falling), '→' (flat)
    """
    if len(rsi) < lookback:
        return "→"

    recent = rsi.iloc[-lookback:]
    slope = recent.iloc[-1] - recent.iloc[0]

    if slope > 2:  # Rising threshold
        return "↑"
    elif slope < -2:  # Falling threshold
        return "↓"
    else:
        return "→"


def calculate_dollar_volume(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    Calculate average dollar volume (price × volume) over period.

    Args:
        df: DataFrame with close and volume columns
        period: Lookback period (default 20)

    Returns:
        Average dollar volume series
    """
    dollar_volume = df["close"] * df["volume"]
    return dollar_volume.rolling(window=period, min_periods=period).mean()


class IndicatorCalculator:
    """Calculate all technical indicators for a symbol."""

    def __init__(self, bars: List[Bar]):
        """Initialize with bar data."""
        self.bars = bars
        self.df = bars_to_df(bars)

        if self.df.empty:
            raise ValueError("No bar data provided")

        # Pre-calculate all indicators
        self._calculate_all()

    def _calculate_all(self):
        """Calculate all indicators."""
        close = self.df["close"]

        # Moving averages
        self.sma_50 = calculate_sma(close, 50)
        self.ema_9 = calculate_ema(close, 9)
        self.ema_21 = calculate_ema(close, 21)

        # RSI
        self.rsi = calculate_rsi(close, 14)
        self.rsi_slope = calculate_rsi_slope(self.rsi, 3)

        # MACD
        self.macd, self.macd_signal, self.macd_histogram = calculate_macd(
            close, fast=12, slow=26, signal=9
        )

        # Volume
        self.volume_avg_20 = calculate_volume_average(self.df["volume"], 20)
        self.avg_dollar_volume_20 = calculate_dollar_volume(self.df, 20)

        # ATR
        self.atr = calculate_atr(self.df, 14)

        # ADX
        self.adx = calculate_adx(self.df, 14)

        # Pivot points
        self.pivot_high = find_pivot_high(self.df, 20)
        self.recent_low = find_recent_low(self.df, 20)

    def get_latest_values(self) -> dict:
        """Get the latest indicator values."""
        try:
            latest_idx = -1  # Most recent bar

            # Calculate volume ratio
            volume_ratio = None
            if not pd.isna(self.volume_avg_20.iloc[latest_idx]):
                volume_ratio = self.df["volume"].iloc[latest_idx] / self.volume_avg_20.iloc[latest_idx]

            return {
                "price": self.df["close"].iloc[latest_idx],
                "volume": self.df["volume"].iloc[latest_idx],
                "sma_50": self.sma_50.iloc[latest_idx] if not pd.isna(self.sma_50.iloc[latest_idx]) else None,
                "ema_9": self.ema_9.iloc[latest_idx] if not pd.isna(self.ema_9.iloc[latest_idx]) else None,
                "ema_21": self.ema_21.iloc[latest_idx] if not pd.isna(self.ema_21.iloc[latest_idx]) else None,
                "rsi": self.rsi.iloc[latest_idx] if not pd.isna(self.rsi.iloc[latest_idx]) else None,
                "rsi_slope": self.rsi_slope,
                "macd": self.macd.iloc[latest_idx] if not pd.isna(self.macd.iloc[latest_idx]) else None,
                "macd_signal": self.macd_signal.iloc[latest_idx] if not pd.isna(self.macd_signal.iloc[latest_idx]) else None,
                "macd_histogram": self.macd_histogram.iloc[latest_idx] if not pd.isna(self.macd_histogram.iloc[latest_idx]) else None,
                "volume_avg_20": self.volume_avg_20.iloc[latest_idx] if not pd.isna(self.volume_avg_20.iloc[latest_idx]) else None,
                "volume_ratio": volume_ratio,
                "avg_dollar_volume_20d": self.avg_dollar_volume_20.iloc[latest_idx] if not pd.isna(self.avg_dollar_volume_20.iloc[latest_idx]) else None,
                "atr": self.atr.iloc[latest_idx] if not pd.isna(self.atr.iloc[latest_idx]) else None,
                "adx": self.adx.iloc[latest_idx] if not pd.isna(self.adx.iloc[latest_idx]) else None,
                "pivot_high": self.pivot_high,
                "recent_low": self.recent_low,
                "histogram_rising": is_histogram_rising(self.macd_histogram, 2)
            }
        except Exception as e:
            logger.error(f"Error getting latest indicator values: {e}")
            return {}
