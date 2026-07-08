# ticker-watch Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a simple read-only Python CLI called `ticker-watch` that fetches Yahoo Finance quotes, caches them, and renders terminal-friendly status/table views.

**Architecture:** Keep modules small and direct: Typer CLI commands call config/cache/provider/render/daemon helpers. The status path reads only JSON cache for tmux speed; live fetching happens in `once`, `watch`, and the daemon loop.

**Tech Stack:** Python, Typer, Rich, Pydantic, PyYAML, yfinance, pytest.

---

### Task 1: Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/ticker_watch/__init__.py`
- Create: `src/ticker_watch/cli.py`
- Create: `README.md`

**Steps:**
1. Add packaging metadata and the `ticker-watch = ticker_watch.cli:app` script.
2. Create an importable Typer app.
3. Run `python -m pytest` after adding smoke tests.
4. Verify `ticker-watch --help` after editable install.

### Task 2: Config

**Files:**
- Create: `src/ticker_watch/models.py`
- Create: `src/ticker_watch/config.py`
- Test: `tests/test_config.py`
- Test: `tests/test_cli_config_commands.py`

**Steps:**
1. Write tests for default config, load/save, add/remove, and type inference.
2. Implement Pydantic config models and YAML helpers.
3. Wire `init`, `list`, `add`, and `remove`.
4. Run config and CLI tests.

### Task 3: Cache And Rendering

**Files:**
- Create: `src/ticker_watch/cache.py`
- Create: `src/ticker_watch/render.py`
- Test: `tests/test_cache.py`
- Test: `tests/test_render_status.py`

**Steps:**
1. Write tests for atomic cache read/write and stale detection.
2. Write tests for compact positive, negative, zero, stale, and error output.
3. Implement JSON cache helpers and renderers.
4. Run cache/render tests.

### Task 4: Yahoo Provider And Once

**Files:**
- Create: `src/ticker_watch/yahoo_provider.py`
- Create: `src/ticker_watch/app.py`
- Modify: `src/ticker_watch/cli.py`
- Test: `tests/test_yahoo_provider_mapping.py`

**Steps:**
1. Mock `yfinance.Tickers` and test normalization.
2. Test failed symbols return error `Quote` rows.
3. Implement `YahooProvider`.
4. Wire `once` to fetch, cache, and print a Rich table.
5. Run provider tests and CLI smoke tests.

### Task 5: Daemon And Watch

**Files:**
- Create: `src/ticker_watch/daemon.py`
- Modify: `src/ticker_watch/cli.py`
- Test: `tests/test_daemon.py`

**Steps:**
1. Test one daemon loop iteration writes `latest.json` using a mocked provider.
2. Implement foreground loop plus PID-file start/stop/status helpers.
3. Wire `daemon start`, `daemon run`, `daemon stop`, `daemon status`, and `watch`.
4. Run daemon tests and full pytest.

### Task 6: README And Verification

**Files:**
- Modify: `README.md`
- Test: `tests/test_static_safety.py`

**Steps:**
1. Add install, command, daemon, and tmux instructions.
2. Add a source-only static test for the forbidden API keywords.
3. Run `pytest`.
4. Run `ticker-watch --help`, `ticker-watch init`, `ticker-watch list`, and `ticker-watch once` when network is available.
