"""
The feedback experiment (MASTER 10.3): can math feedback teach an AI to follow a client's rules,
and does it matter whether the math EXPLAINS itself?

Paired design: for each feasible client and trial, the 3 memos and the Chair's first draft are made
ONCE, then three conditions each get up to 3 rounds of Chair-only revision from that same draft:
  A. self       "re-check your work"            (no Referee info)
  B. bare       which rules failed              (no numbers)
  C. explained  the Referee's sentences          (actual vs limit), never the repaired weights
The Referee checks after every round; a condition stops early once it's compliant.

    python -m eval.experiment --clients 3 --trials 1     # smoke test
    python -m eval.experiment                            # everything, 3 trials
    python -m eval.experiment --ids C91,C92 --trials 3   # just some clients

Outputs in eval/results/: experiment.json, experiment.md, learning_curves.png.
"""

import argparse
import asyncio
import json
import logging
import os
import random
import statistics
import time

from scipy.stats import binomtest

from committee import llm
from committee.analysts import ANALYSTS, analyze
from committee.chair import chair_propose, chair_revise_with
from committee.feedback import MODES, format_feedback
from eval.run_eval import RESULTS_DIR, load_all_clients
from models import AnalysisRequest
from referee import market
from referee.check import COUNT_RULES
from referee.receipt import referee
from referee.repair import capital_moved
from referee.schema import Client, Proposal
from referee.solver import is_feasible

ROUNDS = 3              # revision rounds per condition
TEMPERATURE = 0.7       # eval calls are sampled, so trials differ
CONDITION_NAMES = {"self": "A. Self-check", "bare": "B. Bare verdict", "explained": "C. Explained"}


# ---------- One client-trial ----------

def measure(client: Client, weights: dict[str, float]) -> dict:
    """Check a portfolio with the Referee and boil the receipt down to the numbers we track."""
    receipt = referee(client, _proposal(weights))
    failed = [c for c in receipt.checks if not c.passed]
    return {
        "compliant": receipt.verdict == "PASS",
        "n_broken": len(failed),
        # Weight-type rules in percentage points; count rules (# holdings) reported separately.
        "violation_pp": sum(c.violation * 100 for c in failed if c.type not in COUNT_RULES),
        "violation_count": sum(c.violation for c in failed if c.type in COUNT_RULES),
        "weights": weights,
        "receipt": receipt,
    }


def _proposal(weights: dict[str, float]) -> Proposal:
    return Proposal(weights=weights, thesis="(experiment)", reasons={})


def run_condition(client: Client, draft, mode: str) -> list[dict]:
    """Up to ROUNDS of Chair-only revision with one kind of feedback. Returns the state at round 0..ROUNDS."""
    proposal = draft
    state = measure(client, draft.weights)
    history = [state]
    for _ in range(ROUNDS):
        if state["compliant"]:
            history.append(state)  # stopped early: the state just carries forward
            continue
        feedback_text = format_feedback(state["receipt"], client, mode)
        try:
            proposal = chair_revise_with(client, proposal, feedback_text)
            state = measure(client, proposal.weights)
        except Exception as e:  # a failed LLM call counts as "no progress this round"
            print(f"    {client.client_id} {mode}: revision failed ({e})", flush=True)
        history.append(state)
    return history


def run_trial(client: Client, trial: int) -> dict:
    """Shared start (memos + first draft), then all three conditions from that same draft."""
    with llm.sampling(TEMPERATURE, f"Trial {trial}"):
        req = AnalysisRequest(client_id=client.client_id, client_story=client.story,
                              rules_text=[r.source for r in client.rules], as_of=market.as_of())
        memos = []
        for agent in ANALYSTS:
            try:
                memos.append(analyze(agent, req))
            except Exception as e:
                print(f"    {client.client_id} t{trial}: {agent} memo failed ({e})", flush=True)
        draft = chair_propose(client, memos)
        conditions = {mode: run_condition(client, draft, mode) for mode in MODES}

    out = {"client_id": client.client_id, "trial": trial, "draft": draft.weights, "conditions": {}}
    for mode, history in conditions.items():
        out["conditions"][mode] = {
            "rounds": [{k: v for k, v in s.items() if k != "receipt"} for s in history],
            "rounds_to_comply": rounds_to_comply([s["compliant"] for s in history]),
            "capital_moved": capital_moved(draft.weights, history[-1]["weights"]),
        }
    return out


# ---------- Statistics ----------

def rounds_to_comply(compliant: list[bool]) -> int | None:
    """First round index (0 = the draft itself) at which the portfolio passed; None if it never did."""
    for i, ok in enumerate(compliant):
        if ok:
            return i
    return None


def bootstrap_ci(values: list[float], n: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    """Mean and 95% bootstrap confidence interval (resample the client-trials with replacement)."""
    if not values:
        return float("nan"), float("nan"), float("nan")
    rng = random.Random(seed)
    means = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(n))
    return statistics.mean(values), means[int(0.025 * n)], means[int(0.975 * n) - 1]


