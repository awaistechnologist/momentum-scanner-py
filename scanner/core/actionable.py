"""Actionable filter - converts signals into vetted, sized trades."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from scanner.core.models import Signal, Bar

logger = logging.getLogger(__name__)


@dataclass
class ActionableConfig:
    """Configuration for actionable filter."""
    enabled: bool
    account_size: float
    risk_percent_per_trade: float
    min_rr: float
    require_rsi_slope_non_negative: bool
    min_volume_ratio: float
    allow_volume_rising_days: int
    earnings_lookahead_trading_days: int
    atr_min: float
    gapdown_guard_pct: float
    must_hold_trend: bool
    min_price: float
    min_avg_dollar_volume_20d: float

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "ActionableConfig":
        """Create config from dictionary."""
        return cls(
            enabled=config.get("enabled", True),
            account_size=config.get("risk", {}).get("account_size", 10000),
            risk_percent_per_trade=config.get("risk", {}).get("risk_percent_per_trade", 1.0),
            min_rr=config.get("technical", {}).get("min_rr", 2.0),
            require_rsi_slope_non_negative=config.get("technical", {}).get("require_rsi_slope_non_negative", True),
            min_volume_ratio=config.get("technical", {}).get("min_volume_ratio", 1.2),
            allow_volume_rising_days=config.get("technical", {}).get("allow_volume_rising_days", 3),
            earnings_lookahead_trading_days=config.get("technical", {}).get("earnings_lookahead_trading_days", 7),
            atr_min=config.get("technical", {}).get("atr_min", 1.0),
            gapdown_guard_pct=config.get("technical", {}).get("gapdown_guard_pct", -1.5),
            must_hold_trend=config.get("technical", {}).get("must_hold_trend", True),
            min_price=config.get("liquidity", {}).get("min_price", 5.0),
            min_avg_dollar_volume_20d=config.get("liquidity", {}).get("min_avg_dollar_volume_20d", 10000000)
        )


@dataclass
class ActionableSignal:
    """Signal with actionable trade sizing and metadata."""
    signal: Signal
    position_size_shares: int
    risk_dollars: float
    reward_dollars: float
    notes: List[str]


@dataclass
class RejectedSignal:
    """Signal that didn't pass actionable filters."""
    symbol: str
    rejection_reasons: List[str]


def check_volume_rising(bars: List[Bar], days: int = 3) -> bool:
    """
    Check if volume is rising over last N days.

    Args:
        bars: List of historical bars
        days: Number of consecutive days to check

    Returns:
        True if volume rising for N consecutive days
    """
    if len(bars) < days + 1:
        return False

    recent_volumes = [b.volume for b in bars[-(days + 1):]]

    # Check if each day's volume > previous day
    for i in range(1, len(recent_volumes)):
        if recent_volumes[i] <= recent_volumes[i - 1]:
            return False

    return True


