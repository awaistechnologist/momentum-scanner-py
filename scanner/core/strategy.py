"""Trading strategy rules and signal detection."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from scanner.core.models import Bar, Signal, TickerMeta
from scanner.core.indicators import IndicatorCalculator

logger = logging.getLogger(__name__)


class StrategyConfig:
    """Configuration for strategy rules."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize from config dict."""
        self.rsi_min = config.get("rsi_min", 50)
        self.rsi_max = config.get("rsi_max", 65)
        self.ema_fast = config.get("ema_fast", 9)
        self.ema_slow = config.get("ema_slow", 21)
        self.sma_trend = config.get("sma_trend", 50)
        self.macd_config = config.get("macd", {"fast": 12, "slow": 26, "signal": 9})
        self.volume_window = config.get("volume_window", 20)
        self.adx_min = config.get("adx_min", 0)
        self.weights = config.get("weights", {
            "ema": 25,
            "rsi": 20,
            "macd": 25,
            "volume": 20,
            "breakout": 10
        })
        self.score_threshold = config.get("score_threshold", 60)

        # Quality filters
        self.min_price = config.get("min_price", 5.0)
        self.min_dollar_volume_20d = config.get("min_dollar_volume_20d", 10000000)

        # Risk management
        self.min_risk_reward = config.get("min_risk_reward", 1.5)

        # Signal requirements
        self.macd_histogram_rising_bars = config.get("macd_histogram_rising_bars", 2)
        self.volume_breakout_multiplier = config.get("volume_breakout_multiplier", 1.5)


