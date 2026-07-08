from datetime import datetime, timezone

from ticker_watch.cache import write_cache
from ticker_watch.config import load_config
from ticker_watch.models import AppConfig, QuoteCache
from ticker_watch.yahoo_provider import YahooProvider


def fetch_once(config: AppConfig | None = None, provider: YahooProvider | None = None) -> QuoteCache:
    resolved_config = config or load_config()
    resolved_provider = provider or YahooProvider()
    quotes = resolved_provider.fetch_quotes(resolved_config.watchlist)
    cache = QuoteCache(
        updated_at=datetime.now(timezone.utc),
        refresh_seconds=resolved_config.refresh_seconds,
        source=getattr(resolved_provider, "source", "yfinance"),
        quotes=quotes,
    )
    write_cache(cache)
    return cache
