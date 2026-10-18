"""
Warm the cache for the live demo: run the committee once for each demo client, in live mode
(the same fast model the Fetch agents use), so every LLM answer is saved in cache/.

When a judge then asks the Chair Agent about one of these clients, the agents send the exact same
prompts, so every answer comes straight from the cache: same result, in seconds.

    python -m scripts.warm_demo                 # C02, C04, C91, C03
    python -m scripts.warm_demo C02 C91         # just these
"""

import asyncio
import sys
import time

from committee import llm
from committee.analysts import load_client
from committee.loop import run_committee
from committee.transport_local import LocalTransport

DEMO_CLIENTS = ["C02", "C04", "C91", "C03"]


async def warm(client_id: str) -> None:
    start = time.time()
    result = await run_committee(load_client(client_id), LocalTransport())
    print(f"{client_id}: {result.receipt.verdict}, {result.rounds} round(s), "
          f"self_corrected={result.self_corrected} ({time.time() - start:.0f}s)", flush=True)


async def main(client_ids: list[str]) -> None:
    llm.use_live_model()  # same model and cache entries as the live agents
    await asyncio.gather(*(warm(c) for c in client_ids))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or DEMO_CLIENTS))
