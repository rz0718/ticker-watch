import errno
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol

from ticker_watch.cache import (
    CacheNotFoundError,
    cache_dir_path,
    is_stale,
    log_file_path,
    pid_file_path,
    read_cache,
    write_cache,
)
from ticker_watch.config import load_config
from ticker_watch.models import InstrumentConfig, Quote, QuoteCache
from ticker_watch.yahoo_provider import YahooProvider


class QuoteProvider(Protocol):
    source: str

    def fetch_quotes(self, instruments: list[InstrumentConfig]) -> list[Quote]:
        ...


@dataclass(frozen=True)
class DaemonState:
    running: bool
    pid: int | None
    cache_updated_at: datetime | None
    cache_stale: bool | None


def run_daemon_loop(
    *,
    provider: QuoteProvider | None = None,
    iterations: int | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> None:
    logger = _logger()
    resolved_provider = provider or YahooProvider()
    completed = 0

    while True:
        refresh_seconds = 60
        try:
            config = load_config()
            refresh_seconds = config.refresh_seconds
            now = datetime.now(timezone.utc)
            source = getattr(resolved_provider, "source", "yfinance")
            try:
                quotes = resolved_provider.fetch_quotes(config.watchlist)
            except Exception as exc:
                quotes = _error_quotes(config.watchlist, str(exc), now, source)

            cache = QuoteCache(
                updated_at=now,
                refresh_seconds=config.refresh_seconds,
                source=source,
                quotes=quotes,
            )
            write_cache(cache)
            logger.info("wrote cache with %s quotes", len(quotes))
        except Exception:
            logger.exception("daemon refresh failed")

        completed += 1
        if iterations is not None and completed >= iterations:
            return
        sleep_fn(refresh_seconds)


def start_daemon() -> tuple[int, bool]:
    existing_pid = read_pid()
    if existing_pid and is_process_running(existing_pid):
        return existing_pid, False

    cache_dir_path().mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "ticker_watch.cli", "daemon", "run"]
    with log_file_path().open("a", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    write_pid(process.pid)
    return process.pid, True


def stop_daemon(timeout_seconds: float = 5.0) -> bool:
    pid = read_pid()
    if pid is None:
        return False
    if not is_process_running(pid):
        remove_pid_file()
        return False

    os.kill(pid, signal.SIGTERM)
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if not is_process_running(pid):
            remove_pid_file()
            return True
        time.sleep(0.1)
    remove_pid_file()
    return True


def get_daemon_state() -> DaemonState:
    pid = read_pid()
    running = bool(pid and is_process_running(pid))
    if pid and not running:
        remove_pid_file()
        pid = None

    try:
        cache = read_cache()
        cache_updated_at = cache.updated_at
        cache_stale = is_stale(cache)
    except CacheNotFoundError:
        cache_updated_at = None
        cache_stale = None

    return DaemonState(
        running=running,
        pid=pid,
        cache_updated_at=cache_updated_at,
        cache_stale=cache_stale,
    )


def read_pid(path: Path | None = None) -> int | None:
    pid_path = path or pid_file_path()
    if not pid_path.exists():
        return None
    try:
        return int(pid_path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def write_pid(pid: int, path: Path | None = None) -> Path:
    pid_path = path or pid_file_path()
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(f"{pid}\n", encoding="utf-8")
    return pid_path


def remove_pid_file(path: Path | None = None) -> None:
    pid_path = path or pid_file_path()
    try:
        pid_path.unlink()
    except FileNotFoundError:
        pass


def is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError as exc:
        if exc.errno == errno.ESRCH:
            return False
        return True
    return True


def _error_quotes(
    instruments: list[InstrumentConfig],
    error: str,
    now: datetime,
    source: str,
) -> list[Quote]:
    return [
        Quote(
            symbol=item.symbol,
            name=item.name or item.symbol,
            type=item.type,
            currency=None,
            price=None,
            previous_close=None,
            change=None,
            change_percent=None,
            market_state="ERROR",
            updated_at=now,
            source=source,
            error=error,
        )
        for item in instruments
    ]


def _logger() -> logging.Logger:
    log_path = log_file_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ticker_watch.daemon")
    if not logger.handlers:
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
