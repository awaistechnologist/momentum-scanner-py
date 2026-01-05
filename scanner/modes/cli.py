"""CLI mode for on-demand scanning."""

import argparse
import sys
import logging
from pathlib import Path
from typing import Optional

from scanner.config import Config
from scanner.core.scanner import Scanner
from scanner.core.utils import setup_logging, format_datetime
from scanner.integrations.export import Exporter
from scanner.integrations.telegram import TelegramBot

logger = logging.getLogger(__name__)


def print_table(result):
    """Print results as a formatted table."""
    if not result.signals:
        print("\n❌ No signals found.\n")
        return

    # Determine if we should show actionable or all signals
    show_actionable = result.actionable_signals is not None and result.actionable_count > 0

    print(f"\n{'='*150}")
    print(f"📈 MOMENTUM SCANNER RESULTS")
    print(f"{'='*150}")

    # Readiness banner (if enabled)
    if hasattr(result, 'readiness_status') and result.readiness_status:
        status_colors = {
            "READY": "\033[92m",    # Green
            "EARLY": "\033[93m",    # Yellow
            "STALE": "\033[91m",    # Red
            "HOLIDAY": "\033[91m",  # Red
            "RE_RUN": "\033[93m"    # Yellow
        }
        reset_color = "\033[0m"

        status_emoji = {
            "READY": "✅",
            "EARLY": "⏰",
            "STALE": "⚠️",
            "HOLIDAY": "🚫",
            "RE_RUN": "🔄"
        }

        color = status_colors.get(result.readiness_status, "")
        emoji = status_emoji.get(result.readiness_status, "")

        print(f"\n{color}{emoji} READINESS: {result.readiness_status}{reset_color}")
        print(f"{result.readiness_message}")

        # Market open guidance
        if hasattr(result, 'market_open_guidance') and result.market_open_guidance:
            print(f"{result.market_open_guidance}")

        print(f"{'='*150}\n")

    # Provenance header (Tweak #3)
    mode_str = result.mode.upper() if result.mode else "MOMENTUM"
    regime_str = f" | Regime: {result.regime}" if result.regime else ""
    provider_str = result.data_provider.upper() if result.data_provider else "UNKNOWN"
    timeframe_str = result.timeframe if result.timeframe else "1d"
    last_bar_str = f" | Last Bar: {format_datetime(result.last_bar_timestamp)}" if result.last_bar_timestamp else ""

    print(f"Mode: {mode_str}{regime_str} | Data: {provider_str} | Timeframe: {timeframe_str}{last_bar_str}")
    print(f"Scan Time: {format_datetime(result.scan_timestamp)}")
    print(f"Scanned: {result.scanned_count} symbols | Found: {result.passed_count} signals")

    if show_actionable:
        avg_rr = sum(a.signal.risk_reward for a in result.actionable_signals if a.signal.risk_reward) / max(len(result.actionable_signals), 1)
        total_risk_pct = sum(a.risk_dollars for a in result.actionable_signals) / result.actionable_signals[0].signal.price if result.actionable_signals else 0
        print(f"✅ Actionable: {result.actionable_count} trades | Avg R/R: {avg_rr:.1f}")
        print(f"{'='*150}\n")
        _print_actionable_table(result.actionable_signals)

        # Show rejected signals summary
        if result.rejected_signals:
            print(f"\n{'='*150}")
            print(f"❌ REJECTED SIGNALS ({len(result.rejected_signals)})")
            print(f"{'='*150}")
            _print_rejected_table(result.rejected_signals)
    else:
        print(f"{'='*150}\n")
        _print_standard_table(result.signals)


