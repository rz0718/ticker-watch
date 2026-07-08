import os
from pathlib import Path

import yaml

from ticker_watch.models import AppConfig, InstrumentConfig, InstrumentType

APP_NAME = "ticker-watch"
CONFIG_FILENAME = "config.yaml"


class ConfigNotFoundError(FileNotFoundError):
    pass


def config_dir_path() -> Path:
    override = os.environ.get("TICKER_WATCH_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_NAME


def config_file_path() -> Path:
    return config_dir_path() / CONFIG_FILENAME


def default_config() -> AppConfig:
    return AppConfig(
        refresh_seconds=60,
        provider="yahoo",
        watchlist=[
            InstrumentConfig(symbol="SOXL", type="us", name="SOXL"),
            InstrumentConfig(symbol="SNDK", type="us", name="SanDisk"),
            InstrumentConfig(symbol="BTC-USD", type="crypto", name="Bitcoin"),
            InstrumentConfig(symbol="0700.HK", type="hk", name="Tencent"),
        ],
    )


def load_config(path: Path | None = None) -> AppConfig:
    config_path = path or config_file_path()
    if not config_path.exists():
        raise ConfigNotFoundError(f"Config not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    return AppConfig.model_validate(data)


def save_config(config: AppConfig, path: Path | None = None) -> Path:
    config_path = path or config_file_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data = config.model_dump(mode="json", exclude_none=True)
    with config_path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(data, file, sort_keys=False)
    return config_path


def init_config(force: bool = False, path: Path | None = None) -> tuple[Path, bool]:
    config_path = path or config_file_path()
    if config_path.exists() and not force:
        return config_path, False
    save_config(default_config(), config_path)
    return config_path, True


def infer_instrument_type(symbol: str) -> InstrumentType:
    normalized = symbol.strip().upper()
    if normalized.endswith("-USD"):
        return "crypto"
    if normalized.endswith(".HK"):
        return "hk"
    return "us"


def add_instrument(
    symbol: str,
    instrument_type: InstrumentType | None = None,
    name: str | None = None,
    path: Path | None = None,
) -> AppConfig:
    config = load_config(path)
    normalized_symbol = symbol.strip().upper()
    resolved_type = instrument_type or infer_instrument_type(normalized_symbol)
    updated = InstrumentConfig(
        symbol=normalized_symbol,
        type=resolved_type,
        name=name or normalized_symbol,
    )

    next_watchlist: list[InstrumentConfig] = []
    replaced = False
    for item in config.watchlist:
        if item.symbol == updated.symbol:
            next_watchlist.append(updated)
            replaced = True
        else:
            next_watchlist.append(item)
    if not replaced:
        next_watchlist.append(updated)

    next_config = AppConfig(
        refresh_seconds=config.refresh_seconds,
        provider=config.provider,
        watchlist=next_watchlist,
    )
    save_config(next_config, path)
    return next_config


def remove_instrument(symbol: str, path: Path | None = None) -> AppConfig:
    config = load_config(path)
    normalized_symbol = symbol.strip().upper()
    next_watchlist = [item for item in config.watchlist if item.symbol != normalized_symbol]
    next_config = AppConfig(
        refresh_seconds=config.refresh_seconds,
        provider=config.provider,
        watchlist=next_watchlist,
    )
    save_config(next_config, path)
    return next_config