class MomentumStrategy:
    """Bullish momentum swing trading strategy."""

    def __init__(self, config: StrategyConfig):
        """Initialize strategy with configuration."""
        self.config = config

    def analyze(
        self,
        symbol: str,
        bars: List[Bar],
        meta: Optional[TickerMeta] = None
    ) -> Optional[Signal]:
        """
        Analyze a symbol and generate a signal if conditions are met.

        Args:
            symbol: Ticker symbol
            bars: Historical bar data
            meta: Optional ticker metadata

        Returns:
            Signal object if conditions met, None otherwise
        """
        if not bars or len(bars) < 60:
            logger.debug(f"{symbol}: Insufficient data (need at least 60 bars)")
            return None

        try:
            # Calculate indicators
            calc = IndicatorCalculator(bars)
            ind = calc.get_latest_values()

            # Check if we have all required indicators
            required_indicators = ["price", "sma_50", "ema_9", "ema_21", "rsi", "macd", "macd_signal"]
            if any(ind.get(k) is None for k in required_indicators):
                logger.debug(f"{symbol}: Missing required indicators")
                return None

            # QUALITY FILTERS (from config)
            # Filter 1: Minimum price
            if ind["price"] < self.config.min_price:
                logger.debug(f"{symbol}: Failed - Price ${ind['price']:.2f} below minimum ${self.config.min_price}")
                return None

            # Filter 2: Minimum dollar volume
            if ind.get("avg_dollar_volume_20d"):
                if ind["avg_dollar_volume_20d"] < self.config.min_dollar_volume_20d:
                    logger.debug(f"{symbol}: Failed - Avg dollar volume ${ind['avg_dollar_volume_20d']:,.0f} below minimum ${self.config.min_dollar_volume_20d:,.0f}")
                    return None

            # Apply filters
            signals_hit = []
            score_breakdown = {}

            # 1. Price > 50-SMA (trend confirmation)
            if ind["price"] > ind["sma_50"]:
                signals_hit.append("Price > 50-SMA")
            else:
                logger.debug(f"{symbol}: Failed - Price not above 50-SMA")
                return None

            # 2. 9-EMA > 21-EMA (short-term momentum)
            if ind["ema_9"] > ind["ema_21"]:
                signals_hit.append("9-EMA > 21-EMA")
                score_breakdown["ema"] = self.config.weights["ema"]
            else:
                logger.debug(f"{symbol}: Failed - 9-EMA not above 21-EMA")
                score_breakdown["ema"] = 0

            # 3. RSI in bullish zone (50-65) with slope indicator
            rsi_slope = ind.get("rsi_slope", "→")
            if self.config.rsi_min <= ind["rsi"] <= self.config.rsi_max:
                signals_hit.append(f"RSI={ind['rsi']:.0f}{rsi_slope}")
                # Score based on how centered RSI is in the range
                rsi_center = (self.config.rsi_min + self.config.rsi_max) / 2
                rsi_score = 1 - abs(ind["rsi"] - rsi_center) / (self.config.rsi_max - self.config.rsi_min)
                score_breakdown["rsi"] = rsi_score * self.config.weights["rsi"]
            else:
                logger.debug(f"{symbol}: Failed - RSI {ind['rsi']:.1f} not in range {self.config.rsi_min}-{self.config.rsi_max}")
                return None

            # 4. MACD line > signal AND histogram rising (2 bars)
            macd_bullish = ind["macd"] > ind["macd_signal"]
            histogram_rising = ind.get("histogram_rising", False)
            histogram_rising_bars = self.config.macd_histogram_rising_bars if histogram_rising else 0

            if macd_bullish and histogram_rising:
                signals_hit.append(f"MACD↑ hist+{histogram_rising_bars}bars")
                score_breakdown["macd"] = self.config.weights["macd"]
            elif macd_bullish:
                signals_hit.append("MACD bullish")
                score_breakdown["macd"] = self.config.weights["macd"] * 0.6
            else:
                logger.debug(f"{symbol}: Failed - MACD not bullish")
                return None

            # 5. Volume analysis with ratio display
            volume_score = 0
            volume_ratio = ind.get("volume_ratio")
            if volume_ratio:
                if volume_ratio >= self.config.volume_breakout_multiplier:
                    signals_hit.append(f"Vol={volume_ratio:.1f}×20d")
                    volume_score = self.config.weights["volume"]
                elif volume_ratio > 1.0:
                    signals_hit.append(f"Vol={volume_ratio:.1f}×20d")
                    volume_score = self.config.weights["volume"] * 0.7
                else:
                    volume_score = self.config.weights["volume"] * 0.3

            score_breakdown["volume"] = volume_score

            # 6. Optional ADX check
            if self.config.adx_min > 0 and ind.get("adx"):
                if ind["adx"] >= self.config.adx_min:
                    signals_hit.append(f"ADX > {self.config.adx_min} ({ind['adx']:.1f})")
                else:
                    logger.debug(f"{symbol}: Failed - ADX {ind['adx']:.1f} < {self.config.adx_min}")
                    return None

            # 7. Breakout proximity
            breakout_score = 0
            distance_to_pivot_pct = None
            if ind.get("pivot_high"):
                distance_to_pivot_pct = ((ind["pivot_high"] - ind["price"]) / ind["price"]) * 100
                if distance_to_pivot_pct < 2:  # Within 2% of pivot
                    signals_hit.append(f"Near pivot high ({distance_to_pivot_pct:.1f}%)")
                    breakout_score = self.config.weights["breakout"]
                elif distance_to_pivot_pct < 5:
                    breakout_score = self.config.weights["breakout"] * 0.5

            score_breakdown["breakout"] = breakout_score

            # Calculate total score
            total_score = sum(score_breakdown.values())

            # Check threshold
            if total_score < self.config.score_threshold:
                logger.debug(f"{symbol}: Score {total_score:.1f} below threshold {self.config.score_threshold}")
                return None

            # Calculate risk/reward with labels
            atr = ind.get("atr", ind["price"] * 0.02)  # Fallback to 2% if no ATR
            recent_low = ind.get("recent_low", ind["price"] * 0.97)

            suggested_entry = ind["price"]
            suggested_stop = max(recent_low, ind["price"] - atr)
            suggested_target = ind["price"] * 1.07  # 7% target

            risk = suggested_entry - suggested_stop
            reward = suggested_target - suggested_entry
            risk_reward = reward / risk if risk > 0 else 0

            # Determine stop/target basis labels
            sl_atr_mult = (suggested_entry - suggested_stop) / atr if atr > 0 else 1.0
            stop_basis = f"{sl_atr_mult:.1f}×ATR" if abs(sl_atr_mult - 1.0) < 0.2 else "swing-low"
            target_basis = "+7%"  # Fixed 7% target from config

            # ENFORCE R/R >= 1.5 filter
            if risk_reward < self.config.min_risk_reward:
                logger.debug(f"{symbol}: Failed - R/R {risk_reward:.2f} below minimum {self.config.min_risk_reward}")
                return None

            # Create signal with all new fields
            signal = Signal(
                symbol=symbol,
                timestamp=datetime.now(timezone.utc),
                price=ind["price"],
                score=total_score,
                signals_hit=signals_hit,
                rsi=ind.get("rsi"),
                rsi_slope=rsi_slope,
                ema_9=ind.get("ema_9"),
                ema_21=ind.get("ema_21"),
                sma_50=ind.get("sma_50"),
                macd=ind.get("macd"),
                macd_signal=ind.get("macd_signal"),
                macd_histogram=ind.get("macd_histogram"),
                histogram_rising_bars=histogram_rising_bars,
                volume_avg_20=ind.get("volume_avg_20"),
                current_volume=ind.get("volume"),
                volume_ratio=volume_ratio,
                avg_dollar_volume_20d=ind.get("avg_dollar_volume_20d"),
                atr=atr,
                adx=ind.get("adx"),
                score_breakdown=score_breakdown,
                suggested_entry=suggested_entry,
                suggested_stop=suggested_stop,
                suggested_target=suggested_target,
                stop_basis=stop_basis,
                target_basis=target_basis,
                risk_reward=risk_reward,
                pivot_high=ind.get("pivot_high"),
                recent_low=recent_low,
                distance_to_pivot_pct=distance_to_pivot_pct,
                meta=meta
            )

            logger.info(f"{symbol}: Signal generated - Score: {total_score:.1f}, Signals: {len(signals_hit)}")
            return signal

        except Exception as e:
            logger.error(f"{symbol}: Error analyzing - {e}", exc_info=True)
            return None
