"""Export functionality for scan results."""

import json
import csv
import logging
from pathlib import Path
from typing import List
from datetime import datetime

from scanner.core.models import Signal, ScanResult

logger = logging.getLogger(__name__)


class Exporter:
    """Export scan results to various formats."""

    @staticmethod
    def export_to_csv(signals: List[Signal], filepath: str) -> None:
        """
        Export signals to CSV file.

        Args:
            signals: List of signals to export
            filepath: Output file path
        """
        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "symbol",
            "timestamp",
            "price",
            "score",
            "signals_hit",
            "rsi",
            "ema_9",
            "ema_21",
            "sma_50",
            "macd",
            "macd_signal",
            "volume_avg_20",
            "current_volume",
            "atr",
            "adx",
            "suggested_entry",
            "suggested_stop",
            "suggested_target",
            "risk_reward",
            "distance_to_pivot_pct"
        ]

        try:
            with open(filepath, "w", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for signal in signals:
                    row = {
                        "symbol": signal.symbol,
                        "timestamp": signal.timestamp.isoformat(),
                        "price": signal.price,
                        "score": round(signal.score, 2),
                        "signals_hit": "; ".join(signal.signals_hit),
                        "rsi": round(signal.rsi, 2) if signal.rsi else "",
                        "ema_9": round(signal.ema_9, 2) if signal.ema_9 else "",
                        "ema_21": round(signal.ema_21, 2) if signal.ema_21 else "",
                        "sma_50": round(signal.sma_50, 2) if signal.sma_50 else "",
                        "macd": round(signal.macd, 4) if signal.macd else "",
                        "macd_signal": round(signal.macd_signal, 4) if signal.macd_signal else "",
                        "volume_avg_20": round(signal.volume_avg_20, 0) if signal.volume_avg_20 else "",
                        "current_volume": round(signal.current_volume, 0) if signal.current_volume else "",
                        "atr": round(signal.atr, 2) if signal.atr else "",
                        "adx": round(signal.adx, 2) if signal.adx else "",
                        "suggested_entry": round(signal.suggested_entry, 2) if signal.suggested_entry else "",
                        "suggested_stop": round(signal.suggested_stop, 2) if signal.suggested_stop else "",
                        "suggested_target": round(signal.suggested_target, 2) if signal.suggested_target else "",
                        "risk_reward": round(signal.risk_reward, 2) if signal.risk_reward else "",
                        "distance_to_pivot_pct": round(signal.distance_to_pivot_pct, 2) if signal.distance_to_pivot_pct else ""
                    }
                    writer.writerow(row)

            logger.info(f"Exported {len(signals)} signals to CSV: {filepath}")

        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")
            raise

    @staticmethod
    def export_to_json(scan_result: ScanResult, filepath: str) -> None:
        """
        Export full scan result to JSON file.

        Args:
            scan_result: ScanResult object
            filepath: Output file path
        """
        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(filepath, "w") as f:
                json.dump(scan_result.model_dump(), f, indent=2, default=str)

            logger.info(f"Exported scan result to JSON: {filepath}")

        except Exception as e:
            logger.error(f"Failed to export JSON: {e}")
            raise

    @staticmethod
    def export_signals_simple(signals: List[Signal], filepath: str) -> None:
        """
        Export simple signal list to JSON.

        Args:
            signals: List of signals
            filepath: Output file path
        """
        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        try:
            data = [s.model_dump() for s in signals]
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(f"Exported {len(signals)} signals to JSON: {filepath}")

        except Exception as e:
            logger.error(f"Failed to export signals JSON: {e}")
            raise

    @staticmethod
    def export_watchlist(signals: List[Signal], filepath: str, format: str = "trading212") -> None:
        """
        Export symbols as a watchlist for trading platforms.

        Args:
            signals: List of signals
            filepath: Output file path
            format: Platform format ('trading212', 'simple')
        """
        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        symbols = [s.symbol for s in signals]

        try:
            if format == "trading212":
                # Trading 212 format: one symbol per line
                with open(filepath, "w") as f:
                    f.write("\n".join(symbols))
            else:
                # Simple comma-separated
                with open(filepath, "w") as f:
                    f.write(",".join(symbols))

            logger.info(f"Exported watchlist ({len(symbols)} symbols) to: {filepath}")

        except Exception as e:
            logger.error(f"Failed to export watchlist: {e}")
            raise
