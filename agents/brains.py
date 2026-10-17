"""
The one place agents get their brain functions from (MASTER 4.3).

USE_FAKES = True  -> the hard-coded fakes in fakes.py (to test the Fetch plumbing).
USE_FAKES = False -> the real Referee and committee. Flipping the switch is the whole connection step.
"""

import config

if config.USE_FAKES:
    from fakes import analyze, referee, review, run_committee  # noqa: F401
else:
    from referee.receipt import referee  # noqa: F401
    # The committee (A6-A8) isn't built yet; until it is, the analysts and the loop stay fake.
    try:
        from committee.analysts import analyze, review  # noqa: F401
        from committee.loop import run_committee  # noqa: F401
    except ImportError:
        from fakes import analyze, review, run_committee  # noqa: F401
