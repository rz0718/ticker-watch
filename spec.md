# Spec: `ticker-watch` — Yahoo Finance Terminal Price Monitor

## 1. Goal

Build a simple terminal CLI tool called `ticker-watch`.

The tool monitors configured financial instruments using Yahoo Finance / `yfinance` and shows prices in terminal.

The important use case is:

> I want to keep working in terminal with Claude Code, Hermes agents, shell, vim, or other tools, while a compact price line remains visible by default.

The MVP should be simple, read-only, and use only public market data.

No broker API.  
No trading.  
No Moomoo.  
No IBKR.  
No portfolio.  
No account login.

---

## 2. Core design

The tool should support two display modes:

### 2.1 Full-screen mode

Command:

```bash
ticker-watch watch
```

Shows a live Rich table in terminal.

Useful when I want to actively watch prices.

### 2.2 Compact status-line mode

Command:

```bash
ticker-watch status
```

Prints a one-line compact summary.

Example:

```text
SOXL 71.20 ▲2.1% | BTC 108,240 ▼0.4% | SNDK 68.55 ▲0.6% | 0700.HK 388.4 ▲0.8%
```

This is designed for `tmux` status bar, so prices stay visible while I use the terminal normally.

---

## 3. Recommended terminal integration

Use `tmux`.

Example `~/.tmux.conf`:

```bash
set -g status-right "#(ticker-watch status --compact)"
set -g status-interval 15
```

This means the terminal status bar updates every 15 seconds, but the actual Yahoo Finance fetch should still happen only every 60 seconds through the daemon/cache design.

---

## 4. Data source

Use `yfinance` only for MVP.

Supported examples:

```text
SOXL      US ETF
SNDK      US stock
BTC-USD   Crypto
0700.HK   Hong Kong stock
9988.HK   Hong Kong stock
```

Do not implement:

```text
Moomoo
IBKR
FMP
Finnhub
Polygon
Investing.com
Broker login
Portfolio access
Trading
Order management
```

Extended-hours / overnight price is not required in MVP.

If `yfinance` exposes extended-hours data later, the architecture may support it, but for now display only regular/latest available Yahoo price.

---

## 5. CLI commands

Implement these commands:

```bash
ticker-watch init
ticker-watch once
ticker-watch watch
ticker-watch status
ticker-watch add SYMBOL
ticker-watch remove SYMBOL
ticker-watch list
ticker-watch daemon start
ticker-watch daemon stop
ticker-watch daemon status
```

### 5.1 `ticker-watch init`

Creates default config:

```bash
~/.config/ticker-watch/config.yaml
```

Default config:

```yaml
refresh_seconds: 60
provider: yahoo

watchlist:
  - symbol: NVDA
    type: us
    name: NVIDIA

  - symbol: BTC-USD
    type: crypto
    name: Bitcoin

  - symbol: 0700.HK
    type: hk
    name: Tencent
```

If config already exists, do not overwrite unless `--force` is passed.

### 5.2 `ticker-watch once`

Fetches quotes once from Yahoo Finance and prints a Rich table.

Useful for debugging.

### 5.3 `ticker-watch watch`

Runs a live Rich table.

Should refresh every `refresh_seconds`, default 60 seconds.

Columns:

```text
Symbol
Name
Type
Price
Change
Change %
Currency
Market State
Updated
Status
```

### 5.4 `ticker-watch status`

Reads latest cached quote data and prints a compact one-line summary.

It should be very fast because it is designed for tmux.

Default behavior:

```bash
ticker-watch status
```

Output:

```text
SOXL 71.20 ▲2.1% | BTC 108,240 ▼0.4% | SNDK 68.55 ▲0.6%
```

Options:

```bash
ticker-watch status --compact
ticker-watch status --max-symbols 5
ticker-watch status --show-stale
```

If cache is missing:

```text
ticker-watch: no cache yet, run `ticker-watch daemon start` or `ticker-watch once`
```

If cache is stale:

```text
STALE SOXL 71.20 ▲2.1% | BTC 108,240 ▼0.4%
```

### 5.5 `ticker-watch add SYMBOL`

Adds a symbol to config.

Examples:

```bash
ticker-watch add SOXL --type us
ticker-watch add BTC-USD --type crypto
ticker-watch add 0700.HK --type hk
```

If `--type` is omitted, infer type:

```text
BTC-USD / ETH-USD / *-USD  -> crypto
*.HK                       -> hk
otherwise                  -> us
```

### 5.6 `ticker-watch remove SYMBOL`

Removes symbol from config.

Example:

```bash
ticker-watch remove SOXL
```

### 5.7 `ticker-watch list`

