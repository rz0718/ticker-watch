from __future__ import annotations

from pathlib import Path


def test_source_does_not_contain_forbidden_api_keywords() -> None:
    forbidden = [
        "place_order",
        "cancel_order",
        "modify_order",
        "unlock_trade",
        "OpenSecTradeContext",
        "ib_insync",
        "moomoo",
        "futu",
    ]
    source_root = Path("src")
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in source_root.rglob("*.py"))

    for keyword in forbidden:
        assert keyword not in source_text
