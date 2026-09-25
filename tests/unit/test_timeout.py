"""Hang protection: a backend that never finishes is terminated, with
everything it started, and a clear error is raised.

A dummy backend that sleeps forever stands in for ELLIPROF; the real
numerical code is never forced into a loop."""

import os
import signal
import sys
import time
from pathlib import Path

import numpy as np
import pytest

from elliprof import ElliprofTimeoutError, cli, run_elliprof
from helpers import write_fits

pytestmark = pytest.mark.skipif(os.name != "posix",
                                reason="dummy backend is a POSIX script")


@pytest.fixture
def hanging_backend(tmp_path):
    """A 'backend' that starts a child process, records both PIDs, and
    then sleeps forever."""
    pids = tmp_path / "pids"
    script = tmp_path / "hang.sh"
    script.write_text(f"""#!/bin/sh
sleep 1000 &
echo $! > {pids}
echo $$ >> {pids}
exec sleep 1000
""")
    script.chmod(0o755)
    return script, pids


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # a zombie (killed, not yet reaped by init) is not running
    if sys.platform.startswith("linux"):
        state = Path(f"/proc/{pid}/stat").read_text().split()[2]
        return state != "Z"
    return True


@pytest.fixture
def image(tmp_path):
    return write_fits(tmp_path / "img.fits", np.ones((20, 20)))


def wait_for(path, seconds=5):
    t0 = time.time()
    while not (path.exists() and len(path.read_text().split()) == 2):
        if time.time() - t0 > seconds:
            raise AssertionError("dummy backend did not start")
        time.sleep(0.05)


def test_timeout_kills_backend_and_children(hanging_backend, image):
    script, pids = hanging_backend
    t0 = time.time()
    with pytest.raises(ElliprofTimeoutError) as info:
        run_elliprof(image, 10, 10, r0=1, r1=5, nr=3, backend=script,
                     timeout=1.0)
    assert time.time() - t0 < 15
    err = info.value
    assert str(err) == ("ELLIPROF exceeded the 1-second timeout and was "
                        "terminated")
    assert err.timeout == 1.0
    assert err.command[0] == str(script)
    wait_for(pids)
    child, parent = map(int, pids.read_text().split())
    deadline = time.time() + 5
    while (alive(child) or alive(parent)) and time.time() < deadline:
        time.sleep(0.05)
    assert not alive(parent), "backend still running"
    assert not alive(child), "backend's child still running (orphan)"


def test_timeout_removes_temporary_output(hanging_backend, image,
                                          monkeypatch, tmp_path):
    import tempfile
    made = []
    real = tempfile.mkdtemp

    def spy(*a, **k):
        d = real(*a, **k)
        made.append(Path(d))
        return d
    monkeypatch.setattr(tempfile, "mkdtemp", spy)
    script, _ = hanging_backend
    with pytest.raises(ElliprofTimeoutError):
        run_elliprof(image, 10, 10, r0=1, r1=5, nr=3, backend=script,
                     timeout=0.5)
    assert made and not made[0].exists()


def test_cli_timeout_message(hanging_backend, image, monkeypatch, capsys):
    script, _ = hanging_backend
    monkeypatch.setenv("ELLIPROF_NATIVE", str(script))
    code = cli.main([str(image), "X0=10", "Y0=10", "R0=1", "R1=5", "NR=3",
                     "--timeout", "1"])
    err = capsys.readouterr().err
    assert code == 124
    assert "error: ELLIPROF exceeded the 1-second timeout and was " \
        "terminated" in err
    assert "command: " + str(script) in err


def test_backend_gets_no_terminal_input(tmp_path, image):
    """stdin is closed, so nothing can wait for keyboard input."""
    script = tmp_path / "reads_stdin.sh"
    script.write_text("#!/bin/sh\nread line\necho \"got:$line:\" >&2\n"
                      "exit 3\n")
    script.chmod(0o755)
    res = run_elliprof(image, 10, 10, r0=1, r1=5, nr=3, backend=script,
                       timeout=10, check=False)
    assert res.returncode == 3 and "got::" in res.stderr


def test_default_timeout_is_1800():
    import inspect
    assert inspect.signature(run_elliprof).parameters["timeout"].default \
        == 1800


def test_invalid_timeout(image):
    with pytest.raises(ValueError, match="timeout"):
        run_elliprof(image, 10, 10, r0=1, r1=5, nr=3, timeout=-1)