def _print_standard_table(signals):
    """Print standard signal table (no actionable filter)."""
    # Header
    print(f"{'#':<4} {'Symbol':<8} {'Price':<8} {'Score':<6} {'RSI':<8} {'Vol':<9} {'MACD':<12} {'Entry':<9} {'Stop':<12} {'Target':<11} {'R/R':<5}")
    print(f"{'-'*130}")

    # Rows
    for i, signal in enumerate(signals, 1):
        symbol = signal.symbol[:8]
        price = f"${signal.price:.2f}"
        score = f"{signal.score:.0f}"

        # RSI with slope
        rsi_str = f"{signal.rsi:.0f}{signal.rsi_slope}" if signal.rsi and signal.rsi_slope else "-"

        # Volume ratio
        vol_str = f"{signal.volume_ratio:.1f}×20d" if signal.volume_ratio else "-"

        # MACD histogram status
        if signal.histogram_rising_bars and signal.histogram_rising_bars > 0:
            macd_str = f"↑+{signal.histogram_rising_bars}bars"
        else:
            macd_str = "bullish"

        entry = f"${signal.suggested_entry:.2f}" if signal.suggested_entry else "-"

        # Stop with basis
        if signal.suggested_stop and signal.stop_basis:
            stop = f"${signal.suggested_stop:.2f}({signal.stop_basis})"
        else:
            stop = f"${signal.suggested_stop:.2f}" if signal.suggested_stop else "-"

        # Target with basis
        if signal.suggested_target and signal.target_basis:
            target = f"${signal.suggested_target:.2f}({signal.target_basis})"
        else:
            target = f"${signal.suggested_target:.2f}" if signal.suggested_target else "-"

        rr = f"{signal.risk_reward:.1f}" if signal.risk_reward else "-"

        print(f"{i:<4} {symbol:<8} {price:<8} {score:<6} {rsi_str:<8} {vol_str:<9} {macd_str:<12} {entry:<9} {stop:<12} {target:<11} {rr:<5}")

    print(f"{'-'*130}\n")

    # Summary stats
    avg_score = sum(s.score for s in signals) / len(signals)
    avg_rr = sum(s.risk_reward for s in signals if s.risk_reward) / len([s for s in signals if s.risk_reward])
    print(f"Average Score: {avg_score:.1f} | Average R/R: {avg_rr:.1f}")
    print()


def _print_actionable_table(actionable_signals):
    """Print actionable signals with position sizing."""
    # Header with sizing columns
    print(f"{'#':<4} {'Symbol':<8} {'Price':<8} {'Score':<6} {'RSI':<8} {'Vol':<9} {'MACD':<12} {'Stop':<12} {'Target':<11} {'R/R':<5} {'Size':<6} {'Risk$':<8} {'Reward$':<9} {'Notes':<30}")
    print(f"{'-'*150}")

    # Rows
    for i, actionable in enumerate(actionable_signals, 1):
        signal = actionable.signal
        symbol = signal.symbol[:8]
        price = f"${signal.price:.2f}"
        score = f"{signal.score:.0f}"

        # RSI with slope
        rsi_str = f"{signal.rsi:.0f}{signal.rsi_slope}" if signal.rsi and signal.rsi_slope else "-"

        # Volume ratio
        vol_str = f"{signal.volume_ratio:.1f}×20d" if signal.volume_ratio else "-"

        # MACD histogram status
        if signal.histogram_rising_bars and signal.histogram_rising_bars > 0:
            macd_str = f"↑+{signal.histogram_rising_bars}bars"
        else:
            macd_str = "bullish"

        # Stop with basis
        if signal.suggested_stop and signal.stop_basis:
            stop = f"${signal.suggested_stop:.2f}({signal.stop_basis})"[:12]
        else:
            stop = f"${signal.suggested_stop:.2f}" if signal.suggested_stop else "-"

        # Target with basis
        if signal.suggested_target and signal.target_basis:
            target = f"${signal.suggested_target:.2f}({signal.target_basis})"[:11]
        else:
            target = f"${signal.suggested_target:.2f}" if signal.suggested_target else "-"

        rr = f"{signal.risk_reward:.1f}" if signal.risk_reward else "-"

        # Position sizing
        size = f"{actionable.position_size_shares}"
        risk = f"${actionable.risk_dollars:.0f}"
        reward = f"${actionable.reward_dollars:.0f}"

        # Notes
        notes_str = ", ".join(actionable.notes[:2])[:30]

        print(f"{i:<4} {symbol:<8} {price:<8} {score:<6} {rsi_str:<8} {vol_str:<9} {macd_str:<12} {stop:<12} {target:<11} {rr:<5} {size:<6} {risk:<8} {reward:<9} {notes_str:<30}")

    print(f"{'-'*150}\n")

    # Summary
    total_risk = sum(a.risk_dollars for a in actionable_signals)
    total_reward = sum(a.reward_dollars for a in actionable_signals)
    avg_rr = sum(a.signal.risk_reward for a in actionable_signals if a.signal.risk_reward) / max(len(actionable_signals), 1)
    print(f"Total Risk: ${total_risk:.0f} | Total Potential Reward: ${total_reward:.0f} | Avg R/R: {avg_rr:.1f}")
    print()


