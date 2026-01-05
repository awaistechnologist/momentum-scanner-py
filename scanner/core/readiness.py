"""Run-time readiness checker for EOD scans."""

import json
import logging
from datetime import datetime, timedelta, time
from pathlib import Path
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import pandas_market_calendars as mcal
    MARKET_CAL_AVAILABLE = True
except ImportError:
    MARKET_CAL_AVAILABLE = False

import pytz

logger = logging.getLogger(__name__)


class ReadinessStatus(Enum):
    """Status of scan readiness."""
    READY = "READY"
    EARLY = "EARLY"
    STALE = "STALE"
    HOLIDAY = "HOLIDAY"
    RE_RUN = "RE_RUN"


@dataclass
class ReadinessResult:
    """Result of readiness check."""
    status: ReadinessStatus
    message: str
    can_run: bool  # Whether scan is allowed (warning only for EARLY/RE_RUN)
    details: Dict[str, any]
    market_open_guidance: Optional[str] = None  # Helpful message about next market open


class ReadinessChecker:
    """Check if it's safe to run EOD scan."""

    def __init__(self, config: Dict):
        """Initialize readiness checker.

        Args:
            config: run_readiness config dict
        """
        self.enabled = config.get("enabled", True)
        self.timezone_str = config.get("timezone", "Europe/London")
        self.us_close_time_str = config.get("us_close_time", "21:00")
        self.buffer_minutes = config.get("buffer_minutes", 30)
        self.exchange_calendar = config.get("exchange_calendar", "NYSE")
        self.scan_history_file = Path(config.get("scan_history_file", ".scan_history.json"))

        # Parse timezone and close time
        self.timezone = pytz.timezone(self.timezone_str)
        hour, minute = map(int, self.us_close_time_str.split(":"))
        self.us_close_time = time(hour, minute)

        # Initialize market calendar
        if MARKET_CAL_AVAILABLE:
            try:
                self.market_calendar = mcal.get_calendar(self.exchange_calendar)
                logger.info(f"Loaded {self.exchange_calendar} market calendar")
            except Exception as e:
                logger.warning(f"Failed to load market calendar: {e}")
                self.market_calendar = None
        else:
            logger.warning("pandas_market_calendars not installed - using basic weekend check")
            self.market_calendar = None

        # Load scan history
        self._scan_history = self._load_scan_history()

    def check_readiness(self, last_bar_timestamp: Optional[datetime] = None) -> ReadinessResult:
        """Check if scanner is ready to run.

        Args:
            last_bar_timestamp: Timestamp of most recent bar from data provider (UTC)

        Returns:
            ReadinessResult with status and message
        """
        if not self.enabled:
            return ReadinessResult(
                status=ReadinessStatus.READY,
                message="Readiness check disabled",
                can_run=True,
                details={}
            )

        # Get current time in London timezone
        now_london = datetime.now(self.timezone)
        logger.info(f"Checking readiness at {now_london.strftime('%Y-%m-%d %H:%M %Z')}")

        # 1. Check if we have bar data at all
        if not last_bar_timestamp:
            return ReadinessResult(
                status=ReadinessStatus.STALE,
                message=f"No bar data available. Check your data provider connection.",
                can_run=False,
                details={}
            )

        last_bar_date = last_bar_timestamp.date()
        logger.info(f"Last available bar: {last_bar_date.strftime('%Y-%m-%d')}")

        # 2. Check if bar is recent (within last 5 trading days)
        last_5_trading_days = []
        check_date = now_london.date()
        for _ in range(10):  # Check last 10 calendar days to find 5 trading days
            if self._is_trading_day(check_date):
                last_5_trading_days.append(check_date)
                if len(last_5_trading_days) >= 5:
                    break
            check_date -= timedelta(days=1)

        if last_bar_date not in last_5_trading_days:
            return ReadinessResult(
                status=ReadinessStatus.STALE,
                message=f"Stale data • Last bar: {last_bar_date.strftime('%d %b')}. More than 5 trading days old. Check feed.",
                can_run=False,
                details={"last_bar_date": last_bar_date}
            )

        # 3. Check if we already scanned this bar
        if self._already_scanned(last_bar_timestamp):
            today_is_trading_day = self._is_trading_day(now_london.date())
            today_ready_time = self._calculate_ready_time(now_london.date())

            # Add market open guidance
            market_open_guidance = self._get_market_open_guidance(now_london)

            # If it's a trading day and we're past ready time, hint that new bar might be coming
            if today_is_trading_day and now_london >= today_ready_time:
                return ReadinessResult(
                    status=ReadinessStatus.RE_RUN,
                    message=f"Already scanned bar from {last_bar_date.strftime('%d %b')}. If expecting today's bar, check if provider has published it yet. Run again if config changed.",
                    can_run=True,
                    details={"last_bar_timestamp": last_bar_timestamp},
                    market_open_guidance=market_open_guidance
                )
            else:
                return ReadinessResult(
                    status=ReadinessStatus.RE_RUN,
                    message=f"Already scanned bar from {last_bar_date.strftime('%d %b')}. Run again only if you changed config.",
                    can_run=True,
                    details={"last_bar_timestamp": last_bar_timestamp},
                    market_open_guidance=market_open_guidance
                )

        # 4. Check if today is a holiday/weekend
        today_is_trading_day = self._is_trading_day(now_london.date())
        if not today_is_trading_day:
            next_trading_day = self._get_next_trading_day(now_london.date())
            market_open_guidance = self._get_market_open_guidance(now_london)
            return ReadinessResult(
                status=ReadinessStatus.HOLIDAY,
                message=f"Market closed today (US holiday/weekend). Scanning bar from {last_bar_date.strftime('%d %b')}. Next session: {next_trading_day.strftime('%a, %d %b')}.",
                can_run=True,
                details={"last_bar_date": last_bar_date, "next_trading_day": next_trading_day},
                market_open_guidance=market_open_guidance
            )

        # 5. All checks passed - ready to scan with helpful context
        today_ready_time = self._calculate_ready_time(now_london.date())

        if last_bar_date == now_london.date():
            # We have today's bar already (running after 21:30)
            message = f"Ready • Fresh EOD bar from {last_bar_date.strftime('%d %b')} (today)"
        elif now_london < today_ready_time:
            # Morning/afternoon scan - have yesterday's bar, today's not ready yet
            message = f"Ready • Scanning bar from {last_bar_date.strftime('%d %b')}. Today's bar available after {today_ready_time.strftime('%H:%M')} London."
        else:
            # After ready time but still showing yesterday's bar - provider might be slow
            message = f"Ready • Scanning bar from {last_bar_date.strftime('%d %b')}. (Today's bar may not be published yet)"

        # Add market open guidance
        market_open_guidance = self._get_market_open_guidance(now_london)

        return ReadinessResult(
            status=ReadinessStatus.READY,
            message=message,
            can_run=True,
            details={"last_bar_date": last_bar_date, "ready_time": today_ready_time},
            market_open_guidance=market_open_guidance
        )

    def record_scan(self, last_bar_timestamp: datetime):
        """Record that a scan was performed for this bar.

        Args:
            last_bar_timestamp: Timestamp of the bar that was scanned
        """
        scan_time = datetime.now(pytz.UTC)
        bar_key = last_bar_timestamp.strftime("%Y-%m-%d")
        self._scan_history[bar_key] = scan_time.isoformat()
        self._save_scan_history()
        logger.info(f"Recorded scan for bar {bar_key}")

    def _is_trading_day(self, date) -> bool:
        """Check if date is a US trading day."""
        if self.market_calendar:
            try:
                # Get schedule for this date
                schedule = self.market_calendar.schedule(start_date=date, end_date=date)
                return len(schedule) > 0
            except Exception as e:
                logger.warning(f"Market calendar check failed: {e}")
                # Fallback to basic weekend check
                return date.weekday() < 5  # Mon-Fri
        else:
            # Basic weekend check (doesn't handle holidays)
            return date.weekday() < 5

    def _get_next_trading_day(self, date):
        """Get next trading day after given date."""
        if self.market_calendar:
            try:
                # Get next 10 days and find first trading day
                end_date = date + timedelta(days=10)
                schedule = self.market_calendar.schedule(start_date=date + timedelta(days=1), end_date=end_date)
                if len(schedule) > 0:
                    return schedule.index[0].date()
            except Exception as e:
                logger.warning(f"Next trading day lookup failed: {e}")

        # Fallback: next weekday
        next_day = date + timedelta(days=1)
        while next_day.weekday() >= 5:  # Skip weekend
            next_day += timedelta(days=1)
        return next_day

    def _get_expected_bar_date(self, now_london: datetime):
        """Determine the date of the most recent completed US session.

        Args:
            now_london: Current time in London timezone

        Returns:
            Date of expected bar
        """
        # US market closes at 21:00 London time (+ buffer)
        ready_time_today = datetime.combine(now_london.date(), self.us_close_time)
        ready_time_today = self.timezone.localize(ready_time_today)
        ready_time_today += timedelta(minutes=self.buffer_minutes)

        if now_london >= ready_time_today:
            # After ready time today - expect today's bar (if today is trading day)
            if self._is_trading_day(now_london.date()):
                return now_london.date()
            else:
                # Today is not trading day, find previous trading day
                return self._get_previous_trading_day(now_london.date())
        else:
            # Before ready time - expect previous trading day's bar
            return self._get_previous_trading_day(now_london.date())

    def _get_previous_trading_day(self, date):
        """Get previous trading day before given date."""
        if self.market_calendar:
            try:
                # Look back 10 days to find last trading day
                start_date = date - timedelta(days=10)
                schedule = self.market_calendar.schedule(start_date=start_date, end_date=date - timedelta(days=1))
                if len(schedule) > 0:
                    return schedule.index[-1].date()
            except Exception as e:
                logger.warning(f"Previous trading day lookup failed: {e}")

        # Fallback: previous weekday
        prev_day = date - timedelta(days=1)
        while prev_day.weekday() >= 5:  # Skip weekend
            prev_day -= timedelta(days=1)
        return prev_day

    def _calculate_ready_time(self, bar_date) -> datetime:
        """Calculate the ready time for a given bar date.

        Args:
            bar_date: Date of the bar

        Returns:
            Datetime in London timezone when scan should be ready
        """
        # US close time + buffer on the bar date
        ready_time = datetime.combine(bar_date, self.us_close_time)
        ready_time = self.timezone.localize(ready_time)
        ready_time += timedelta(minutes=self.buffer_minutes)
        return ready_time

    def _already_scanned(self, last_bar_timestamp: datetime) -> bool:
        """Check if we already scanned this bar.

        Args:
            last_bar_timestamp: Timestamp of the bar

        Returns:
            True if already scanned
        """
        bar_key = last_bar_timestamp.strftime("%Y-%m-%d")
        return bar_key in self._scan_history

    def _get_market_open_guidance(self, now_london: datetime) -> Optional[str]:
        """Generate guidance message about next market open.

        Args:
            now_london: Current time in London timezone

        Returns:
            Guidance message or None
        """
        if not self.market_calendar:
            return None

        try:
            # Get next trading day's schedule
            end_date = now_london.date() + timedelta(days=5)
            schedule = self.market_calendar.schedule(start_date=now_london.date(), end_date=end_date)

            if len(schedule) == 0:
                return None

            # Find next market open
            next_open_utc = None
            for idx, row in schedule.iterrows():
                market_open_utc = row['market_open']
                # Convert to London time
                if market_open_utc.tzinfo is None:
                    market_open_utc = pytz.UTC.localize(market_open_utc)
                market_open_london = market_open_utc.astimezone(self.timezone)

                if market_open_london > now_london:
                    next_open_utc = market_open_london
                    break

            if not next_open_utc:
                return None

            # Calculate time until open
            minutes_to_open = (next_open_utc - now_london).total_seconds() / 60

            # Generate appropriate message based on time window
            if minutes_to_open < 0:
                # Market is currently open
                return f"🇺🇸 US market is OPEN now. Intraday data forming."
            elif minutes_to_open <= 60:
                # Within 1 hour
                return f"🇺🇸 Market opens in {int(minutes_to_open)} mins ({next_open_utc.strftime('%H:%M')} London). Finalize orders soon!"
            elif minutes_to_open <= 300:
                # Within 5 hours
                return f"🇺🇸 Market opens in {int(minutes_to_open//60)}h {int(minutes_to_open%60)}m ({next_open_utc.strftime('%H:%M')} London). Place orders before open."
            elif minutes_to_open <= 1440:
                # Within 24 hours
                return f"Next US session: {next_open_utc.strftime('%a %H:%M')} London."
            else:
                # More than 1 day away
                days_away = int(minutes_to_open // 1440)
                return f"Next US session: {next_open_utc.strftime('%a %d %b, %H:%M')} London ({days_away}d away)."

        except Exception as e:
            logger.warning(f"Failed to get market open guidance: {e}")
            return None

    def _load_scan_history(self) -> Dict[str, str]:
        """Load scan history from file."""
        if self.scan_history_file.exists():
            try:
                with open(self.scan_history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load scan history: {e}")
        return {}

    def _save_scan_history(self):
        """Save scan history to file."""
        try:
            self.scan_history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.scan_history_file, 'w') as f:
                json.dump(self._scan_history, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save scan history: {e}")
