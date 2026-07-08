from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


CACHE_DIR = Path("/tmp/ticker-watch-demo-cache")


def main() -> None:
    now = datetime.now(timezone.utc).isoformat()
    quotes = [
        quote("SOXL", "SOXL", "us", 165.28, -15.1, "USD"),
        quote("SNDK", "SanDisk", "us", 1618.0, -7.3, "USD"),
        quote("BTC-USD", "Bitcoin", "crypto", 62980.0, -0.3, "USD"),
        quote("0700.HK", "Tencent", "hk", 475.6, 3.1, "HKD"),
        quote("7709.HK", "Xiaomi", "hk", 95.76, 4.4, "HKD"),
        quote("3690.HK", "Meituan", "hk", 79.45, 1.4, "HKD"),
    ]
    payload = {
        "updated_at": now,
        "refresh_seconds": 3600,
        "source": "demo",
        "quotes": [{**item, "updated_at": now} for item in quotes],
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / "latest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def quote(
    symbol: str,
    name: str,
    instrument_type: str,
    price: float,
    change_percent: float,
    currency: str,
) -> dict[str, object]:
    previous_close = price / (1 + (change_percent / 100))
    return {
        "symbol": symbol,
        "name": name,
        "type": instrument_type,
        "currency": currency,
        "price": price,
        "previous_close": previous_close,
        "change": price - previous_close,
        "change_percent": change_percent,
        "market_state": "DEMO",
        "source": "demo",
        "error": None,
    }


if __name__ == "__main__":
    main()
