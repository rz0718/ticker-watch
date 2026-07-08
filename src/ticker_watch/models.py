from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

InstrumentType = Literal["us", "hk", "crypto"]


class InstrumentConfig(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    symbol: str
    type: InstrumentType
    name: str | None = None

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        symbol = value.strip().upper()
        if not symbol:
            raise ValueError("symbol cannot be empty")
        return symbol

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class AppConfig(BaseModel):
    refresh_seconds: int = Field(default=60, ge=30)
    provider: Literal["yahoo"] = "yahoo"
    watchlist: list[InstrumentConfig]

    @field_validator("watchlist")
    @classmethod
    def validate_watchlist(cls, value: list[InstrumentConfig]) -> list[InstrumentConfig]:
        if not value:
            raise ValueError("watchlist cannot be empty")
        return value


class Quote(BaseModel):
    symbol: str
    name: str | None = None
    type: InstrumentType
    currency: str | None = None
    price: float | None = None
    previous_close: float | None = None
    change: float | None = None
    change_percent: float | None = None
    market_state: str | None = None
    updated_at: datetime
    source: str = "yfinance"
    error: str | None = None


class QuoteCache(BaseModel):
    updated_at: datetime
    refresh_seconds: int
    source: str
    quotes: list[Quote]
