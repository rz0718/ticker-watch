from __future__ import annotations

from datetime import datetime, timezone

import pytest
from typer.testing import CliRunner

from ticker_watch.cache import read_cache, write_cache
from ticker_watch.cli import app
from ticker_watch.models import Quote, QuoteCache


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def isolated_paths(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("TICKER_WATCH_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("TICKER_WATCH_CACHE_DIR", str(tmp_path / "cache"))


def sample_cache() -> QuoteCache:
    now = datetime(2026, 7, 8, 10, 0, tzinfo=timezone.utc)
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


def test_status_reads_cache_without_fetching(runner: CliRunner, isolated_paths) -> None:
    write_cache(sample_cache())

    result = runner.invoke(app, ["status", "--compact"])

    assert result.exit_code == 0
    assert result.output.strip() == "SOXL 71.20 ▲2.1%"


def test_status_reports_missing_cache(runner: CliRunner, isolated_paths) -> None:
    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "no cache yet" in result.output


def test_once_fetches_writes_cache_and_prints_table(runner: CliRunner, isolated_paths, monkeypatch) -> None:
    assert runner.invoke(app, ["init"]).exit_code == 0

    class FakeProvider:
        def fetch_quotes(self, instruments):
            cache = sample_cache()
            return cache.quotes

    monkeypatch.setattr("ticker_watch.app.YahooProvider", lambda: FakeProvider())

    result = runner.invoke(app, ["once"])

    assert result.exit_code == 0
    assert "SOXL" in result.output
    assert read_cache().quotes[0].symbol == "SOXL"
