# ticker-watch Design

## Goal

Build `ticker-watch`, a small read-only terminal CLI that monitors Yahoo Finance quotes with `yfinance`, renders a Rich table for active viewing, and renders a fast one-line cache-backed status suitable for tmux.

## Approach

Use a simple Python package under `src/ticker_watch`. Typer owns the CLI, Pydantic owns config/cache/quote models, YAML stores user config, JSON stores the latest cache, Rich handles table rendering, and `yfinance` is the only market data source.

The daemon uses a PID file in the cache directory for MVP portability. `ticker-watch daemon start` launches a background Python process that runs `ticker-watch daemon run`, reloads config every loop, fetches quotes, writes `latest.json` atomically, and logs to `~/.cache/ticker-watch/ticker-watch.log`.

## Components

- `models.py`: Pydantic models and validation.
- `config.py`: default config, YAML load/save, type inference, add/remove helpers.
- `cache.py`: cache paths, atomic read/write, stale detection.
- `yahoo_provider.py`: yfinance fetch and quote normalization with per-symbol error rows.
- `render.py`: compact status string and Rich table renderers.
- `daemon.py`: loop, PID handling, start/stop/status helpers.
- `cli.py`: Typer command wiring.
- `app.py`: orchestration helpers shared by CLI and daemon.

## Data Flow

`init` writes default config. `once` loads config, fetches Yahoo quotes, writes cache, and prints a table. `daemon run` repeats the same fetch/cache cycle on `refresh_seconds`. `status` only reads cache and formats a single compact line, so tmux can call it frequently without hitting Yahoo.

## Error Handling

Config validation catches empty symbols, too-short refresh intervals, and empty watchlists. Provider failures create `Quote` rows with `error` instead of aborting other symbols. Cache writes are atomic. Missing cache produces a clear one-line message. Stale cache is prefixed with `STALE`.

## Testing

Unit tests mock `yfinance`, isolate config/cache paths with environment variables, and cover config commands, cache read/write/stale detection, compact status rendering, full table rendering, provider normalization, daemon cache writes, error rows, and static source checks for forbidden API keywords.
