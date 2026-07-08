from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ticker_watch.models import Quote, QuoteCache
from ticker_watch.render import render_compact_status, render_quotes_table


def quote(
    symbol: str,
    price: float | None,
    change_percent: float | None,
    *,
    type_: str = "us",
    error: str | None = None,
) -> Quote:
    now = datetime(2026, 7, 8, 10, 0, tzinfo=timezone.utc)
    return Quote(
        symbol=symbol,
        name=symbol,
        type=type_,
        currency="USD",
        price=price,
        previous_close=100.0,
        change=None,
        change_percent=change_percent,
        market_state="OPEN" if error is None else "ERROR",
        updated_at=now,
        error=error,
    )


def cache(quotes: list[Quote], updated_at: datetime | None = None) -> QuoteCache:
    return QuoteCache(
        updated_at=updated_at or datetime(2026, 7, 8, 10, 0, tzinfo=timezone.utc),
        refresh_seconds=60,
        source="yfinance",
        quotes=quotes,
    )


def test_compact_status_renders_positive_negative_zero_and_error() -> None:
    rendered = render_compact_status(
        cache(
            [
                quote("SOXL", 71.2, 2.09),
                quote("BTC-USD", 108240.0, -0.4, type_="crypto"),
                quote("SNDK", 68.55, 0.0),
                quote("BAD", None, None, error="No data returned"),
            ]
        )
    )

    assert rendered == "SOXL 71.20 ▲2.1% | BTC 108,240 ▼0.4% | SNDK 68.55 →0.0% | BAD ERR"


def test_compact_status_prefixes_stale_cache() -> None:
    now = datetime(2026, 7, 8, 10, 5, tzinfo=timezone.utc)
    old = now - timedelta(seconds=151)

    rendered = render_compact_status(cache([quote("SOXL", 71.2, 2.09)], updated_at=old), now=now)

    assert rendered.startswith("STALE SOXL")


def test_compact_status_limits_symbols() -> None:
    rendered = render_compact_status(
        cache([quote("SOXL", 71.2, 2.09), quote("SNDK", 68.55, 0.6)]),
        max_symbols=1,
    )

    assert rendered == "SOXL 71.20 ▲2.1%"


def test_compact_status_rotates_limited_symbols() -> None:
    rendered = render_compact_status(
        cache(
            [
                quote("SOXL", 71.2, 2.09),
                quote("SNDK", 68.55, 0.6),
                quote("BTC-USD", 108240.0, -0.4, type_="crypto"),
                quote("0700.HK", 388.4, 0.8),
            ]
        ),
        max_symbols=2,
        now=datetime(1970, 1, 1, 0, 0, 10, tzinfo=timezone.utc),
        show_stale=False,
        rotate=True,
        rotate_seconds=5,
    )

    assert rendered == "BTC 108,240 ▼0.4% | 0700.HK 388.40 ▲0.8%"


def test_compact_status_rotation_wraps_to_first_symbol() -> None:
    rendered = render_compact_status(
        cache(
            [
                quote("SOXL", 71.2, 2.09),
                quote("SNDK", 68.55, 0.6),
                quote("BTC-USD", 108240.0, -0.4, type_="crypto"),
                quote("0700.HK", 388.4, 0.8),
            ]
        ),
        max_symbols=2,
        now=datetime(1970, 1, 1, 0, 0, 15, tzinfo=timezone.utc),
        show_stale=False,
        rotate=True,
        rotate_seconds=5,
    )

    assert rendered == "0700.HK 388.40 ▲0.8% | SOXL 71.20 ▲2.1%"


def test_compact_status_marquee_returns_fixed_width_slice() -> None:
    rendered = render_compact_status(
        cache([quote("SOXL", 71.2, 2.09), quote("SNDK", 68.55, 0.6)]),
        now=datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        show_stale=False,
        marquee=True,
        marquee_width=24,
    )

    assert rendered == "SOXL 71.20 ▲2.1% | SNDK "
    assert len(rendered) == 24


def test_compact_status_marquee_moves_left_over_time() -> None:
    rendered = render_compact_status(
        cache([quote("SOXL", 71.2, 2.09), quote("SNDK", 68.55, 0.6)]),
        now=datetime(1970, 1, 1, 0, 0, 2, tzinfo=timezone.utc),
        show_stale=False,
        marquee=True,
        marquee_width=24,
    )

    assert rendered == "XL 71.20 ▲2.1% | SNDK 68"
    assert len(rendered) == 24


def test_compact_status_marquee_wraps_to_start() -> None:
    rendered = render_compact_status(
        cache([quote("SOXL", 71.2, 2.09)]),
        now=datetime(1970, 1, 1, 0, 0, 19, tzinfo=timezone.utc),
        show_stale=False,
        marquee=True,
        marquee_width=16,
    )

    assert rendered == "SOXL 71.20 ▲2.1%"
    assert len(rendered) == 16


def test_full_table_render_does_not_crash_on_missing_data() -> None:
    table = render_quotes_table(
        cache(
            [
                quote("SOXL", 71.2, 2.09),
                quote("BAD", None, None, error="No data returned"),
            ]
        )
    )

    assert len(table.rows) == 2
