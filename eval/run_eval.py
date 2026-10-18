"""
The evaluation (MASTER 10.2): run the real committee on every client and measure M1-M6.

    python -m eval.run_eval                 # all clients in data/clients
    python -m eval.run_eval --clients 3     # just the first 3 (smoke test)

Outputs in eval/results/: results.json, results.md (table) and violations.png (M1 -> M2 -> M3).
"""

import argparse
import asyncio
import glob
import json
import os
import statistics
import time

from committee.loop import run_committee
from committee.transport_local import LocalTransport
from models import CommitteeResult
from referee.check import check, clean_dust
from referee.schema import Client
from referee.solver import is_feasible

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENTS_DIR = os.path.join(ROOT, "data", "clients")
RESULTS_DIR = os.path.join(ROOT, "eval", "results")


def load_all_clients(limit: int | None = None) -> list[Client]:
    """Every client in data/clients, sorted by id (optionally only the first `limit`)."""
    clients = []
    for path in sorted(glob.glob(os.path.join(CLIENTS_DIR, "*.json"))):
        with open(path) as f:
            clients.append(Client.model_validate(json.load(f)))
    return clients[:limit] if limit else clients


def n_failed(checks) -> int:
    return sum(1 for c in checks if not c.passed)


def share(flags: list[bool]) -> float | None:
    """Fraction of True values (None if the list is empty, so we never divide by zero)."""
    return sum(flags) / len(flags) if flags else None


def mean(xs: list[float]) -> float | None:
    return statistics.mean(xs) if xs else None


def client_row(client: Client, feasible: bool, result: CommitteeResult) -> dict:
    """Everything we need from one committee run, as plain numbers."""
    final_weights, _ = clean_dust(result.final_proposal.weights, client.universe)
    stances = [e.stance for e in result.debate_log if e.kind == "stance"]
    repaired = feasible and result.receipt.verdict == "VIOLATIONS_REPAIRED"
    return {
        "client_id": client.client_id,
        "feasible": feasible,
        "planted_conflict": client.planted_conflict,
        "first_failed": n_failed(result.first_receipt.checks),
        # result.receipt is always the check of the Chair's LAST OWN proposal (before any repair).
        "last_failed": n_failed(result.receipt.checks),
        "final_failed": n_failed(check(final_weights, client)) if feasible else None,
        "verdict": result.receipt.verdict,
        "conflict_set": sorted(result.receipt.conflict_set),
        "repaired": repaired,
        "capital_moved_by_repair": result.receipt.capital_moved if repaired else None,
        "sharpe_change": (result.receipt.sharpe_after - result.receipt.sharpe_before) if repaired else None,
        "rounds": result.rounds,
        "stances": stances,
        "notes": result.notes,
    }


def compute_metrics(rows: list[dict]) -> dict:
    """M1-M6 from the per-client rows (MASTER 10.2)."""
    feas = [r for r in rows if r["feasible"]]
    infeas = [r for r in rows if not r["feasible"]]
    stances = [s for r in rows for s in r["stances"]]
    moved = [r["capital_moved_by_repair"] for r in feas if r["repaired"]]
    sharpe = [r["sharpe_change"] for r in feas if r["repaired"]]
    planted = [r for r in infeas if r["planted_conflict"]]
    return {
        "n_clients": len(rows), "n_feasible": len(feas), "n_infeasible": len(infeas),
        "M1_first_violates": share([r["first_failed"] > 0 for r in feas]),
        "M1_mean_failed": mean([r["first_failed"] for r in feas]),
        "M2_last_own_violates": share([r["last_failed"] > 0 for r in feas]),
        "M2_mean_failed": mean([r["last_failed"] for r in feas]),
        "M3_final_passes": share([r["final_failed"] == 0 for r in feas]),
        "M4_median_capital_moved": statistics.median(moved) if moved else None,
        "M4_mean_sharpe_change": mean(sharpe),
        "M4_n_repaired": len(moved),
        "M5_infeasible_detected": sum(r["verdict"] == "RULES_INFEASIBLE" for r in infeas),
        "M5_conflict_matches_planted": sum(r["conflict_set"] == sorted(r["planted_conflict"]) for r in planted),
        "M5_n_planted": len(planted),
        "M6_concede": share([s == "concede" for s in stances]),
        "M6_defend": share([s == "defend" for s in stances]),
        "M6_modify": share([s == "modify" for s in stances]),
        "M6_n_stances": len(stances),
        "M6_mean_rounds": mean([r["rounds"] for r in rows]),
    }


