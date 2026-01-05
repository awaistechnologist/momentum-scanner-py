"""Configuration management."""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use environment variables directly


class Config:
    """Configuration manager."""

    def __init__(self, config_dict: Dict[str, Any]):
        """Initialize from config dictionary."""
        self._data = config_dict

    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        """Load configuration from JSON file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, "r") as f:
            data = json.load(f)

        # Override with environment variables
        data = cls._apply_env_overrides(data)

        return cls(data)

    @classmethod
    def from_defaults(cls) -> "Config":
        """Create config with default values."""
        return cls({
            "timezone": "Europe/London",
            "universe": {
                "lists": [],
                "custom_symbols": []
            },
            "data": {
                "provider": "alpaca",
                "api_keys": {},
                "fallback_provider": None,
                "interval": "1d",
                "lookback_days": 200
            },
            "strategy": {
                "rsi_min": 50,
                "rsi_max": 65,
                "ema_fast": 9,
                "ema_slow": 21,
                "sma_trend": 50,
                "macd": {"fast": 12, "slow": 26, "signal": 9},
                "volume_window": 20,
                "adx_min": 0,
                "weights": {"ema": 25, "rsi": 20, "macd": 25, "volume": 20, "breakout": 10},
                "score_threshold": 60,
                "top_n": 15
            },
            "risk": {
                "atr_window": 14,
                "tp_pct": 0.07,
                "sl_atr_mult": 1.0
            },
            "notifications": {
                "telegram": {
                    "enabled": False,
                    "bot_token": "",
                    "chat_id": "",
                    "send_charts": True
                }
            },
            "export": {
                "csv_path": "./output/last_scan.csv",
                "json_path": "./output/last_scan.json"
            },
            "scheduler": {
                "enabled": False,
                "run_time_local": "07:00"
            },
            "logging": {
                "level": "INFO",
                "path": "./logs/scanner.log"
            }
        })

    @staticmethod
    def _apply_env_overrides(data: Dict[str, Any]) -> Dict[str, Any]:
        """Override config values with environment variables."""
        # API keys
        if "FINNHUB_API_KEY" in os.environ:
            if "data" not in data:
                data["data"] = {}
            if "api_keys" not in data["data"]:
                data["data"]["api_keys"] = {}
            data["data"]["api_keys"]["finnhub"] = os.environ["FINNHUB_API_KEY"]

        if "TWELVEDATA_API_KEY" in os.environ:
            if "data" not in data:
                data["data"] = {}
            if "api_keys" not in data["data"]:
                data["data"]["api_keys"] = {}
            data["data"]["api_keys"]["twelvedata"] = os.environ["TWELVEDATA_API_KEY"]

        # Telegram
        if "TELEGRAM_BOT_TOKEN" in os.environ:
            if "notifications" not in data:
                data["notifications"] = {}
            if "telegram" not in data["notifications"]:
                data["notifications"]["telegram"] = {}
            data["notifications"]["telegram"]["bot_token"] = os.environ["TELEGRAM_BOT_TOKEN"]

        if "TELEGRAM_CHAT_ID" in os.environ:
            if "notifications" not in data:
                data["notifications"] = {}
            if "telegram" not in data["notifications"]:
                data["notifications"]["telegram"] = {}
            data["notifications"]["telegram"]["chat_id"] = os.environ["TELEGRAM_CHAT_ID"]

        return data

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by key (supports dot notation)."""
        keys = key.split(".")
        value = self._data

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def __getitem__(self, key: str) -> Any:
        """Get config section."""
        return self._data[key]

    def to_dict(self) -> Dict[str, Any]:
        """Get full config as dictionary."""
        return self._data.copy()