def paired_comparison(c_rounds: list[int | None], other_rounds: list[int | None]) -> dict:
    """
    Per client-trial: did C become compliant in fewer / the same / more rounds than the other condition?
    "Never" counts as worse than any number of rounds. Sign test on fewer vs more (ties dropped).
    """
    never = ROUNDS + 1
    fewer = same = more = 0
    for c, o in zip(c_rounds, other_rounds):
        c = never if c is None else c
        o = never if o is None else o
        if c < o:
            fewer += 1
        elif c == o:
            same += 1
        else:
            more += 1
    p = binomtest(fewer, fewer + more, 0.5).pvalue if fewer + more > 0 else 1.0
    return {"fewer": fewer, "same": same, "more": more, "p_value": p}


def summarize(trials: list[dict]) -> dict:
    """Per condition and round: compliance rate, mean # broken, mean violation, with 95% CIs."""
    summary = {}
    for mode in MODES:
        per_round = []
        for r in range(ROUNDS + 1):
            states = [t["conditions"][mode]["rounds"][r] for t in trials]
            per_round.append({
                "compliance": bootstrap_ci([1.0 if s["compliant"] else 0.0 for s in states]),
                "n_broken": bootstrap_ci([float(s["n_broken"]) for s in states]),
                "violation_pp": bootstrap_ci([s["violation_pp"] for s in states]),
                "violation_count": statistics.mean([s["violation_count"] for s in states]),
            })
        summary[mode] = {
            "per_round": per_round,
            "capital_moved": bootstrap_ci([t["conditions"][mode]["capital_moved"] for t in trials]),
        }
    c = [t["conditions"]["explained"]["rounds_to_comply"] for t in trials]
    summary["C_vs_B"] = paired_comparison(c, [t["conditions"]["bare"]["rounds_to_comply"] for t in trials])
    summary["C_vs_A"] = paired_comparison(c, [t["conditions"]["self"]["rounds_to_comply"] for t in trials])
    summary["n_trials"] = len(trials)
    summary["n_draft_violates"] = sum(not t["conditions"]["self"]["rounds"][0]["compliant"] for t in trials)
    return summary


# ---------- Outputs ----------

def _ci(t, pct=True) -> str:
    m, lo, hi = t
    if pct:
        return f"{m * 100:.0f}% [{lo * 100:.0f}, {hi * 100:.0f}]"
    return f"{m:.2f} [{lo:.2f}, {hi:.2f}]"


def finding_text(s: dict) -> str:
    """Three factual sentences built only from the numbers (MASTER 10.3 honesty rule)."""
    final = {m: s[m]["per_round"][-1]["compliance"][0] for m in MODES}
    cb, ca = s["C_vs_B"], s["C_vs_A"]
    return (
        f"Out of {s['n_trials']} client-trials, {s['n_draft_violates']} first drafts broke at least one rule. "
        f"After {ROUNDS} rounds of revision, compliance was {final['self'] * 100:.0f}% with self-check, "
        f"{final['bare'] * 100:.0f}% with the bare verdict and {final['explained'] * 100:.0f}% with the "
        f"explained feedback. "
        f"Explained feedback reached compliance in fewer rounds than bare in {cb['fewer']}, the same in "
        f"{cb['same']} and more in {cb['more']} client-trials (sign test p = {cb['p_value']:.3f}); versus "
        f"self-check: {ca['fewer']} / {ca['same']} / {ca['more']} (p = {ca['p_value']:.3f})."
    )


