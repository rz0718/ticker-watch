import time
from typing import Annotated

from pydantic import ValidationError
from rich.console import Console
from rich.live import Live
from rich.table import Table
import typer

from ticker_watch.app import fetch_once
from ticker_watch.cache import CacheNotFoundError, read_cache
from ticker_watch.config import (
    ConfigNotFoundError,
    add_instrument,
    init_config,
    load_config,
    remove_instrument,
)
from ticker_watch.daemon import get_daemon_state, run_daemon_loop, start_daemon, stop_daemon
from ticker_watch.render import render_compact_status, render_quotes_table

app = typer.Typer(help="Yahoo Finance terminal quote monitor.")
daemon_app = typer.Typer(help="Manage the background cache refresh process.")
console = Console()


@app.callback()
def main() -> None:
    """Monitor configured Yahoo Finance symbols in the terminal."""


@app.command("init")
def init_command(
    force: Annotated[bool, typer.Option("--force", help="Overwrite existing config.")] = False,
) -> None:
    path, created = init_config(force=force)
    if created:
        console.print(f"Created config: {path}")
    else:
        console.print(f"Config already exists: {path}")


@app.command("list")
def list_command() -> None:
    try:
        config = load_config()
    except ConfigNotFoundError as exc:
        console.print(f"ticker-watch: {exc}")
        raise typer.Exit(1) from exc

    table = Table(title="ticker-watch watchlist")
    table.add_column("Symbol")
    table.add_column("Name")
    table.add_column("Type")
    for item in config.watchlist:
        table.add_row(item.symbol, item.name or item.symbol, item.type)
    console.print(table)


@app.command("once")
def once_command() -> None:
    try:
        cache = fetch_once()
    except (ConfigNotFoundError, ValidationError) as exc:
        console.print(f"ticker-watch: {exc}")
        raise typer.Exit(1) from exc
    console.print(render_quotes_table(cache))


@app.command("watch")
def watch_command() -> None:
    try:
        config = load_config()
        cache = fetch_once(config)
        with Live(render_quotes_table(cache), refresh_per_second=1) as live:
            while True:
                time.sleep(config.refresh_seconds)
                config = load_config()
                cache = fetch_once(config)
                live.update(render_quotes_table(cache))
    except KeyboardInterrupt:
        console.print("Stopped")
    except (ConfigNotFoundError, ValidationError) as exc:
        console.print(f"ticker-watch: {exc}")
        raise typer.Exit(1) from exc


@app.command("status")
def status_command(
    compact: Annotated[bool, typer.Option("--compact", help="Print compact one-line status.")] = False,
    max_symbols: Annotated[
        int | None,
        typer.Option("--max-symbols", min=1, help="Maximum number of symbols to show."),
    ] = None,
    show_stale: Annotated[
        bool,
        typer.Option("--show-stale", help="Show stale cache indicator when cache is old."),
    ] = False,
) -> None:
    _ = compact
    _ = show_stale
    try:
        cache = read_cache()
    except CacheNotFoundError:
        console.print("ticker-watch: no cache yet, run `ticker-watch daemon start` or `ticker-watch once`")
        return
    console.print(render_compact_status(cache, max_symbols=max_symbols, show_stale=True))


@daemon_app.command("run")
def daemon_run_command() -> None:
    run_daemon_loop()


@daemon_app.command("start")
def daemon_start_command() -> None:
    pid, started = start_daemon()
    if started:
        console.print(f"Started ticker-watch daemon pid={pid}")
    else:
        console.print(f"ticker-watch daemon already running pid={pid}")


@daemon_app.command("stop")
def daemon_stop_command() -> None:
    stopped = stop_daemon()
    if stopped:
        console.print("Stopped ticker-watch daemon")
    else:
        console.print("ticker-watch daemon was not running")


@daemon_app.command("status")
def daemon_status_command() -> None:
    state = get_daemon_state()
    if state.running:
        cache_text = _format_cache_state(state.cache_updated_at, state.cache_stale)
        console.print(f"ticker-watch daemon running pid={state.pid} {cache_text}")
    else:
        cache_text = _format_cache_state(state.cache_updated_at, state.cache_stale)
        console.print(f"ticker-watch daemon stopped {cache_text}")


@app.command("add")
def add_command(
    symbol: str,
    instrument_type: Annotated[
        str | None,
        typer.Option("--type", help="Instrument type: us, hk, or crypto."),
    ] = None,
    name: Annotated[str | None, typer.Option("--name", help="Display name.")] = None,
) -> None:
    if instrument_type is not None and instrument_type not in {"us", "hk", "crypto"}:
        console.print("ticker-watch: --type must be one of: us, hk, crypto")
        raise typer.Exit(1)
    try:
        config = add_instrument(symbol, instrument_type=instrument_type, name=name)
    except (ConfigNotFoundError, ValidationError) as exc:
        console.print(f"ticker-watch: {exc}")
        raise typer.Exit(1) from exc
    added = next(item for item in config.watchlist if item.symbol == symbol.strip().upper())
    console.print(f"Added {added.symbol} ({added.type})")


@app.command("remove")
def remove_command(symbol: str) -> None:
    try:
        remove_instrument(symbol)
    except (ConfigNotFoundError, ValidationError) as exc:
        console.print(f"ticker-watch: {exc}")
        raise typer.Exit(1) from exc
    console.print(f"Removed {symbol.strip().upper()}")


def _format_cache_state(updated_at, stale) -> str:
    if updated_at is None:
        return "cache=missing"
    marker = "stale" if stale else "fresh"
    return f"cache={marker} updated={updated_at.astimezone().strftime('%Y-%m-%d %H:%M:%S')}"


app.add_typer(daemon_app, name="daemon")


if __name__ == "__main__":
    app()
