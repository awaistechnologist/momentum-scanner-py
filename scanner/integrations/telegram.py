"""Telegram bot integration for notifications."""

import logging
import io
from typing import List, Optional
import requests

from scanner.core.models import Signal

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot for sending scan notifications."""

    BASE_URL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram bot.

        Args:
            bot_token: Telegram bot token
            chat_id: Target chat ID
        """
        self.bot_token = bot_token
        self.chat_id = chat_id

    def _make_request(self, method: str, data: dict = None, files: dict = None) -> dict:
        """Make request to Telegram API."""
        url = self.BASE_URL.format(token=self.bot_token, method=method)

        try:
            if files:
                response = requests.post(url, data=data, files=files, timeout=30)
            else:
                response = requests.post(url, json=data, timeout=30)

            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.error(f"Telegram API request failed: {e}")
            raise

    def send_message(self, text: str, parse_mode: str = "MarkdownV2") -> bool:
        """
        Send text message to Telegram.

        Args:
            text: Message text
            parse_mode: Parse mode (MarkdownV2, HTML, or None)

        Returns:
            True if successful
        """
        # Split long messages (Telegram limit is 4096 chars)
        max_length = 4000
        if len(text) > max_length:
            chunks = [text[i:i + max_length] for i in range(0, len(text), max_length)]
            for chunk in chunks:
                self._send_chunk(chunk, parse_mode)
            return True
        else:
            return self._send_chunk(text, parse_mode)

    def _send_chunk(self, text: str, parse_mode: str = "MarkdownV2") -> bool:
        """Send a single message chunk."""
        data = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }

        try:
            result = self._make_request("sendMessage", data=data)
            return result.get("ok", False)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    def send_photo(self, photo_bytes: bytes, caption: str = None) -> bool:
        """
        Send photo to Telegram.

        Args:
            photo_bytes: Image bytes
            caption: Optional caption

        Returns:
            True if successful
        """
        data = {"chat_id": self.chat_id}
        if caption:
            data["caption"] = caption
            data["parse_mode"] = "MarkdownV2"

        files = {"photo": ("chart.png", io.BytesIO(photo_bytes), "image/png")}

        try:
            result = self._make_request("sendPhoto", data=data, files=files)
            return result.get("ok", False)
        except Exception as e:
            logger.error(f"Failed to send photo: {e}")
            return False

    @staticmethod
    def escape_markdown(text: str) -> str:
        """
        Escape special characters for MarkdownV2.

        Args:
            text: Text to escape

        Returns:
            Escaped text
        """
        # Characters that need escaping in MarkdownV2
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text

    def format_signal_message(self, signal: Signal) -> str:
        """
        Format a signal into Telegram message.

        Args:
            signal: Signal to format

        Returns:
            Formatted message with MarkdownV2
        """
        # Build message
        symbol = self.escape_markdown(signal.symbol)
        price = signal.price
        score = signal.score
        signals_hit = self.escape_markdown(", ".join(signal.signals_hit[:3]))  # Top 3 signals

        msg = f"*{symbol}* @ {price:.2f}\n"
        msg += f"📊 Score: *{score:.1f}*\n"
        msg += f"✅ {signals_hit}\n"

        # RSI
        if signal.rsi:
            msg += f"RSI: {signal.rsi:.1f} "

        # Volume
        if signal.current_volume and signal.volume_avg_20:
            vol_ratio = signal.current_volume / signal.volume_avg_20
            msg += f"Vol: {vol_ratio:.1f}x\n"
        else:
            msg += "\n"

        # Entry/Stop/Target
        if signal.suggested_entry and signal.suggested_stop and signal.suggested_target:
            msg += f"🎯 Entry: {signal.suggested_entry:.2f}\n"
            msg += f"🛑 Stop: {signal.suggested_stop:.2f}\n"
            msg += f"💰 Target: {signal.suggested_target:.2f}\n"

            if signal.risk_reward:
                msg += f"R/R: {signal.risk_reward:.1f}\n"

        return msg

    def send_scan_summary(
        self,
        signals: List[Signal],
        scan_time: str,
        scanned_count: int
    ) -> bool:
        """
        Send scan summary with top signals.

        Args:
            signals: List of signals
            scan_time: Scan timestamp
            scanned_count: Number of symbols scanned

        Returns:
            True if successful
        """
        # Header
        header = f"*📈 Momentum Scanner Results*\n"
        header += f"🕐 {self.escape_markdown(scan_time)}\n"
        header += f"Scanned: {scanned_count} \\| Found: {len(signals)}\n"
        header += "━━━━━━━━━━━━━━━━━━━━\n\n"

        # Send header
        self.send_message(header)

        # Send top signals (max 10)
        for i, signal in enumerate(signals[:10], 1):
            msg = f"*\\#{i}\\. {self.format_signal_message(signal)}*\n"
            msg += "━━━━━━━━━━━━━━━━━━━━\n"
            self.send_message(msg)

        return True

    def send_simple_summary(self, signals: List[Signal], title: str = "Scan Results") -> bool:
        """
        Send simplified summary message.

        Args:
            signals: List of signals
            title: Message title

        Returns:
            True if successful
        """
        msg = f"*{self.escape_markdown(title)}*\n\n"

        if not signals:
            msg += "No signals found\\.\n"
        else:
            msg += f"Found *{len(signals)}* signals:\n\n"

            for i, signal in enumerate(signals[:15], 1):
                symbol = self.escape_markdown(signal.symbol)
                msg += f"{i}\\. *{symbol}* \\- Score: {signal.score:.1f} \\- ${signal.price:.2f}\n"

        return self.send_message(msg)