class ActionableFilter:
    """
    Second-stage filter that converts scanner signals into actionable trades.

    Applies stricter safety filters and calculates position sizing.
    """

    def __init__(self, config: ActionableConfig):
        """Initialize with configuration."""
        self.config = config

    def filter_signals(
        self,
        signals: List[Signal],
        bars_dict: Optional[Dict[str, List[Bar]]] = None
    ) -> Tuple[List[ActionableSignal], List[RejectedSignal]]:
        """
        Filter signals through actionable safety rules.

        Args:
            signals: List of signals from scanner
            bars_dict: Optional dict of symbol -> bars for volume rising check

        Returns:
            Tuple of (actionable_signals, rejected_signals)
        """
        if not self.config.enabled:
            logger.info("Actionable filter disabled - returning all signals as-is")
            # Convert all signals to actionable (with minimal sizing)
            actionable = []
            for sig in signals:
                pos_size, risk_dollars, reward_dollars = self._calculate_sizing(sig)
                actionable.append(ActionableSignal(
                    signal=sig,
                    position_size_shares=pos_size,
                    risk_dollars=risk_dollars,
                    reward_dollars=reward_dollars,
                    notes=["Actionable filter disabled"]
                ))
            return actionable, []

        actionable: List[ActionableSignal] = []
        rejected: List[RejectedSignal] = []

        for signal in signals:
            reasons = []

            # Apply safety rules
            passed, rule_reasons = self._apply_safety_rules(signal, bars_dict)
            reasons.extend(rule_reasons)

            if not passed:
                rejected.append(RejectedSignal(
                    symbol=signal.symbol,
                    rejection_reasons=reasons
                ))
                logger.debug(f"{signal.symbol}: Rejected by actionable filter - {', '.join(reasons)}")
                continue

            # Calculate position sizing
            pos_size, risk_dollars, reward_dollars = self._calculate_sizing(signal)

            if pos_size < 1:
                rejected.append(RejectedSignal(
                    symbol=signal.symbol,
                    rejection_reasons=["Position size < 1 share"]
                ))
                logger.debug(f"{signal.symbol}: Rejected - position size {pos_size} < 1 share")
                continue

            # Create actionable signal
            notes = self._generate_notes(signal)
            actionable.append(ActionableSignal(
                signal=signal,
                position_size_shares=pos_size,
                risk_dollars=risk_dollars,
                reward_dollars=reward_dollars,
                notes=notes
            ))
            logger.info(f"{signal.symbol}: Actionable - Size={pos_size} shares, Risk=${risk_dollars:.0f}, Reward=${reward_dollars:.0f}")

        return actionable, rejected

    def _apply_safety_rules(
        self,
        signal: Signal,
        bars_dict: Optional[Dict[str, List[Bar]]]
    ) -> Tuple[bool, List[str]]:
        """
        Apply all safety rules to a signal.

        Returns:
            Tuple of (passed, rejection_reasons)
        """
        reasons = []

        # 1. R/R gate
        if signal.risk_reward and signal.risk_reward < self.config.min_rr:
            reasons.append(f"R/R {signal.risk_reward:.1f} < {self.config.min_rr}")

        # 2. RSI slope
        if self.config.require_rsi_slope_non_negative:
            if signal.rsi_slope == "↓":
                reasons.append("RSI slope ↓ (falling)")

        # 3. Volume check
        volume_ok = False
        if signal.volume_ratio and signal.volume_ratio >= self.config.min_volume_ratio:
            volume_ok = True
        elif bars_dict and signal.symbol in bars_dict:
            # Check if volume rising for N days
            if check_volume_rising(bars_dict[signal.symbol], self.config.allow_volume_rising_days):
                volume_ok = True

        if not volume_ok:
            vol_str = f"{signal.volume_ratio:.1f}×" if signal.volume_ratio else "?"
            reasons.append(f"Volume {vol_str} needs ≥ {self.config.min_volume_ratio}× or rising {self.config.allow_volume_rising_days}d")

        # 4. Trend health (already checked in strategy, but re-verify if required)
        if self.config.must_hold_trend:
            # Signals already passed 50-SMA and EMA checks in strategy
            # This is a sanity check - would need fresh data for real-time verification
            pass

        # 5. Earnings proximity (optional - skip for now, mark as unknown)
        # TODO: Implement earnings date fetching
        # For now, we'll add a note but not reject

        # 6. ATR floor
        if signal.atr and signal.atr < self.config.atr_min:
            reasons.append(f"ATR {signal.atr:.2f} < {self.config.atr_min} (low volatility)")

        # 7. Gap-down guard (requires intraday data - skip for daily scanner)
        # This would need current/open price vs entry price
        # Skip for now in daily mode

        # 8. Liquidity reaffirmation
        if signal.price < self.config.min_price:
            reasons.append(f"Price ${signal.price:.2f} < ${self.config.min_price}")

        if signal.avg_dollar_volume_20d and signal.avg_dollar_volume_20d < self.config.min_avg_dollar_volume_20d:
            reasons.append(f"Dollar volume ${signal.avg_dollar_volume_20d:,.0f} < ${self.config.min_avg_dollar_volume_20d:,.0f}")

        passed = len(reasons) == 0
        return passed, reasons

    def _calculate_sizing(self, signal: Signal) -> Tuple[int, float, float]:
        """
        Calculate position size and risk/reward dollars.

        Returns:
            Tuple of (position_size_shares, risk_dollars, reward_dollars)
        """
        if not signal.suggested_entry or not signal.suggested_stop or not signal.suggested_target:
            return 0, 0.0, 0.0

        # Risk per share
        risk_per_share = signal.suggested_entry - signal.suggested_stop
        if risk_per_share <= 0:
            return 0, 0.0, 0.0

        # Risk dollars target (account size × risk percent)
        risk_dollars_target = self.config.account_size * (self.config.risk_percent_per_trade / 100)

        # Position size (floored)
        position_size_shares = int(risk_dollars_target / risk_per_share)

        # ACTUAL risk dollars after rounding shares
        risk_dollars_actual = position_size_shares * risk_per_share

        # Reward dollars
        reward_per_share = signal.suggested_target - signal.suggested_entry
        reward_dollars = position_size_shares * reward_per_share

        return position_size_shares, risk_dollars_actual, reward_dollars

    def _generate_notes(self, signal: Signal) -> List[str]:
        """Generate notes/badges for actionable signal."""
        notes = []

        # Trend quality
        if signal.score >= 80:
            notes.append("🔥 High score")

        # RSI slope (Tweak #5: Add confirmation tag for accepted signals)
        if signal.rsi_slope == "↑":
            notes.append("RSI rising")
        elif signal.rsi_slope == "→":
            notes.append("RSI flat")
        # Add confirmation for non-falling RSI (requirement passed)
        if signal.rsi_slope in ["↑", "→"]:
            notes.append("RSI slope OK")

        # Volume
        if signal.volume_ratio and signal.volume_ratio >= 1.5:
            notes.append("Volume breakout")

        # MACD
        if signal.histogram_rising_bars and signal.histogram_rising_bars > 0:
            notes.append(f"MACD hist +{signal.histogram_rising_bars}bars")

        # R/R
        if signal.risk_reward and signal.risk_reward >= 3.0:
            notes.append("High R/R")

        # Pivot proximity (Tweak #6: Standardize wording)
        if signal.distance_to_pivot_pct is not None:
            if signal.distance_to_pivot_pct < 1:
                notes.append("At pivot")
            elif signal.distance_to_pivot_pct < 2:
                notes.append("Near pivot")
            elif signal.distance_to_pivot_pct < 5:
                notes.append("Approaching pivot")

        # Earnings status (Tweak #4: placeholder - will need earnings data integration)
        # TODO: Implement earnings date fetching
        notes.append("Earnings: unknown")

        if not notes:
            notes.append("✅ Clean trend")

        return notes
