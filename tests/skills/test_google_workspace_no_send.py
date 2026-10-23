"""Tests for the HERMES_GMAIL_NO_SEND guard in the Google Workspace skill."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "skills/productivity/google-workspace/scripts"


def _load(name, filename, monkeypatch, tmp_path, no_send):
    home = tmp_path / ".hermes"
    home.mkdir(exist_ok=True)
    monkeypatch.setenv("HERMES_HOME", str(home))
    if no_send:
        monkeypatch.setenv("HERMES_GMAIL_NO_SEND", no_send)
    else:
        monkeypatch.delenv("HERMES_GMAIL_NO_SEND", raising=False)
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def bridge(monkeypatch, tmp_path):
    return _load("gws_bridge_nosend", "gws_bridge.py", monkeypatch, tmp_path, "1")


@pytest.mark.parametrize(
    "argv",
    [
        ["gmail", "users", "messages", "send", "--params", "{}"],
        ["gmail", "users", "drafts", "send", "--json", "{}"],
        ["gmail", "+send", "--to", "a@b.c", "--subject", "x", "--body", "y"],
        ["gmail", "+reply", "--message-id", "1", "--body", "y"],
        ["gmail", "+reply-all", "--message-id", "1", "--body", "y"],
        ["gmail", "+forward", "--message-id", "1", "--to", "a@b.c"],
    ],
)
def test_send_calls_are_detected(bridge, argv):
    assert bridge._is_gmail_send_call(argv) is True


@pytest.mark.parametrize(
    "argv",
    [
        ["gmail", "+send", "--to", "a@b.c", "--body", "y", "--draft"],
        ["gmail", "+reply", "--message-id", "1", "--body", "y", "--draft"],
        ["gmail", "+forward", "--message-id", "1", "--to", "a@b.c", "--draft"],
        ["gmail", "+reply", "--message-id", "1", "--body", "y", "--dry-run"],
        ["gmail", "users", "drafts", "create", "--json", "{}"],
        ["gmail", "users", "messages", "list"],
        ["gmail", "+triage"],
        ["calendar", "events", "list"],
    ],
)
def test_draft_and_read_calls_are_allowed(bridge, argv):
    assert bridge._is_gmail_send_call(argv) is False


def test_bridge_blocks_before_touching_token(monkeypatch, tmp_path, capsys):
    bridge = _load("gws_bridge_nosend2", "gws_bridge.py", monkeypatch, tmp_path, "1")
    monkeypatch.setattr(bridge, "get_valid_token", lambda: pytest.fail("token must not be fetched"))
    monkeypatch.setattr(sys, "argv", ["gws_bridge.py", "gmail", "+send", "--to", "a@b.c"])
    with pytest.raises(SystemExit) as exc:
        bridge.main()
    assert exc.value.code == 1
    assert json.loads(capsys.readouterr().out)["status"] == "blocked"


@pytest.mark.parametrize("value", [None, "", "0", "false"])
def test_guard_is_off_unless_enabled(monkeypatch, tmp_path, value):
    bridge = _load("gws_bridge_off", "gws_bridge.py", monkeypatch, tmp_path, value)
    assert bridge.no_send_enabled() is False


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " 1 "])
def test_guard_on_values(monkeypatch, tmp_path, value):
    bridge = _load("gws_bridge_on", "gws_bridge.py", monkeypatch, tmp_path, value)
    assert bridge.no_send_enabled() is True


@pytest.mark.parametrize("func", ["gmail_send", "gmail_reply"])
def test_google_api_send_and_reply_blocked(monkeypatch, tmp_path, capsys, func):
    api = _load("google_api_nosend", "google_api.py", monkeypatch, tmp_path, "1")
    monkeypatch.setattr(api, "_gws_binary", lambda: pytest.fail("must not reach gws"))
    getattr(api, func)(type("A", (), {})())
    assert json.loads(capsys.readouterr().out)["status"] == "blocked"
