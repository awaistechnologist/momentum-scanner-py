"""Background worker mode for scheduled scanning."""

import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime

from scanner.config import Config
from scanner.core.scanner import Scanner
from scanner.core.utils import setup_logging, format_datetime
from scanner.integrations.export import Exporter
from scanner.integrations.telegram import TelegramBot

logger = logging.getLogger(__name__)


def run_scheduled_scan(config_path: str):
    """
    Run a scheduled scan.

    Args:
        config_path: Path to configuration file
    """
    try:
        # Load config
        config = Config.from_file(config_path)
        logger.info(f"Loaded configuration from {config_path}")

        # Setup logging from config
        log_level = config.get("logging.level", "INFO")
        log_file = config.get("logging.path")
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        setup_logging(level=log_level, log_file=log_file)

        logger.info("=" * 80)
        logger.info("STARTING SCHEDULED SCAN")
        logger.info("=" * 80)

        # Create scanner
        scanner = Scanner(config)

        # Run scan
        result = scanner.scan(max_workers=5)

        logger.info(f"Scan complete: {result.passed_count} signals from {result.scanned_count} symbols")

        # Export results
        if result.signals:
            # CSV export
            csv_path = config.get("export.csv_path")
            if csv_path:
                Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
                Exporter.export_to_csv(result.signals, csv_path)
                logger.info(f"Exported CSV: {csv_path}")

            # JSON export
            json_path = config.get("export.json_path")
            if json_path:
                Path(json_path).parent.mkdir(parents=True, exist_ok=True)
                Exporter.export_to_json(result, json_path)
                logger.info(f"Exported JSON: {json_path}")

            # Send Telegram notification
            telegram_config = config.get("notifications.telegram", {})
            if telegram_config.get("enabled"):
                try:
                    bot_token = telegram_config.get("bot_token")
                    chat_id = telegram_config.get("chat_id")

                    if bot_token and chat_id:
                        bot = TelegramBot(bot_token, chat_id)

                        # Send summary
                        scan_time = format_datetime(result.scan_timestamp)
                        bot.send_scan_summary(
                            signals=result.signals,
                            scan_time=scan_time,
                            scanned_count=result.scanned_count
                        )

                        logger.info("Telegram notification sent successfully")

                        # Optionally send charts
                        if telegram_config.get("send_charts", False):
                            logger.info("Chart sending not yet implemented")

                    else:
                        logger.warning("Telegram enabled but credentials missing")

                except Exception as e:
                    logger.error(f"Failed to send Telegram notification: {e}", exc_info=True)

        else:
            logger.info("No signals found in this scan")

            # Still notify if configured
            telegram_config = config.get("notifications.telegram", {})
            if telegram_config.get("enabled"):
                try:
                    bot_token = telegram_config.get("bot_token")
                    chat_id = telegram_config.get("chat_id")

                    if bot_token and chat_id:
                        bot = TelegramBot(bot_token, chat_id)
                        scan_time = format_datetime(result.scan_timestamp)
                        bot.send_message(
                            f"*Scheduled Scan Complete*\n\n"
                            f"Time: {bot.escape_markdown(scan_time)}\n"
                            f"Scanned: {result.scanned_count} symbols\n"
                            f"No signals found\\."
                        )
                except Exception as e:
                    logger.error(f"Failed to send Telegram notification: {e}")

        logger.info("=" * 80)
        logger.info("SCAN COMPLETE")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        raise


def main():
    """Worker main function."""
    parser = argparse.ArgumentParser(
        description="Short-Term Momentum Scanner - Background Worker"
    )

    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to config file (JSON)"
    )

    args = parser.parse_args()

    # Initial logging setup (will be overridden by config)
    setup_logging(level="INFO")

    try:
        run_scheduled_scan(args.config)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Worker failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
