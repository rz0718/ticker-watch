from __future__ import annotations

from ticker_watch import yahoo_provider
from ticker_watch.models import InstrumentConfig
from ticker_watch.yahoo_provider import YahooProvider


class FakeTicker:
    def __init__(self, fast_info: dict, info: dict | None = None) -> None:
        self.fast_info = fast_info
        self.info = info or {}


class FakeTickers:
    def __init__(self, symbols: str) -> None:
        assert symbols == "SOXL BAD"
        self.tickers = {
            "SOXL": FakeTicker(
                {
                    "last_price": 101.5,
                    "previous_close": 100.0,
                    "currency": "USD",
                },
                {
                    "shortName": "SOXL Fund",
                    "marketState": "OPEN",
                },
            )
        }


def test_provider_normalizes_yfinance_response(monkeypatch) -> None:
    monkeypatch.setattr(yahoo_provider.yf, "Tickers", FakeTickers)
    provider = YahooProvider()

    quotes = provider.fetch_quotes(
        [
            InstrumentConfig(symbol="SOXL", type="us", name="SOXL"),
            InstrumentConfig(symbol="BAD", type="us", name="Bad Symbol"),
        ]
    )

    good = quotes[0]
    assert good.symbol == "SOXL"
    assert good.name == "SOXL"
    assert good.price == 101.5
    assert good.previous_close == 100.0
    assert good.change == 1.5
    assert good.change_percent == 1.5
    assert good.currency == "USD"
    assert good.market_state == "OPEN"
    assert good.error is None

    bad = quotes[1]
    assert bad.symbol == "BAD"
    assert bad.price is None
    assert bad.market_state == "ERROR"
    assert bad.error == "No data returned"


def test_provider_returns_error_rows_when_yfinance_raises(monkeypatch) -> None:
    def raise_error(symbols: str):
        raise RuntimeError("network unavailable")

    monkeypatch.setattr(yahoo_provider.yf, "Tickers", raise_error)
    provider = YahooProvider()

    quotes = provider.fetch_quotes([InstrumentConfig(symbol="SOXL", type="us", name="SOXL")])

    assert len(quotes) == 1
    assert quotes[0].symbol == "SOXL"
    assert quotes[0].error == "network unavailable"
    assert quotes[0].market_state == "ERROR"
