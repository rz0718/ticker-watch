from __future__ import annotations

from datetime import datetime, timezone

import pytest
from typer.testing import CliRunner

from ticker_watch.cache import read_cache
from ticker_watch.cli import app
from ticker_watch.config import init_config
from ticker_watch.daemon import run_daemon_loop
from ticker_watch.models import Quote, QuoteCache


@pytest.fixture()
def isolated_paths(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("TICKER_WATCH_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("TICKER_WATCH_CACHE_DIR", str(tmp_path / "cache"))


def quote(symbol: str = "SOXL") -> Quote:
    now = datetime(2026, 7, 8, 10, 0, tzinfo=timezone.utc)
    return Quote(
        symbol=symbol,
        name=symbol,
        type="us",
        currency="USD",
        price=71.2,
        previous_close=69.74,
        change=1.46,
        change_percent=2.09,
        market_state="OPEN",
        updated_at=now,
    )


def test_daemon_loop_writes_latest_cache(isolated_paths) -> None:
    init_config()

    class FakeProvider:
        source = "yfinance"

        def fetch_quotes(self, instruments):
            return [quote(item.symbol) for item in instruments]

    run_daemon_loop(provider=FakeProvider(), iterations=1, sleep_fn=lambda seconds: None)

    cache = read_cache()
    assert isinstance(cache, QuoteCache)
    assert [item.symbol for item in cache.quotes] == ["SOXL", "SNDK", "BTC-USD", "0700.HK"]


def test_daemon_loop_writes_error_rows_when_provider_raises(isolated_paths) -> None:
    init_config()

    class RaisingProvider:
        source = "yfinance"

        def fetch_quotes(self, instruments):
            raise RuntimeError("provider failed")

    run_daemon_loop(provider=RaisingProvider(), iterations=1, sleep_fn=lambda seconds: None)

    cache = read_cache()
    assert len(cache.quotes) == 4
    assert all(item.error == "provider failed" for item in cache.quotes)
    assert all(item.market_state == "ERROR" for item in cache.quotes)


def test_daemon_status_command_reports_stopped(isolated_paths) -> None:
    result = CliRunner().invoke(app, ["daemon", "status"])

    assert result.exit_code == 0
    assert "stopped" in result.output
