from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ticker_watch.cache import cache_file_path, is_stale, read_cache, write_cache
from ticker_watch.models import Quote, QuoteCache


@pytest.fixture()
def isolated_cache(monkeypatch: pytest.MonkeyPatch, tmp_path):
    cache_dir = tmp_path / "cache"
    monkeypatch.setenv("TICKER_WATCH_CACHE_DIR", str(cache_dir))
    return cache_dir


def make_cache(updated_at: datetime | None = None) -> QuoteCache:
    now = updated_at or datetime.now(timezone.utc)
    return QuoteCache(
        updated_at=now,
        refresh_seconds=60,
        source="yfinance",
        quotes=[
            Quote(
                symbol="SOXL",
                name="SOXL",
                type="us",
                currency="USD",
                price=71.2,
                previous_close=69.74,
                change=1.46,
                change_percent=2.09,
                market_state="OPEN",
                updated_at=now,
            )
        ],
    )


def test_cache_write_read_round_trip(isolated_cache) -> None:
    cache = make_cache()

    path = write_cache(cache)
    loaded = read_cache()

    assert path == cache_file_path()
    assert loaded == cache


def test_cache_stale_detection(isolated_cache) -> None:
    now = datetime(2026, 7, 8, 10, 0, tzinfo=timezone.utc)
    fresh = make_cache(updated_at=now - timedelta(seconds=149))
    stale = make_cache(updated_at=now - timedelta(seconds=151))

    assert is_stale(fresh, now=now) is False
    assert is_stale(stale, now=now) is True
