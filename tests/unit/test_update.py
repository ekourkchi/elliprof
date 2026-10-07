"""elliprof --check-update / --update / -u, and the once-a-day notice.

No test here touches the network or installs anything: PyPI and pip are
replaced by stand-ins."""

import io
import json
import sys
import threading
import time

import pytest

from elliprof import cli, update
from elliprof._version import __version__


@pytest.fixture(autouse=True)
def no_network(monkeypatch, tmp_path):
    def refuse(*a, **k):
        raise AssertionError("network used in a test")
    monkeypatch.setattr("urllib.request.urlopen", refuse)
    monkeypatch.setattr(update, "_cache_file",
                        lambda: tmp_path / "cache" / "update_check.json")
    monkeypatch.delenv(update.ENV_OFF, raising=False)


def newer():
    parts = [int(p) for p in __version__.split(".")]
    parts[-1] += 1
    return ".".join(map(str, parts))


def test_versions():
    assert update.parse_version("0.1.4") == (0, 1, 4)
    assert update.parse_version("0.1.0") == update.parse_version("0.1")
    for bad in ("0.1.4rc1", "0.1.4.dev0", "0+unknown", ""):
        assert update.parse_version(bad) is None
    assert update.is_newer("0.1.10", "0.1.9")
    assert not update.is_newer("0.1.4", "0.1.4")
    assert not update.is_newer("0.2.0rc1", "0.1.4")    # never offered


def test_latest_version_reads_pypi_json(monkeypatch):
    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    seen = {}

    def fake(req, timeout):
        seen["url"], seen["timeout"] = req.full_url, timeout
        return Resp(json.dumps({"info": {"version": "9.9.9"}}).encode())
    monkeypatch.setattr("urllib.request.urlopen", fake)
    assert update.latest_version(timeout=3) == "9.9.9"
    assert seen == {"url": "https://pypi.org/pypi/elliprof/json",
                    "timeout": 3}


def test_offline_is_a_clear_error(monkeypatch, capsys):
    monkeypatch.setattr("urllib.request.urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("x")))
    assert update.check_update() == 1
    assert "could not reach PyPI" in capsys.readouterr().err


def test_check_update_never_installs(monkeypatch, capsys):
    monkeypatch.setattr(update, "latest_version", lambda **k: newer())
    monkeypatch.setattr(update.subprocess, "call",
                        lambda *a: pytest.fail("pip run by --check-update"))
    assert update.check_update() == 0
    out = capsys.readouterr().out
    assert f"Installed: elliprof {__version__}" in out
    assert f"Latest:    elliprof {newer()}" in out
    assert "elliprof --update" in out and "pip install --upgrade" in out
    monkeypatch.setattr(update, "latest_version", lambda **k: __version__)
    assert update.check_update() == 0
    assert "up to date" in capsys.readouterr().out


def test_update_runs_pip_of_this_python(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(update, "source_checkout", lambda: None)
    monkeypatch.setattr(update, "latest_version", lambda **k: newer())
    monkeypatch.setattr(update.subprocess, "call",
                        lambda cmd: calls.append(cmd) or 0)
    assert update.update() == 0
    assert calls == [[sys.executable, "-m", "pip", "install", "--upgrade",
                      f"elliprof=={newer()}"]]
    assert f"updated to {newer()}" in capsys.readouterr().out


def test_update_when_current_does_nothing(monkeypatch, capsys):
    monkeypatch.setattr(update, "source_checkout", lambda: None)
    monkeypatch.setattr(update, "latest_version", lambda **k: __version__)
    monkeypatch.setattr(update.subprocess, "call",
                        lambda *a: pytest.fail("pip run when up to date"))
    assert update.update() == 0
    assert "up to date" in capsys.readouterr().out


def test_update_reports_pip_failure(monkeypatch, capsys):
    monkeypatch.setattr(update, "source_checkout", lambda: None)
    monkeypatch.setattr(update, "latest_version", lambda **k: newer())
    monkeypatch.setattr(update.subprocess, "call", lambda cmd: 1)
    assert update.update() == 1
    assert "pip could not update elliprof" in capsys.readouterr().err


def test_update_refuses_a_source_checkout(monkeypatch, capsys):
    """These tests run from the source tree."""
    assert update.source_checkout() is not None
    monkeypatch.setattr(update.subprocess, "call",
                        lambda *a: pytest.fail("pip run on a checkout"))
    assert update.update() == 1
    assert "source checkout" in capsys.readouterr().err


@pytest.mark.parametrize("flag, fn", [("-u", "update"),
                                      ("--update", "update"),
                                      ("--check-update", "check_update")])
def test_cli_flags(monkeypatch, flag, fn):
    called = []
    monkeypatch.setattr(update, fn, lambda: called.append(fn) or 7)
    assert cli.main([flag]) == 7
    assert called == [fn]


# ---- the notice

def tty(monkeypatch, on=True):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: on, raising=False)
    monkeypatch.setattr(sys.stderr, "isatty", lambda: on, raising=False)


def test_notice_off_in_scripts_and_by_env(monkeypatch):
    tty(monkeypatch, False)
    assert update.start_notice() is None
    tty(monkeypatch, True)
    monkeypatch.setenv(update.ENV_OFF, "1")
    assert update.start_notice() is None


def test_notice_once_a_day(monkeypatch, capsys):
    tty(monkeypatch)
    n = []
    monkeypatch.setattr(update, "latest_version",
                        lambda **k: n.append(1) or newer())
    update.finish_notice(update.start_notice())
    assert f"elliprof {newer()} is available" in capsys.readouterr().err
    update.finish_notice(update.start_notice())       # cached: no request
    assert len(n) == 1
    assert "elliprof --update" in capsys.readouterr().err
    cache = json.loads(update._cache_file().read_text())
    cache["checked"] = time.time() - 2 * update.NOTICE_INTERVAL
    update._cache_file().write_text(json.dumps(cache))
    update.finish_notice(update.start_notice())       # a day later
    assert len(n) == 2


def test_notice_silent_when_current_or_offline(monkeypatch, capsys):
    tty(monkeypatch)
    monkeypatch.setattr(update, "latest_version", lambda **k: __version__)
    update.finish_notice(update.start_notice())
    assert capsys.readouterr().err == ""
    update._cache_file().unlink()

    def offline(**k):
        raise update.UpdateError("offline")
    monkeypatch.setattr(update, "latest_version", offline)
    update.finish_notice(update.start_notice())
    assert capsys.readouterr().err == ""


def test_notice_never_delays(monkeypatch, capsys):
    tty(monkeypatch)
    gate = threading.Event()

    def slow(**k):
        gate.wait(5)
        return newer()
    monkeypatch.setattr(update, "latest_version", slow)
    t0 = time.time()
    update.finish_notice(update.start_notice())
    assert time.time() - t0 < 1.0
    assert capsys.readouterr().err == ""
    gate.set()


def test_help_documents_updates():
    text = io.StringIO()
    old, sys.stdout = sys.stdout, text
    try:
        cli.main(["-h"])
    finally:
        sys.stdout = old
    h = text.getvalue()
    assert "-u, --update" in h and "--check-update" in h
    assert "ELLIPROF_NO_UPDATE_CHECK=1" in h
