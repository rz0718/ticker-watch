from __future__ import annotations

import pytest
from pydantic import ValidationError

from ticker_watch.config import (
    add_instrument,
    config_file_path,
    default_config,
    infer_instrument_type,
    init_config,
    load_config,
    remove_instrument,
    save_config,
)
from ticker_watch.models import AppConfig, InstrumentConfig


@pytest.fixture()
def isolated_config(monkeypatch: pytest.MonkeyPatch, tmp_path):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("TICKER_WATCH_CONFIG_DIR", str(config_dir))
    return config_dir


def test_default_config_contains_required_symbols(isolated_config) -> None:
    config = default_config()

    assert [item.symbol for item in config.watchlist] == [
        "NVDA",
        "BTC-USD",
        "0700.HK",
    ]
    assert config.refresh_seconds == 60
    assert config.provider == "yahoo"


def test_config_load_save_round_trip(isolated_config) -> None:
    config = AppConfig(
        refresh_seconds=45,
        provider="yahoo",
        watchlist=[InstrumentConfig(symbol="AAPL", type="us", name="Apple")],
    )

    save_config(config)
    loaded = load_config()

    assert loaded == config


def test_init_config_does_not_overwrite_without_force(isolated_config) -> None:
    init_config()
    edited = AppConfig(
        refresh_seconds=45,
        provider="yahoo",
        watchlist=[InstrumentConfig(symbol="AAPL", type="us", name="Apple")],
    )
    save_config(edited)

    path, created = init_config()

    assert path == config_file_path()
    assert created is False
    assert load_config() == edited


def test_init_config_force_overwrites(isolated_config) -> None:
    save_config(
        AppConfig(
            refresh_seconds=45,
            provider="yahoo",
            watchlist=[InstrumentConfig(symbol="AAPL", type="us", name="Apple")],
        )
    )

    path, created = init_config(force=True)

    assert path == config_file_path()
    assert created is True
    assert [item.symbol for item in load_config().watchlist] == [
        "NVDA",
        "BTC-USD",
        "0700.HK",
    ]


@pytest.mark.parametrize(
    ("symbol", "expected"),
    [
        ("BTC-USD", "crypto"),
        ("ETH-USD", "crypto"),
        ("0700.HK", "hk"),
        ("NVDA", "us"),
    ],
)
def test_infer_instrument_type(symbol: str, expected: str) -> None:
    assert infer_instrument_type(symbol) == expected


def test_add_and_remove_instrument(isolated_config) -> None:
    init_config()

    after_add = add_instrument("AAPL", instrument_type="us", name="Apple")
    assert any(item.symbol == "AAPL" and item.name == "Apple" for item in after_add.watchlist)

    after_remove = remove_instrument("AAPL")
    assert all(item.symbol != "AAPL" for item in after_remove.watchlist)


def test_add_instrument_is_idempotent(isolated_config) -> None:
    init_config()

    add_instrument("AAPL")
    config = add_instrument("aapl", instrument_type="us", name="Apple")

    matches = [item for item in config.watchlist if item.symbol == "AAPL"]
    assert len(matches) == 1
    assert matches[0].name == "Apple"


def test_remove_instrument_rejects_empty_watchlist(isolated_config) -> None:
    save_config(
        AppConfig(
            refresh_seconds=60,
            provider="yahoo",
            watchlist=[InstrumentConfig(symbol="SOXL", type="us", name="SOXL")],
        )
    )

    with pytest.raises(ValidationError):
        remove_instrument("SOXL")


def test_config_validation_rejects_empty_watchlist() -> None:
    with pytest.raises(ValidationError):
        AppConfig(refresh_seconds=60, provider="yahoo", watchlist=[])


def test_config_validation_rejects_short_refresh() -> None:
    with pytest.raises(ValidationError):
        AppConfig(
            refresh_seconds=10,
            provider="yahoo",
            watchlist=[InstrumentConfig(symbol="SOXL", type="us")],
        )
