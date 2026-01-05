"""Utility functions for the scanner."""

import time
import logging
from datetime import datetime, timezone
from functools import wraps
from typing import Callable, Any, Optional, TypeVar, cast
from zoneinfo import ZoneInfo
import hashlib
import json

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: float = 0.1,
    exceptions: tuple = (Exception,)
):
    """
    Retry decorator with exponential backoff and jitter.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        jitter: Random jitter factor (0.0 to 1.0)
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} retries: {e}"
                        )
                        raise

                    # Calculate delay with jitter
                    import random
                    jitter_amount = delay * jitter * random.random()
                    actual_delay = delay + jitter_amount

                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {actual_delay:.2f}s..."
                    )
                    time.sleep(actual_delay)
                    delay *= backoff_factor

            raise last_exception  # type: ignore

        return wrapper
    return decorator


class SimpleCache:
    """Simple in-memory LRU-like cache for function results."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        Initialize cache.

        Args:
            max_size: Maximum number of cached items
            ttl_seconds: Time-to-live for cached items in seconds
        """
        self._cache: dict[str, tuple[Any, float]] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds

    def _make_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Create cache key from function name and arguments."""
        key_data = {
            "func": func_name,
            "args": str(args),
            "kwargs": sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """Set value in cache, evicting old items if needed."""
        # Simple eviction: remove oldest if at capacity
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

        self._cache[key] = (value, time.time())

    def clear(self) -> None:
        """Clear all cached items."""
        self._cache.clear()


# Global cache instance
_global_cache = SimpleCache()


def cached(ttl_seconds: int = 3600):
    """
    Caching decorator for functions.

    Args:
        ttl_seconds: Time-to-live for cached results
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            cache_key = _global_cache._make_key(func.__name__, args, kwargs)

            # Try to get from cache
            cached_value = _global_cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value

            # Compute and cache
            result = func(*args, **kwargs)
            _global_cache.set(cache_key, result)
            return result

        return wrapper
    return decorator


def clear_cache() -> None:
    """Clear the global cache."""
    _global_cache.clear()


def get_timezone(tz_name: str) -> ZoneInfo:
    """
    Get timezone object from name.

    Args:
        tz_name: Timezone name (e.g., 'Europe/London', 'America/New_York')

    Returns:
        ZoneInfo object
    """
    try:
        return ZoneInfo(tz_name)
    except Exception as e:
        logger.warning(f"Invalid timezone '{tz_name}', defaulting to UTC: {e}")
        return ZoneInfo("UTC")


def now_in_timezone(tz_name: str = "UTC") -> datetime:
    """
    Get current datetime in specified timezone.

    Args:
        tz_name: Timezone name

    Returns:
        Current datetime with timezone info
    """
    tz = get_timezone(tz_name)
    return datetime.now(tz)


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
    """
    Format datetime to string.

    Args:
        dt: Datetime object
        fmt: Format string

    Returns:
        Formatted datetime string
    """
    return dt.strftime(fmt)


def parse_datetime(dt_str: str, tz_name: str = "UTC") -> datetime:
    """
    Parse datetime string to datetime object.

    Args:
        dt_str: ISO format datetime string
        tz_name: Timezone to use if not specified in string

    Returns:
        Datetime object with timezone
    """
    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        tz = get_timezone(tz_name)
        dt = dt.replace(tzinfo=tz)
    return dt


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = False
) -> None:
    """
    Setup logging configuration.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
        json_format: Use JSON format for logs
    """
    import sys

    handlers: list[logging.Handler] = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    handlers.append(console_handler)

    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        handlers.append(file_handler)

    # Format
    if json_format:
        import json
        import traceback

        class JsonFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                log_data = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
                if record.exc_info:
                    log_data["exception"] = traceback.format_exception(*record.exc_info)
                return json.dumps(log_data)

        formatter: logging.Formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    for handler in handlers:
        handler.setFormatter(formatter)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=handlers,
        force=True
    )
