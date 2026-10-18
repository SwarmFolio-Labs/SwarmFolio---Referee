# Make the project folder importable from tests (so `import models` works).
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _live_mode_off():
    """Importing agents/brains.py switches on the fast live model; every test starts with it off."""
    from committee import llm
    llm._live["on"] = False
    yield
    llm._live["on"] = False