def write_markdown(s: dict, path: str) -> None:
    lines = ["# The feedback experiment", ""]
    if s.get("run_note"):
        lines += [f"*{s['run_note']}*", ""]
    lines += [f"{s['n_trials']} client-trials; {s['n_draft_violates']} first drafts broke ≥1 rule. "
             "95% bootstrap CIs in brackets.", "",
             "| Condition | " + " | ".join(f"Round {r}" for r in range(ROUNDS + 1)) + " | Capital moved |",
             "|---|" + "---|" * (ROUNDS + 2)]
    for mode in MODES:
        cells = [_ci(pr["compliance"]) for pr in s[mode]["per_round"]]
        lines.append(f"| {CONDITION_NAMES[mode]} (compliance) | " + " | ".join(cells)
                     + f" | {_ci(s[mode]['capital_moved'])} |")
    lines += ["", "| Condition | " + " | ".join(f"Round {r}" for r in range(ROUNDS + 1)) + " |",
              "|---|" + "---|" * (ROUNDS + 1)]
    for mode in MODES:
        cells = [f"{pr['n_broken'][0]:.2f} broken, {pr['violation_pp'][0]:.1f} pp" for pr in s[mode]["per_round"]]
        lines.append(f"| {CONDITION_NAMES[mode]} | " + " | ".join(cells) + " |")
    for key, label in (("C_vs_B", "C vs B"), ("C_vs_A", "C vs A")):
        p = s[key]
        lines.append(f"\n**{label}** (rounds to compliance): C fewer {p['fewer']}, same {p['same']}, "
                     f"more {p['more']}; sign test p = {p['p_value']:.3f}")
    lines += ["", "## Finding", "", finding_text(s)]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def plot_curves(s: dict, path: str) -> None:
    """Compliance rate vs round, one line per condition, shaded 95% CIs."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"self": "#8c8c8c", "bare": "#e3a33b", "explained": "#2f6db5"}
    fig, ax = plt.subplots(figsize=(7, 4.5))
    xs = list(range(ROUNDS + 1))
    for mode in MODES:
        m = [pr["compliance"][0] * 100 for pr in s[mode]["per_round"]]
        lo = [pr["compliance"][1] * 100 for pr in s[mode]["per_round"]]
        hi = [pr["compliance"][2] * 100 for pr in s[mode]["per_round"]]
        ax.plot(xs, m, marker="o", color=colors[mode], label=CONDITION_NAMES[mode])
        ax.fill_between(xs, lo, hi, color=colors[mode], alpha=0.15)
    ax.set_xticks(xs)
    ax.set_xlabel("Revision round (0 = first draft)")
    ax.set_ylabel("Compliant portfolios (%)")
    ax.set_ylim(-2, 102)
    ax.set_title("Does explained math feedback help the AI follow the rules?")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ---------- Main ----------

async def run_all(jobs: list[tuple[Client, int]], concurrency: int) -> list[dict]:
    """Run every client-trial, `concurrency` at a time."""
    gate = asyncio.Semaphore(concurrency)

    async def one(client: Client, trial: int) -> dict | None:
        async with gate:
            start = time.time()
            try:
                result = await asyncio.to_thread(run_trial, client, trial)
            except Exception as e:
                print(f"  {client.client_id} t{trial}: FAILED ({e})", flush=True)
                return None
            got = {m: result["conditions"][m]["rounds_to_comply"] for m in MODES}
            print(f"  {client.client_id} t{trial}: rounds to comply {got} ({time.time() - start:.0f}s)", flush=True)
            return result

    results = await asyncio.gather(*(one(c, t) for c, t in jobs))
    return [r for r in results if r is not None]


def main() -> None:
    parser = argparse.ArgumentParser(description="The feedback experiment (MASTER 10.3).")
    parser.add_argument("--clients", type=int, default=None, help="only the first N feasible clients")
    parser.add_argument("--trials", type=int, default=3, help="trials per client")
    parser.add_argument("--concurrency", type=int, default=4, help="client-trials run at the same time")
    parser.add_argument("--ids", type=str, default=None, help="only these clients, e.g. C91,C92")
    parser.add_argument("--live", action="store_true",
                        help="use the fast live model (config.LIVE_MODEL, capped answers) instead of the default")
    parser.add_argument("--suffix", type=str, default="",
                        help="output names get _<suffix>, e.g. experiment_mini.md (keeps earlier runs)")
    parser.add_argument("--note", type=str, default="", help="extra line for the results header")
    parser.add_argument("--log", type=str, default=None,
                        help="where to write one line per LLM call (default: eval/results/llm_calls[_suffix].jsonl)")
    args = parser.parse_args()
    tail = f"_{args.suffix}" if args.suffix else ""
    if args.log is None:
        args.log = os.path.join(RESULTS_DIR, f"llm_calls{tail}.jsonl")
    if args.live:
        llm.use_live_model()

    # One JSON line per LLM call, so we can see why calls are slow.
    os.makedirs(os.path.dirname(args.log), exist_ok=True)
    handler = logging.FileHandler(args.log)
    handler.setFormatter(logging.Formatter("%(message)s"))
    llm.call_log.addHandler(handler)
    llm.call_log.setLevel(logging.INFO)
    llm.call_log.propagate = False

    clients = [c for c in load_all_clients() if is_feasible(c)]  # infeasible clients can't comply
    if args.ids:
        wanted = [i.strip() for i in args.ids.split(",")]
        clients = [c for c in clients if c.client_id in wanted]
    clients = clients[:args.clients] if args.clients else clients
    jobs = [(c, t) for c in clients for t in range(1, args.trials + 1)]
    print(f"Experiment: {len(clients)} feasible clients x {args.trials} trials = {len(jobs)} client-trials", flush=True)

    trials = asyncio.run(run_all(jobs, args.concurrency))
    if not trials:
        raise SystemExit("Every client-trial failed; nothing to report.")
    summary = summarize(trials)
    # Say exactly what produced these numbers, so different runs are never mixed up.
    summary["model"] = {"chair": llm.model_id_for("chair"), "analyst": llm.model_id_for("analyst")}
    summary["clients"] = sorted({t["client_id"] for t in trials})
    summary["run_note"] = (f"Model: {summary['model']['chair']} (temperature {TEMPERATURE}). "
                           f"Clients: {', '.join(summary['clients'])}. " + args.note).strip()

    os.makedirs(RESULTS_DIR, exist_ok=True)
    md_path = os.path.join(RESULTS_DIR, f"experiment{tail}.md")
    with open(os.path.join(RESULTS_DIR, f"experiment{tail}.json"), "w") as f:
        json.dump({"summary": summary, "trials": trials}, f, indent=2)
    write_markdown(summary, md_path)
    plot_curves(summary, os.path.join(RESULTS_DIR, f"learning_curves{tail}.png"))
    print(open(md_path).read())


if __name__ == "__main__":
    main()