def _print_rejected_table(rejected_signals):
    """Print rejected signals with reasons."""
    for rejected in rejected_signals[:10]:  # Show top 10 rejected
        reasons_str = ", ".join(rejected.rejection_reasons)
        print(f"  {rejected.symbol:<8} - {reasons_str}")
    if len(rejected_signals) > 10:
        print(f"  ... and {len(rejected_signals) - 10} more")
    print()


def main():
    """CLI main function."""
    parser = argparse.ArgumentParser(
        description="Short-Term Momentum Scanner - CLI Mode"
    )

    # Overrides
    parser.add_argument(
        "--symbols",
        type=str,
        help="Comma-separated list of symbols to scan (overrides config universe)"
    )

    # Export
    parser.add_argument(
        "--export",
        type=str,
        choices=["csv", "json", "both"],
        help="Export format"
    )

    parser.add_argument(
        "--export-path",
        type=str,
        help="Custom export path (default: ./output/)"
    )

    # Notifications
    parser.add_argument(
        "--no-telegram",
        action="store_true",
        help="Disable Telegram notifications"
    )

    # Logging
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of parallel workers (default: 5)"
    )

    args = parser.parse_args()

    # Setup logging
    log_level = "DEBUG" if args.debug else "INFO"
    setup_logging(level=log_level)

    try:
        # Always load config.json from current directory
        config_path = Path("config.json")
        if not config_path.exists():
            logger.error("config.json not found in current directory")
            print("\n❌ Error: config.json not found")
            print("Run: cp scanner/config/config.example.json config.json\n")
            sys.exit(1)

        config = Config.from_file(str(config_path))
        logger.info("Loaded config.json (API keys from .env)")

        # Get symbols
        symbols = None
        if args.symbols:
            symbols = [s.strip().upper() for s in args.symbols.split(",")]
            logger.info(f"Scanning {len(symbols)} custom symbols")

        # Create scanner
        scanner = Scanner(config)

        # Run scan
        print("\n🔍 Starting scan...\n")
        result = scanner.scan(symbols=symbols, max_workers=args.workers)

        # Display results
        print_table(result)

        # Export
        export_path = args.export_path or "./output"
        Path(export_path).mkdir(parents=True, exist_ok=True)

        if args.export in ["csv", "both"]:
            csv_file = f"{export_path}/scan_{result.scan_timestamp.strftime('%Y%m%d_%H%M%S')}.csv"
            Exporter.export_to_csv(result.signals, csv_file)
            print(f"✅ Exported to CSV: {csv_file}")

        if args.export in ["json", "both"]:
            json_file = f"{export_path}/scan_{result.scan_timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            Exporter.export_to_json(result, json_file)
            print(f"✅ Exported to JSON: {json_file}")

        # Telegram notification
        if not args.no_telegram and config.get("notifications.telegram.enabled"):
            try:
                bot_token = config.get("notifications.telegram.bot_token")
                chat_id = config.get("notifications.telegram.chat_id")

                if bot_token and chat_id:
                    bot = TelegramBot(bot_token, chat_id)
                    scan_time_str = format_datetime(result.scan_timestamp)
                    bot.send_simple_summary(result.signals, f"CLI Scan - {scan_time_str}")
                    print("✅ Telegram notification sent")
                else:
                    logger.warning("Telegram credentials not configured")
            except Exception as e:
                logger.error(f"Failed to send Telegram notification: {e}")

        print("\n✅ Scan complete!\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  Scan interrupted by user\n")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