def _fmt(x, pct=False) -> str:
    if x is None:
        return "n/a"
    if pct:
        return f"{x * 100:.0f}%"
    return f"{x:.2f}" if isinstance(x, float) else str(x)


def write_markdown(m: dict, rows: list[dict], path: str) -> None:
    """results.md: the metrics table plus one line per client."""
    lines = [
        "# SwarmFolio Referee: evaluation results", "",
        f"{m['n_clients']} clients ({m['n_feasible']} feasible, {m['n_infeasible']} infeasible).", "",
        "| Metric | Value |", "|---|---|",
        f"| M1 first proposal breaks ≥1 rule | {_fmt(m['M1_first_violates'], True)} (mean {_fmt(m['M1_mean_failed'])} broken) |",
        f"| M2 Chair's last own proposal breaks ≥1 rule | {_fmt(m['M2_last_own_violates'], True)} (mean {_fmt(m['M2_mean_failed'])} broken) |",
        f"| M3 final portfolio passes every rule | {_fmt(m['M3_final_passes'], True)} |",
        f"| M4 median capital moved by repair | {_fmt(m['M4_median_capital_moved'], True)} ({m['M4_n_repaired']} repaired) |",
        f"| M4 mean Sharpe change from repair | {_fmt(m['M4_mean_sharpe_change'])} |",
        f"| M5 infeasible clients detected | {m['M5_infeasible_detected']} / {m['n_infeasible']} |",
        f"| M5 conflict set == planted set | {m['M5_conflict_matches_planted']} / {m['M5_n_planted']} |",
        f"| M6 stances concede / defend / modify | {_fmt(m['M6_concede'], True)} / {_fmt(m['M6_defend'], True)} / "
        f"{_fmt(m['M6_modify'], True)} ({m['M6_n_stances']} stances) |",
        f"| M6 mean rounds | {_fmt(m['M6_mean_rounds'])} |",
        "", "| Client | Feasible | First broken | Last own broken | Final broken | Verdict | Rounds |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['client_id']} | {r['feasible']} | {r['first_failed']} | {r['last_failed']} | "
                     f"{_fmt(r['final_failed'])} | {r['verdict']} | {r['rounds']} |")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def plot_violations(m: dict, path: str) -> None:
    """Bar chart: share of feasible clients breaking a rule at M1 (first), M2 (last own), M3 (final)."""
    import matplotlib
    matplotlib.use("Agg")  # no window, just a file
    import matplotlib.pyplot as plt

    labels = ["First proposal (M1)", "Chair's last own (M2)", "Final, after Referee (M3)"]
    values = [m["M1_first_violates"] or 0, m["M2_last_own_violates"] or 0,
              1 - m["M3_final_passes"] if m["M3_final_passes"] is not None else 0]
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(labels, [v * 100 for v in values], color=["#c0504d", "#e3a33b", "#4f9d69"])
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1, f"{v * 100:.0f}%", ha="center")
    ax.set_ylabel("Feasible clients breaking ≥1 rule (%)")
    ax.set_ylim(0, 105)
    ax.set_title("Rule violations: AI alone vs. with the Referee")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


async def run_all(clients: list[Client], concurrency: int) -> list[dict]:
    """Run the committee on every client, `concurrency` at a time."""
    gate = asyncio.Semaphore(concurrency)

    async def one(client: Client) -> dict:
        async with gate:
            feasible = await asyncio.to_thread(is_feasible, client)
            start = time.time()
            result = await run_committee(client, LocalTransport())
            row = client_row(client, feasible, result)
            print(f"  {client.client_id}: {row['verdict']}, rounds={row['rounds']} ({time.time() - start:.0f}s)",
                  flush=True)
            return row

    return list(await asyncio.gather(*(one(c) for c in clients)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the committee + Referee (MASTER 10.2).")
    parser.add_argument("--clients", type=int, default=None, help="only the first N clients")
    parser.add_argument("--concurrency", type=int, default=4, help="clients run at the same time")
    args = parser.parse_args()

    clients = load_all_clients(args.clients)
    print(f"Evaluating {len(clients)} clients...", flush=True)
    rows = asyncio.run(run_all(clients, args.concurrency))
    metrics = compute_metrics(rows)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "results.json"), "w") as f:
        json.dump({"metrics": metrics, "clients": rows}, f, indent=2)
    write_markdown(metrics, rows, os.path.join(RESULTS_DIR, "results.md"))
    plot_violations(metrics, os.path.join(RESULTS_DIR, "violations.png"))
    print(open(os.path.join(RESULTS_DIR, "results.md")).read())


if __name__ == "__main__":
    main()
