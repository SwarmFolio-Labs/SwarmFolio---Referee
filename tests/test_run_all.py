"""
run_all must stop all 5 child agents on Ctrl+C (SIGINT), `kill <pid>` (SIGTERM) or a closed
terminal (SIGHUP). The children here are tiny stand-in processes, so nothing touches the network.
"""

import os
import signal
import subprocess
import sys
import time

import pytest

from agents import run_all

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FAKE_AGENT = """
import os, pathlib, time
pathlib.Path(os.environ["RUN_ALL_PID_DIR"], str(os.getpid())).write_text("")
while True:
    time.sleep(1)
"""

DRIVER = """
from agents import run_all
run_all.AGENTS = [(name, seed_var, "fake_agent") for name, seed_var, _ in run_all.AGENTS]
run_all.main()
"""


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _start(tmp_path, ignore_sighup: bool = False):
    """Start run_all with 5 stand-in agents; return (driver process, the 5 child pids)."""
    (tmp_path / "fake_agent.py").write_text(FAKE_AGENT)
    pid_dir = tmp_path / "pids"
    pid_dir.mkdir()
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(tmp_path), REPO]),
           "RUN_ALL_PID_DIR": str(pid_dir), "USE_ANALYST_AGENTS": "true"}
    for var in ("REFEREE_SEED", "MACRO_SEED", "FUNDAMENTALS_SEED", "RISK_SEED", "CHAIR_SEED"):
        env[var] = f"run_all signal test seed for {var}, swarmfolio unit tests only"

    # ignore_sighup starts run_all the way `nohup` does: with SIGHUP already ignored.
    preexec = (lambda: signal.signal(signal.SIGHUP, signal.SIG_IGN)) if ignore_sighup else None
    driver = subprocess.Popen([sys.executable, "-c", DRIVER], cwd=REPO, env=env, preexec_fn=preexec,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 60
    while len(os.listdir(pid_dir)) < 5:
        if driver.poll() is not None or time.time() > deadline:
            driver.kill()
            pytest.fail("run_all never started all 5 stand-in agents")
        time.sleep(0.1)
    return driver, [int(name) for name in os.listdir(pid_dir)]


def _cleanup(driver, children):
    if driver.poll() is None:
        driver.kill()
    for pid in children:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _all_gone(children, wait_s: float = 10) -> bool:
    deadline = time.time() + wait_s
    while any(_alive(pid) for pid in children) and time.time() < deadline:
        time.sleep(0.1)
    return not any(_alive(pid) for pid in children)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signals")
@pytest.mark.parametrize("sig", [signal.SIGTERM, signal.SIGHUP, signal.SIGINT])
def test_signal_stops_all_children(tmp_path, sig):
    """Start run_all with 5 stand-in agents, send it the signal, and check every child is gone."""
    driver, children = _start(tmp_path)
    try:
        assert all(_alive(pid) for pid in children)
        driver.send_signal(sig)
        assert driver.wait(timeout=30) is not None
        assert _all_gone(children), "some agents outlived run_all"
    finally:
        _cleanup(driver, children)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signals")
def test_nohup_keeps_sighup_ignored(tmp_path):
    """Under nohup (SIGHUP ignored at start), a closed terminal must not stop the agents; SIGTERM still does."""
    driver, children = _start(tmp_path, ignore_sighup=True)
    try:
        driver.send_signal(signal.SIGHUP)
        time.sleep(2)
        assert driver.poll() is None, "run_all stopped on SIGHUP even though nohup ignores it"
        assert all(_alive(pid) for pid in children)

        driver.send_signal(signal.SIGTERM)
        assert driver.wait(timeout=30) is not None
        assert _all_gone(children), "some agents outlived run_all"
    finally:
        _cleanup(driver, children)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signals")
def test_install_stop_handlers_respects_ignored_sighup():
    """In-process: an ignored SIGHUP stays ignored; SIGTERM still gets the stop handler."""
    old = {sig: signal.getsignal(sig) for sig in (signal.SIGHUP, signal.SIGTERM)}
    try:
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        run_all.install_stop_handlers()
        assert signal.getsignal(signal.SIGHUP) == signal.SIG_IGN
        assert signal.getsignal(signal.SIGTERM) == run_all._stop

        signal.signal(signal.SIGHUP, signal.SIG_DFL)
        run_all.install_stop_handlers()
        assert signal.getsignal(signal.SIGHUP) == run_all._stop
    finally:
        for sig, handler in old.items():
            signal.signal(sig, handler)
