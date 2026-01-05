"""Data models for the scanner."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Bar(BaseModel):
    """OHLCV bar data."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Quote(BaseModel):
    """Current quote data."""
    symbol: str
    price: float
    change: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[float] = None
    timestamp: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TickerMeta(BaseModel):
    """Ticker metadata."""
    symbol: str
    name: Optional[str] = None
    exchange: Optional[str] = None
    currency: Optional[str] = None
    market_cap: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None


class Signal(BaseModel):
    """Trading signal with scoring and analysis."""
    symbol: str
    timestamp: datetime
    price: float
    score: float = Field(ge=0, le=100, description="Composite score 0-100")

    # Signal components
    signals_hit: List[str] = Field(default_factory=list)

    # Indicator values
    rsi: Optional[float] = None
    rsi_slope: Optional[str] = None  # '↑', '↓', '→'
    ema_9: Optional[float] = None
    ema_21: Optional[float] = None
    sma_50: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    histogram_rising_bars: Optional[int] = None  # Number of bars histogram is rising
    volume_avg_20: Optional[float] = None
    current_volume: Optional[float] = None
    volume_ratio: Optional[float] = None  # current_volume / volume_avg_20
    avg_dollar_volume_20d: Optional[float] = None
    atr: Optional[float] = None
    adx: Optional[float] = None

    # Score breakdown
    score_breakdown: Dict[str, float] = Field(default_factory=dict)

    # Risk management
    suggested_entry: Optional[float] = None
    suggested_stop: Optional[float] = None
    suggested_target: Optional[float] = None
    stop_basis: Optional[str] = None  # e.g., "1.0×ATR", "swing-low"
    target_basis: Optional[str] = None  # e.g., "+7%", "2×ATR"
    risk_reward: Optional[float] = None

    # Additional context
    pivot_high: Optional[float] = None
    recent_low: Optional[float] = None
    distance_to_pivot_pct: Optional[float] = None

    # Metadata
    meta: Optional[TickerMeta] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def to_summary(self) -> str:
        """Generate a human-readable summary."""
        signals = ", ".join(self.signals_hit) if self.signals_hit else "None"
        return (
            f"{self.symbol} @ {self.price:.2f} | Score: {self.score:.1f}\n"
            f"  Signals: {signals}\n"
            f"  RSI: {self.rsi:.1f if self.rsi else 'N/A'} | "
            f"ATR: {self.atr:.2f if self.atr else 'N/A'}\n"
            f"  Entry: {self.suggested_entry:.2f if self.suggested_entry else 'N/A'} | "
            f"Stop: {self.suggested_stop:.2f if self.suggested_stop else 'N/A'} | "
            f"Target: {self.suggested_target:.2f if self.suggested_target else 'N/A'}"
        )


class ActionableSignal(BaseModel):
    """Signal with position sizing and actionable metadata."""
    signal: Signal
    position_size_shares: int
    risk_dollars: float
    reward_dollars: float
    notes: List[str] = Field(default_factory=list)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RejectedSignal(BaseModel):
    """Signal rejected by actionable filter."""
    symbol: str
    rejection_reasons: List[str]


class ScanResult(BaseModel):
    """Complete scan result with multiple signals."""
    scan_timestamp: datetime
    universe: List[str]
    signals: List[Signal]
    scanned_count: int
    passed_count: int
    config_snapshot: Dict[str, Any] = Field(default_factory=dict)

    # Provenance metadata (Tweak #3: header/provenance)
    mode: Optional[str] = None  # "momentum", "rebound", or "auto"
    regime: Optional[str] = None  # "MOMENTUM" or "REBOUND" (when mode=auto)
    data_provider: Optional[str] = None  # "alpaca", "finnhub", etc.
    timeframe: Optional[str] = None  # "1d", "1h", etc.
    last_bar_timestamp: Optional[datetime] = None  # Timestamp of most recent data

    # Actionable results (optional, only if actionable filter enabled)
    actionable_signals: Optional[List[ActionableSignal]] = None
    rejected_signals: Optional[List[RejectedSignal]] = None
    actionable_count: Optional[int] = None

    # Run readiness (optional, only if readiness check enabled)
    readiness_status: Optional[str] = None  # READY, EARLY, STALE, HOLIDAY, RE_RUN
    readiness_message: Optional[str] = None
    readiness_can_run: Optional[bool] = None
    market_open_guidance: Optional[str] = None  # Next market open timing guidance

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
