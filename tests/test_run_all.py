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


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signals")
@pytest.mark.parametrize("sig", [signal.SIGTERM, signal.SIGHUP, signal.SIGINT])
def test_signal_stops_all_children(tmp_path, sig):
    """Start run_all with 5 stand-in agents, send it the signal, and check every child is gone."""
    (tmp_path / "fake_agent.py").write_text(FAKE_AGENT)
    pid_dir = tmp_path / "pids"
    pid_dir.mkdir()
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(tmp_path), REPO]),
           "RUN_ALL_PID_DIR": str(pid_dir), "USE_ANALYST_AGENTS": "true"}
    for var in ("REFEREE_SEED", "MACRO_SEED", "FUNDAMENTALS_SEED", "RISK_SEED", "CHAIR_SEED"):
        env[var] = f"run_all signal test seed for {var}, swarmfolio unit tests only"

    driver = subprocess.Popen([sys.executable, "-c", DRIVER], cwd=REPO, env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.time() + 60
        while len(os.listdir(pid_dir)) < 5:
            assert driver.poll() is None, "run_all exited before starting all agents"
            assert time.time() < deadline, "the 5 stand-in agents never started"
            time.sleep(0.1)
        children = [int(name) for name in os.listdir(pid_dir)]
        assert all(_alive(pid) for pid in children)

        driver.send_signal(sig)
        assert driver.wait(timeout=30) is not None

        deadline = time.time() + 10
        while any(_alive(pid) for pid in children) and time.time() < deadline:
            time.sleep(0.1)
        assert not any(_alive(pid) for pid in children), "some agents outlived run_all"
    finally:
        if driver.poll() is None:
            driver.kill()
        for name in os.listdir(pid_dir):
            try:
                os.kill(int(name), signal.SIGKILL)
            except ProcessLookupError:
                pass