Shows configured watchlist.

### 5.8 `ticker-watch daemon start`

Starts background fetch loop.

The daemon should:

```text
1. Load config
2. Fetch quotes from Yahoo Finance every refresh_seconds
3. Write latest normalized quotes to cache
4. Continue running even if one symbol fails
```

### 5.9 `ticker-watch daemon stop`

Stops daemon.

Implementation can use either:

```text
systemd user service
```

or a simple PID file in MVP.

Preferred: systemd user service if running on Linux / Raspberry Pi.

### 5.10 `ticker-watch daemon status`

Shows whether daemon is running and when cache was last updated.

---

## 6. Cache design

Use cache file:

```bash
~/.cache/ticker-watch/latest.json
```

Daemon writes this file every successful refresh.

`ticker-watch status` should read this file instead of calling Yahoo Finance directly.

Reason:

```text
tmux status may refresh frequently
Yahoo fetch should only happen once per minute
status command must be fast
```

Example cache format:

```json
{
  "updated_at": "2026-07-08T10:30:00+08:00",
  "refresh_seconds": 60,
  "source": "yfinance",
  "quotes": [
    {
      "symbol": "SOXL",
      "name": "SOXL",
      "type": "us",
      "currency": "USD",
      "price": 71.2,
      "previous_close": 69.74,
      "change": 1.46,
      "change_percent": 2.09,
      "market_state": "OPEN",
      "updated_at": "2026-07-08T10:30:00+08:00",
      "error": null
    }
  ]
}
```

If a symbol fails, still write an entry:

```json
{
  "symbol": "BAD",
  "name": "BAD",
  "type": "us",
  "currency": null,
  "price": null,
  "previous_close": null,
  "change": null,
  "change_percent": null,
  "market_state": "ERROR",
  "updated_at": "2026-07-08T10:30:00+08:00",
  "error": "No data returned"
}
```

---

## 7. Data models

Use Pydantic models.

### 7.1 Config model

```python
class InstrumentConfig(BaseModel):
    symbol: str
    type: Literal["us", "hk", "crypto"]
    name: str | None = None


class AppConfig(BaseModel):
    refresh_seconds: int = 60
    provider: Literal["yahoo"] = "yahoo"
    watchlist: list[InstrumentConfig]
```

Validation:

```text
refresh_seconds >= 30
watchlist cannot be empty
symbol cannot be empty
```

### 7.2 Quote model

```python
class Quote(BaseModel):
    symbol: str
    name: str | None = None
    type: Literal["us", "hk", "crypto"]
    currency: str | None = None

    price: float | None = None
    previous_close: float | None = None
    change: float | None = None
    change_percent: float | None = None

    market_state: str | None = None
    updated_at: datetime
    source: str = "yfinance"
    error: str | None = None
```

### 7.3 Cache model

```python
class QuoteCache(BaseModel):
    updated_at: datetime
    refresh_seconds: int
    source: str
    quotes: list[Quote]
```

---

## 8. Yahoo provider behavior

Create `YahooProvider`.

Responsibilities:

```text
- Fetch all configured symbols
- Normalize raw Yahoo/yfinance data into Quote models
- Never throw for one bad symbol
- Return error Quote for failed symbol
```

Suggested implementation approach:

```python
import yfinance as yf

tickers = yf.Tickers("SOXL SNDK BTC-USD 0700.HK")
```

For each symbol, try to extract:

```text
last price
previous close
currency
market state
regular market change
regular market change percent
```

Fallback calculation:

```text
change = price - previous_close
change_percent = change / previous_close * 100
```

If `previous_close` is missing, show change as `-`.

Timeouts:

```text
Provider should not hang forever.
Use reasonable timeout if supported.
```

If Yahoo/yfinance fails:

```text
Show error in Quote.error
Continue other symbols
```

---

## 9. Rendering

Use `rich`.

### 9.1 Full table

Positive change:

```text
green
```

Negative change:

```text
red
```

Unavailable:

```text
dim
```

Error:

```text
yellow or red status
```

Example:

```text
Ticker Watch                                  Last refresh: 2026-07-08 10:30 SGT

Symbol    Name      Type    Price      Chg      Chg %    Currency    Market    Updated    Status
SOXL      SOXL      us      71.20      +1.46    +2.09%   USD         OPEN      10:30      OK
BTC-USD   Bitcoin   crypto  108240.0   -430.0   -0.40%   USD         24/7      10:30      OK
0700.HK   Tencent   hk      388.40     +3.20    +0.83%   HKD         CLOSED    10:30      OK
```

### 9.2 Compact status rendering

Rules:

