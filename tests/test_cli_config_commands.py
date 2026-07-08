from __future__ import annotations

import pytest
from typer.testing import CliRunner

from ticker_watch.cli import app
from ticker_watch.config import load_config


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def isolated_paths(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("TICKER_WATCH_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("TICKER_WATCH_CACHE_DIR", str(tmp_path / "cache"))


def test_init_and_list_commands(runner: CliRunner, isolated_paths) -> None:
    init_result = runner.invoke(app, ["init"])
    assert init_result.exit_code == 0
    assert "Created config" in init_result.output

    list_result = runner.invoke(app, ["list"])
    assert list_result.exit_code == 0
    assert "NVDA" in list_result.output
    assert "BTC-USD" in list_result.output


def test_add_and_remove_commands(runner: CliRunner, isolated_paths) -> None:
    assert runner.invoke(app, ["init"]).exit_code == 0

    add_result = runner.invoke(app, ["add", "AAPL", "--type", "us", "--name", "Apple"])
    assert add_result.exit_code == 0
    assert "AAPL" in add_result.output
    assert any(item.symbol == "AAPL" and item.name == "Apple" for item in load_config().watchlist)

    remove_result = runner.invoke(app, ["remove", "AAPL"])
    assert remove_result.exit_code == 0
    assert "Removed AAPL" in remove_result.output
    assert all(item.symbol != "AAPL" for item in load_config().watchlist)


def test_add_command_infers_type(runner: CliRunner, isolated_paths) -> None:
    assert runner.invoke(app, ["init"]).exit_code == 0

    result = runner.invoke(app, ["add", "ETH-USD"])

    assert result.exit_code == 0
    added = next(item for item in load_config().watchlist if item.symbol == "ETH-USD")
    assert added.type == "crypto"
