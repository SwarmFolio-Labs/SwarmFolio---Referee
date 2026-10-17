"""The Fetch.ai agents: thin wrappers that turn messages into brain-function calls."""

import asyncio


def event_loop() -> asyncio.AbstractEventLoop:
    """The event loop a uAgents Agent should use.

    Python 3.14 no longer makes an event loop on demand, but uagents 0.26.1 asks for one when an
    Agent is created. So reuse the running loop (inside async code) or make a fresh one.
    """
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop
