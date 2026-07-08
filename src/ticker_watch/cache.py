import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ticker_watch.models import QuoteCache

APP_NAME = "ticker-watch"
CACHE_FILENAME = "latest.json"
LOG_FILENAME = "ticker-watch.log"
PID_FILENAME = "ticker-watch.pid"


class CacheNotFoundError(FileNotFoundError):
    pass


def cache_dir_path() -> Path:
    override = os.environ.get("TICKER_WATCH_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / APP_NAME


def cache_file_path() -> Path:
    return cache_dir_path() / CACHE_FILENAME


def log_file_path() -> Path:
    return cache_dir_path() / LOG_FILENAME


def pid_file_path() -> Path:
    return cache_dir_path() / PID_FILENAME


def write_cache(cache: QuoteCache, path: Path | None = None) -> Path:
    cache_path = path or cache_file_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
    payload = json.dumps(cache.model_dump(mode="json"), indent=2, sort_keys=True)
    temp_path.write_text(payload + "\n", encoding="utf-8")
    temp_path.replace(cache_path)
    return cache_path


def read_cache(path: Path | None = None) -> QuoteCache:
    cache_path = path or cache_file_path()
    if not cache_path.exists():
        raise CacheNotFoundError(f"Cache not found: {cache_path}")
    return QuoteCache.model_validate_json(cache_path.read_text(encoding="utf-8"))


def is_stale(cache: QuoteCache, now: datetime | None = None) -> bool:
    updated_at = _aware(cache.updated_at)
    current = _aware(now or datetime.now(timezone.utc))
    max_age = timedelta(seconds=cache.refresh_seconds * 2.5)
    return current - updated_at > max_age


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