```text
Show symbol, price, arrow, percent change.
Use ▲ for positive.
Use ▼ for negative.
Use → for unchanged or unknown.
Separate symbols with " | ".
For crypto symbols, optionally shorten BTC-USD to BTC.
```

Example:

```text
SOXL 71.20 ▲2.1% | BTC 108,240 ▼0.4% | SNDK 68.55 ▲0.6% | 0700.HK 388.4 ▲0.8%
```

If error:

```text
SOXL ERR | BTC 108,240 ▼0.4%
```

If stale cache:

```text
STALE SOXL 71.20 ▲2.1% | BTC 108,240 ▼0.4%
```

Stale means:

```text
now - cache.updated_at > refresh_seconds * 2.5
```

---

## 10. Daemon design

For MVP, implement a simple foreground daemon command first:

```bash
ticker-watch daemon start
```

It can run in foreground initially.

Later add systemd user service support.

Daemon loop:

```python
while True:
    config = load_config()
    quotes = provider.fetch_quotes(config.watchlist)
    write_cache(QuoteCache(...))
    sleep(config.refresh_seconds)
```

Requirements:

```text
- Reload config on each loop so adding/removing symbols takes effect automatically.
- Atomic cache writes: write to temp file then rename.
- Log errors to ~/.cache/ticker-watch/ticker-watch.log
- Do not crash if one symbol fails.
- If all symbols fail, write cache with error rows.
```

---

## 11. Systemd user service

Add a command or documentation for Linux / Raspberry Pi:

Service file path:

```bash
~/.config/systemd/user/ticker-watch.service
```

Service content:

```ini
[Unit]
Description=ticker-watch Yahoo Finance quote daemon
After=network-online.target

[Service]
Type=simple
ExecStart=%h/.local/bin/ticker-watch daemon run
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

Commands:

```bash
systemctl --user daemon-reload
systemctl --user enable --now ticker-watch.service
systemctl --user status ticker-watch.service
```

The CLI may expose helper command later:

```bash
ticker-watch service install
ticker-watch service uninstall
```

Not required in MVP.

---

## 12. Project structure

```text
ticker-watch/
  pyproject.toml
  README.md
  spec.md
  src/
    ticker_watch/
      __init__.py
      cli.py
      config.py
      models.py
      yahoo_provider.py
      cache.py
      daemon.py
      render.py
      app.py
  tests/
    test_config.py
    test_cli_config_commands.py
    test_cache.py
    test_render_status.py
    test_yahoo_provider_mapping.py
    test_daemon.py
```

---

## 13. Dependencies

Use:

```text
typer
rich
pydantic
pyyaml
yfinance
pytest
```

Optional:

```text
platformdirs
```

`platformdirs` can be used to locate config/cache directories cleanly.

---

## 14. Packaging

Use `pyproject.toml`.

CLI entrypoint:

```toml
[project.scripts]
ticker-watch = "ticker_watch.cli:app"
```

Install locally:

```bash
pip install -e .
```

---

## 15. Testing requirements

Do not use live Yahoo Finance calls in unit tests.

Tests should mock provider output.

Required tests:

```text
1. Config load/save works.
2. Default config contains NVDA, BTC-USD, 0700.HK.
3. Add symbol works.
4. Remove symbol works.
5. Type inference works:
   - BTC-USD -> crypto
   - 0700.HK -> hk
   - NVDA -> us
6. Cache write/read works.
7. Cache stale detection works.
8. Compact status output renders positive, negative, zero, and error quotes.
9. Full table render does not crash on missing data.
10. Daemon loop writes latest.json using mocked provider.
11. Bad symbol creates error Quote instead of crashing.
```

---

## 16. Security and safety requirements

Hard requirements:

```text
- No broker API.
- No account login.
- No trading.
- No order placement.
- No order cancellation.
- No portfolio access.
- No API keys required.
- No secrets stored.
```

Add grep-style tests or simple static checks to ensure source code does not contain:

```text
place_order
cancel_order
modify_order
unlock_trade
OpenSecTradeContext
ib_insync
moomoo
futu
```

This is intentionally over-strict for MVP.

---

## 17. Claude Code Goal Mode prompt

Use this:

```text
/goal Build a simple Python CLI called ticker-watch using Yahoo Finance/yfinance as the only data source for now.

Goal:
The tool monitors configured financial instruments and can show prices in terminal while I continue working with Claude Code, Hermes agents, vim, or normal shell commands.

Core requirement:
Support two display modes:
1. Full-screen watch mode.
2. Compact one-line status mode suitable for tmux status bar.

