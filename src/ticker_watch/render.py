from datetime import datetime

from rich.table import Table

from ticker_watch.cache import is_stale
from ticker_watch.models import Quote, QuoteCache


def render_compact_status(
    cache: QuoteCache,
    *,
    max_symbols: int | None = None,
    now: datetime | None = None,
    show_stale: bool = True,
) -> str:
    quotes = cache.quotes[:max_symbols] if max_symbols else cache.quotes
    parts = [_render_compact_quote(quote) for quote in quotes]
    status = " | ".join(parts)
    if show_stale and is_stale(cache, now=now):
        return f"STALE {status}"
    return status


def render_quotes_table(cache: QuoteCache) -> Table:
    table = Table(
        title=f"Ticker Watch    Last refresh: {_format_datetime(cache.updated_at)}",
        show_lines=False,
    )
    table.add_column("Symbol", no_wrap=True)
    table.add_column("Name")
    table.add_column("Type", no_wrap=True)
    table.add_column("Price", justify="right")
    table.add_column("Change", justify="right")
    table.add_column("Change %", justify="right")
    table.add_column("Currency", no_wrap=True)
    table.add_column("Market State", no_wrap=True)
    table.add_column("Updated", no_wrap=True)
    table.add_column("Status", no_wrap=True)

    for quote in cache.quotes:
        style = _quote_style(quote)
        table.add_row(
            quote.symbol,
            quote.name or quote.symbol,
            quote.type,
            _format_price(quote.price),
            _format_change(quote.change),
            _format_percent(quote.change_percent, signed=True),
            quote.currency or "-",
            quote.market_state or "-",
            _format_datetime(quote.updated_at, time_only=True),
            "ERR" if quote.error else "OK",
            style=style,
        )
    return table


def _render_compact_quote(quote: Quote) -> str:
    symbol = _compact_symbol(quote)
    if quote.error:
        return f"{symbol} ERR"

    price = _format_price(quote.price)
    if quote.change_percent is None:
        return f"{symbol} {price} →-"

    if quote.change_percent > 0:
        arrow = "▲"
    elif quote.change_percent < 0:
        arrow = "▼"
    else:
        arrow = "→"
    return f"{symbol} {price} {arrow}{abs(quote.change_percent):.1f}%"


def _compact_symbol(quote: Quote) -> str:
    if quote.type == "crypto" and quote.symbol.endswith("-USD"):
        return quote.symbol.removesuffix("-USD")
    return quote.symbol


def _format_price(value: float | None) -> str:
    if value is None:
        return "-"
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def _format_change(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:+,.2f}"


def _format_percent(value: float | None, *, signed: bool = False) -> str:
    if value is None:
        return "-"
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{value:.2f}%"


def _format_datetime(value: datetime, *, time_only: bool = False) -> str:
    local = value.astimezone()
    if time_only:
        return local.strftime("%H:%M")
    return local.strftime("%Y-%m-%d %H:%M")


def _quote_style(quote: Quote) -> str | None:
    if quote.error:
        return "yellow"
    if quote.change_percent is None:
        return "dim"
    if quote.change_percent > 0:
        return "green"
    if quote.change_percent < 0:
        return "red"
    return None
