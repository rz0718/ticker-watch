import math
from datetime import datetime, timezone
from typing import Any, Iterable

import yfinance as yf

from ticker_watch.models import InstrumentConfig, Quote


class YahooProvider:
    source = "yfinance"

    def fetch_quotes(self, instruments: Iterable[InstrumentConfig]) -> list[Quote]:
        items = list(instruments)
        if not items:
            return []

        now = datetime.now(timezone.utc)
        symbols = " ".join(item.symbol for item in items)
        try:
            tickers = yf.Tickers(symbols)
        except Exception as exc:
            return [_error_quote(item, str(exc), now) for item in items]

        ticker_map = getattr(tickers, "tickers", {}) or {}
        quotes: list[Quote] = []
        for item in items:
            try:
                ticker = ticker_map.get(item.symbol) or ticker_map.get(item.symbol.upper())
                if ticker is None:
                    raise ValueError("No data returned")
                quotes.append(self._normalize(item, ticker, now))
            except Exception as exc:
                quotes.append(_error_quote(item, str(exc), now))
        return quotes

    def _normalize(self, item: InstrumentConfig, ticker: Any, now: datetime) -> Quote:
        fast_info = _safe_attr(ticker, "fast_info")
        info = _safe_attr(ticker, "info") or {}

        price = _first_number(
            fast_info,
            info,
            keys=(
                "last_price",
                "lastPrice",
                "regularMarketPrice",
                "currentPrice",
                "previousClose",
            ),
        )
        previous_close = _first_number(
            fast_info,
            info,
            keys=("previous_close", "previousClose", "regularMarketPreviousClose"),
        )
        change = _first_number(fast_info, info, keys=("regularMarketChange", "change"))
        change_percent = _first_number(
            fast_info,
            info,
            keys=("regularMarketChangePercent", "regularMarketChangePct", "changePercent"),
        )

        if price is None:
            raise ValueError("No data returned")
        if change is None and previous_close not in (None, 0):
            change = price - previous_close
        if change_percent is None and change is not None and previous_close not in (None, 0):
            change_percent = (change / previous_close) * 100

        return Quote(
            symbol=item.symbol,
            name=item.name or _first_text(info, keys=("shortName", "longName")) or item.symbol,
            type=item.type,
            currency=_first_text(fast_info, info, keys=("currency",)),
            price=price,
            previous_close=previous_close,
            change=change,
            change_percent=change_percent,
            market_state=_first_text(
                fast_info,
                info,
                keys=("market_state", "marketState", "quoteMarketState"),
            ),
            updated_at=now,
            source=self.source,
            error=None,
        )


def _error_quote(item: InstrumentConfig, error: str, now: datetime) -> Quote:
    return Quote(
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
        source=YahooProvider.source,
        error=error,
    )


def _safe_attr(source: Any, name: str) -> Any:
    try:
        return getattr(source, name)
    except Exception:
        return None


def _first_number(*sources: Any, keys: tuple[str, ...]) -> float | None:
    for source in sources:
        for key in keys:
            value = _get_value(source, key)
            number = _coerce_number(value)
            if number is not None:
                return number
    return None


def _first_text(*sources: Any, keys: tuple[str, ...]) -> str | None:
    for source in sources:
        for key in keys:
            value = _get_value(source, key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
    return None


def _get_value(source: Any, key: str) -> Any:
    if source is None:
        return None
    if isinstance(source, dict):
        return source.get(key)
    try:
        return source[key]
    except Exception:
        pass
    try:
        return getattr(source, key)
    except Exception:
        return None


def _coerce_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number