Data source:
- Use yfinance only for MVP.
- Support US stocks/ETFs, HK stocks, and crypto.
- Examples: SOXL, SNDK, BTC-USD, 0700.HK.
- Do not implement Moomoo, IBKR, FMP, Finnhub, Polygon, or Investing.com.
- Do not implement overnight price for now.
- Do not implement broker login, portfolio access, or trading.

Commands:
- ticker-watch init
- ticker-watch once
- ticker-watch watch
- ticker-watch status
- ticker-watch add SYMBOL
- ticker-watch remove SYMBOL
- ticker-watch list
- ticker-watch daemon start
- ticker-watch daemon stop
- ticker-watch daemon status

Config:
Use ~/.config/ticker-watch/config.yaml

Default config:
refresh_seconds: 60
provider: yahoo

watchlist:
  - symbol: NVDA
    type: us
    name: NVIDIA
  - symbol: BTC-USD
    type: crypto
    name: Bitcoin
  - symbol: 0700.HK
    type: hk
    name: Tencent

Cache:
- Daemon writes latest quotes to ~/.cache/ticker-watch/latest.json.
- ticker-watch status reads latest.json and prints one compact line.
- ticker-watch watch can fetch live directly or read from daemon cache.
- If cache is stale, show STALE indicator.
- If a symbol failed, show ERR for that symbol but do not crash.

Compact status output example:
SOXL 71.20 ▲2.1% | BTC 108,240 ▼0.4% | SNDK 68.55 ▲0.6% | 0700.HK 388.4 ▲0.8%

Full table output:
Use rich to show:
- Symbol
- Name
- Type
- Price
- Change
- Change %
- Currency
- Market State
- Last Update
- Status

Terminal integration:
Add README section for tmux:

set -g status-right "#(ticker-watch status --compact)"
set -g status-interval 15

Implementation:
Use Python with:
- typer
- rich
- pydantic
- pyyaml
- yfinance
- pytest

Project structure:
src/ticker_watch/
  cli.py
  config.py
  models.py
  yahoo_provider.py
  cache.py
  daemon.py
  render.py
  app.py

Tests:
- config load/save
- default config
- add/remove/list
- type inference
- cache read/write
- stale cache detection
- compact status output
- full table render
- provider normalization with mocked yfinance response
- daemon writes latest.json
- failed quote creates error row instead of crashing

Security:
- No broker APIs.
- No Moomoo.
- No IBKR.
- No account access.
- No portfolio access.
- No trading.
- No API keys.
- No secrets.

After each milestone, run tests and fix issues before continuing.
```

---

## 18. Implementation milestones

### Milestone 1: Scaffold

Deliver:

```text
pyproject.toml
src/ticker_watch/
CLI entrypoint
README.md
```

Acceptance:

```bash
ticker-watch --help
```

works.

### Milestone 2: Config

Deliver:

```text
init
list
add
remove
config load/save
```

Acceptance:

```bash
ticker-watch init
ticker-watch list
ticker-watch add AAPL --type us
ticker-watch remove AAPL
```

works.

### Milestone 3: Yahoo provider

Deliver:

```text
YahooProvider
Quote normalization
once command
```

Acceptance:

```bash
ticker-watch once
```

prints a table for NVDA, BTC-USD, and 0700.HK.

### Milestone 4: Cache and status

Deliver:

```text
latest.json cache
status command
compact renderer
stale detection
```

Acceptance:

```bash
ticker-watch status
```

prints one-line output from cache.

### Milestone 5: Daemon

Deliver:

```text
daemon start
daemon status
daemon stop if feasible
cache writing loop
```

Acceptance:

```bash
ticker-watch daemon start
```

refreshes cache every 60 seconds.

### Milestone 6: Watch mode

Deliver:

```text
Rich live table
ticker-watch watch
```

Acceptance:

```bash
ticker-watch watch
```

runs live full-screen price table.

### Milestone 7: Tests and README

Deliver:

```text
pytest coverage for config/cache/render/provider/daemon
README with tmux integration
```

Acceptance:

```bash
pytest
```

passes.

---

## 19. Non-goals

Do not implement these in MVP:

```text
Overnight price
Broker APIs
Portfolio
Alerts
SQLite history
Charts
Web UI
Mobile notifications
Trading
Order placement
Account login
```

These can be later versions.

---

## 20. Future improvements

Possible later:

```text
1. Alerts when price crosses threshold.
2. Portfolio quantity and market value.
3. SQLite price history.
4. Terminal sparkline charts.
5. JSON output mode.
6. Better Yahoo fallback handling.
7. Provider abstraction for Moomoo or IBKR, only if needed later.
8. Hermes integration through read-only local HTTP service.
```
