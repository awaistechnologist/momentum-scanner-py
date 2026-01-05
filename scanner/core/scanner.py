"""Core scanner engine."""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from scanner.core.data_providers.base import MarketDataProvider
from scanner.core.data_providers.alpaca import AlpacaProvider
from scanner.core.data_providers.finnhub import FinnhubProvider
from scanner.core.data_providers.twelvedata import TwelveDataProvider
from scanner.core.data_providers.alphavantage import AlphaVantageProvider
from scanner.core.strategy import MomentumStrategy, StrategyConfig
from scanner.core.ranking import SignalRanker
from scanner.core.models import Signal, ScanResult, ActionableSignal as ActionableSignalModel, RejectedSignal as RejectedSignalModel
from scanner.core.actionable import ActionableFilter, ActionableConfig
from scanner.core.readiness import ReadinessChecker
from scanner.config import Config
from scanner.config.universes import get_universe

logger = logging.getLogger(__name__)


class Scanner:
    """Main scanner engine."""

    def __init__(self, config: Config):
        """
        Initialize scanner with configuration.

        Args:
            config: Configuration object
        """
        self.config = config

        # Initialize data provider
        self.provider = self._init_provider()
        self.fallback_provider = self._init_fallback_provider()

        # Initialize strategy (merge strategy + filters + signal_requirements + risk)
        strategy_dict = dict(config["strategy"])
        if "filters" in config.to_dict():
            strategy_dict.update(config["filters"])
        if "signal_requirements" in config.to_dict():
            strategy_dict.update(config["signal_requirements"])
        if "risk" in config.to_dict() and "min_risk_reward" in config["risk"]:
            strategy_dict["min_risk_reward"] = config["risk"]["min_risk_reward"]

        strategy_config = StrategyConfig(strategy_dict)
        self.strategy = MomentumStrategy(strategy_config)

        # Initialize ranker
        self.ranker = SignalRanker()

        # Initialize actionable filter (optional)
        if "actionable" in config.to_dict():
            self.actionable_filter = ActionableFilter(ActionableConfig.from_dict(config["actionable"]))
        else:
            self.actionable_filter = None

        # Initialize readiness checker (optional)
        if "run_readiness" in config.to_dict():
            self.readiness_checker = ReadinessChecker(config["run_readiness"])
        else:
            self.readiness_checker = None

    def _init_provider(self) -> MarketDataProvider:
        """Initialize primary data provider (default: Alpaca)."""
        provider_name = self.config.get("data.provider", "alpaca")
        # Get API keys from environment (loaded by config)
        import os

        if provider_name == "alpaca":
            api_key = os.getenv("ALPACA_API_KEY")
            api_secret = os.getenv("ALPACA_API_SECRET")
            if not api_key or not api_secret:
                logger.error("Alpaca API credentials not found. Set ALPACA_API_KEY and ALPACA_API_SECRET in .env")
                raise ValueError("Alpaca credentials required")
            return AlpacaProvider(api_key, api_secret)

        elif provider_name == "alphavantage":
            api_key = os.getenv("ALPHAVANTAGE_API_KEY")
            if not api_key:
                logger.error("Alpha Vantage API key not found. Set ALPHAVANTAGE_API_KEY in .env")
                raise ValueError("AlphaVantage API key required")
            return AlphaVantageProvider(api_key)

        elif provider_name == "finnhub":
            api_key = os.getenv("FINNHUB_API_KEY")
            if not api_key:
                logger.error("Finnhub API key not found. Set FINNHUB_API_KEY in .env")
                raise ValueError("Finnhub API key required")
            return FinnhubProvider(api_key)

        elif provider_name == "twelvedata":
            api_key = os.getenv("TWELVEDATA_API_KEY")
            if not api_key:
                logger.error("Twelve Data API key not found. Set TWELVEDATA_API_KEY in .env")
                raise ValueError("TwelveData API key required")
            return TwelveDataProvider(api_key)

        else:
            logger.warning(f"Unknown provider '{provider_name}', using Alpaca as default")
            api_key = os.getenv("ALPACA_API_KEY")
            api_secret = os.getenv("ALPACA_API_SECRET")
            if not api_key or not api_secret:
                logger.error("Alpaca API credentials not found")
                raise ValueError("Alpaca credentials required")
            return AlpacaProvider(api_key, api_secret)

    def _init_fallback_provider(self) -> Optional[MarketDataProvider]:
        """Initialize fallback data provider (optional backup)."""
        fallback_name = self.config.get("data.fallback_provider", None)

        if not fallback_name:
            return None

        import os

        if fallback_name == "alpaca":
            api_key = os.getenv("ALPACA_API_KEY")
            api_secret = os.getenv("ALPACA_API_SECRET")
            if api_key and api_secret:
                return AlpacaProvider(api_key, api_secret)

        elif fallback_name == "alphavantage":
            api_key = os.getenv("ALPHAVANTAGE_API_KEY")
            if api_key:
                return AlphaVantageProvider(api_key)

        elif fallback_name == "finnhub":
            api_key = os.getenv("FINNHUB_API_KEY")
            if api_key:
                return FinnhubProvider(api_key)

        elif fallback_name == "twelvedata":
            api_key = os.getenv("TWELVEDATA_API_KEY")
            if api_key:
                return TwelveDataProvider(api_key)

        return None

    def _get_data_for_symbol(self, symbol: str) -> tuple[str, Optional[list], Optional[dict]]:
        """
        Fetch data for a symbol with fallback.

        Returns:
            Tuple of (symbol, bars, metadata)
        """
        interval = self.config.get("data.interval", "1d")
        lookback = self.config.get("data.lookback_days", 200)

        try:
            # Try primary provider
            bars = self.provider.get_bars(symbol, interval, lookback)
            try:
                meta = self.provider.get_meta(symbol)
            except:
                meta = None

            return symbol, bars, meta

        except Exception as e:
            logger.warning(f"{symbol}: Primary provider failed ({e}), trying fallback...")

            # Try fallback
            if self.fallback_provider:
                try:
                    bars = self.fallback_provider.get_bars(symbol, interval, lookback)
                    try:
                        meta = self.fallback_provider.get_meta(symbol)
                    except:
                        meta = None

                    return symbol, bars, meta

                except Exception as e2:
                    logger.error(f"{symbol}: Fallback provider also failed ({e2})")

            return symbol, None, None

    def scan_symbol(self, symbol: str) -> Optional[Signal]:
        """
        Scan a single symbol.

        Args:
            symbol: Ticker symbol

        Returns:
            Signal if found, None otherwise
        """
        logger.info(f"Scanning {symbol}...")

        _, bars, meta = self._get_data_for_symbol(symbol)

        if not bars:
            logger.warning(f"{symbol}: No data available")
            return None

        # Analyze with strategy
        signal = self.strategy.analyze(symbol, bars, meta)

        return signal

    def scan(
        self,
        symbols: Optional[List[str]] = None,
        max_workers: int = 5
    ) -> ScanResult:
        """
        Scan multiple symbols using batch API requests for efficiency.

        Args:
            symbols: List of symbols to scan (None = use config universe)
            max_workers: Number of parallel workers (used for batch processing)

        Returns:
            ScanResult with all signals
        """
        # Get universe
        if symbols is None:
            universe_lists = self.config.get("universe.lists", [])
            custom_symbols = self.config.get("universe.custom_symbols", [])
            symbols = get_universe(universe_lists, custom_symbols)

        if not symbols:
            logger.warning("No symbols to scan")
            return ScanResult(
                scan_timestamp=datetime.now(timezone.utc),
                universe=[],
                signals=[],
                scanned_count=0,
                passed_count=0
            )

        logger.info(f"Starting scan of {len(symbols)} symbols...")

        signals = []

        # Use batch API if provider supports it (Alpaca)
        if hasattr(self.provider, 'get_bars_batch'):
            signals = self._scan_batch(symbols)
        else:
            # Fallback to parallel individual scans
            signals = self._scan_parallel(symbols, max_workers)

        # Rank signals
        top_n = self.config.get("strategy.top_n", 15)
        ranked_signals = self.ranker.rank_signals(signals, top_n)

        logger.info(f"Scan complete: {len(signals)} signals found from {len(symbols)} symbols")

        # Apply actionable filter if enabled
        actionable_signals = None
        rejected_signals = None
        actionable_count = None

        if self.actionable_filter and self.actionable_filter.config.enabled:
            logger.info("Applying actionable filter...")
            # Get bars dict for volume rising check
            bars_dict = {}
            if hasattr(self.provider, 'get_bars_batch'):
                interval = self.config.get("data.interval", "1d")
                lookback = self.config.get("data.lookback_days", 200)
                try:
                    bars_dict = self.provider.get_bars_batch([s.symbol for s in ranked_signals], interval, lookback)
                except Exception as e:
                    logger.warning(f"Could not fetch bars for volume rising check: {e}")

            actionable_list, rejected_list = self.actionable_filter.filter_signals(ranked_signals, bars_dict)

            # Convert to model types
            actionable_signals = [ActionableSignalModel(**a.__dict__) for a in actionable_list]
            rejected_signals = [RejectedSignalModel(**r.__dict__) for r in rejected_list]
            actionable_count = len(actionable_signals)

            logger.info(f"Actionable filter: {actionable_count} actionable, {len(rejected_signals)} rejected")

        # Determine last bar timestamp from signals
        last_bar_ts = None
        if bars_dict and ranked_signals:
            # Get timestamp from first signal's bars
            first_symbol = ranked_signals[0].symbol
            if first_symbol in bars_dict and bars_dict[first_symbol]:
                last_bar_ts = bars_dict[first_symbol][-1].timestamp

        # Check run readiness
        readiness_status = None
        readiness_message = None
        readiness_can_run = None
        market_open_guidance = None

        if self.readiness_checker and self.readiness_checker.enabled:
            logger.info("Checking run readiness...")
            readiness = self.readiness_checker.check_readiness(last_bar_ts)
            readiness_status = readiness.status.value
            readiness_message = readiness.message
            readiness_can_run = readiness.can_run
            market_open_guidance = readiness.market_open_guidance

            logger.info(f"Readiness: {readiness_status} - {readiness_message}")
            if market_open_guidance:
                logger.info(f"Market guidance: {market_open_guidance}")

            # Record this scan if it's actually running
            if last_bar_ts and readiness.status.value in ["READY", "EARLY", "RE_RUN"]:
                self.readiness_checker.record_scan(last_bar_ts)

        return ScanResult(
            scan_timestamp=datetime.now(timezone.utc),
            universe=symbols,
            signals=ranked_signals,
            scanned_count=len(symbols),
            passed_count=len(signals),
            config_snapshot=self.config.to_dict(),
            mode=self.config.get("mode", "momentum"),
            regime=None,  # TODO: Implement regime detection for "auto" mode
            data_provider=self.config.get("data.provider", "alpaca"),
            timeframe=self.config.get("data.interval", "1d"),
            last_bar_timestamp=last_bar_ts,
            actionable_signals=actionable_signals,
            rejected_signals=rejected_signals,
            actionable_count=actionable_count,
            readiness_status=readiness_status,
            readiness_message=readiness_message,
            readiness_can_run=readiness_can_run,
            market_open_guidance=market_open_guidance
        )

    def _scan_batch(self, symbols: List[str]) -> List[Signal]:
        """Scan symbols using batch API (chunked for large universes)."""
        interval = self.config.get("data.interval", "1d")
        lookback = self.config.get("data.lookback_days", 200)

        # Batch size limit (Alpaca can handle ~100 symbols per request)
        BATCH_SIZE = 100

        # Split into chunks if needed
        chunks = [symbols[i:i + BATCH_SIZE] for i in range(0, len(symbols), BATCH_SIZE)]
        num_chunks = len(chunks)

        if num_chunks > 1:
            logger.info(f"📡 Fetching data in {num_chunks} batches ({BATCH_SIZE} symbols each)...")
        else:
            logger.info(f"📡 Fetching data for {len(symbols)} symbols in 1 API call...")

        # Fetch all bars (in chunks if needed)
        all_bars = {}
        for i, chunk in enumerate(chunks, 1):
            try:
                if num_chunks > 1:
                    logger.info(f"  Batch {i}/{num_chunks}: {len(chunk)} symbols...")
                bars_dict = self.provider.get_bars_batch(chunk, interval, lookback)
                all_bars.update(bars_dict)
            except Exception as e:
                logger.error(f"Batch {i} request failed: {e}")

        # Analyze each symbol
        signals = []
        for symbol in symbols:
            logger.info(f"Scanning {symbol}...")

            bars = all_bars.get(symbol)
            if not bars:
                logger.warning(f"{symbol}: No data available")
                continue

            # Get metadata (no API call for Alpaca)
            try:
                meta = self.provider.get_meta(symbol)
            except:
                meta = None

            # Analyze with strategy
            signal = self.strategy.analyze(symbol, bars, meta)

            if signal:
                signals.append(signal)
                logger.info(f"{symbol}: ✓ Signal found (score: {signal.score:.1f})")
            else:
                logger.debug(f"{symbol}: ✗ No signal")

        return signals

    def _scan_parallel(self, symbols: List[str], max_workers: int) -> List[Signal]:
        """Scan symbols in parallel (fallback for non-batch providers)."""
        signals = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.scan_symbol, symbol): symbol for symbol in symbols}

            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    signal = future.result()
                    if signal:
                        signals.append(signal)
                        logger.info(f"{symbol}: ✓ Signal found (score: {signal.score:.1f})")
                    else:
                        logger.debug(f"{symbol}: ✗ No signal")
                except Exception as e:
                    logger.error(f"{symbol}: Error during scan - {e}")

        return signals
