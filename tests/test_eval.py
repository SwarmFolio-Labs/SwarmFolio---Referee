"""Offline tests for the evaluation helpers (A10). No LLM: the committee and Chair are faked."""

import pytest

from eval import experiment, run_eval
from referee.schema import Proposal

PATEL = run_eval.load_all_clients()[1]
GOOD = {"JNJ": 0.30, "MSFT": 0.15, "GOOGL": 0.10, "KO": 0.10, "PG": 0.10, "TLT": 0.10, "WMT": 0.10, "NVDA": 0.05}
BAD = {"NVDA": 0.41, "JNJ": 0.30, "GOOGL": 0.15, "XOM": 0.14}


def test_rounds_to_comply():
    assert experiment.rounds_to_comply([False, False, True, True]) == 2
    assert experiment.rounds_to_comply([True, True, True, True]) == 0
    assert experiment.rounds_to_comply([False] * 4) is None


def test_bootstrap_ci_brackets_the_mean_and_is_deterministic():
    values = [0.0, 1.0, 1.0, 0.0, 1.0, 1.0]
    m, lo, hi = experiment.bootstrap_ci(values)
    assert m == pytest.approx(4 / 6) and lo <= m <= hi
    assert experiment.bootstrap_ci(values) == (m, lo, hi)  # fixed seed -> same answer
    assert experiment.bootstrap_ci([1.0, 1.0]) == (1.0, 1.0, 1.0)


def test_paired_comparison_counts_and_never_is_worst():
    out = experiment.paired_comparison([1, 2, None, 1], [2, 2, 1, None])
    assert (out["fewer"], out["same"], out["more"]) == (2, 1, 1)
    assert 0 < out["p_value"] <= 1
    assert experiment.paired_comparison([1], [1])["p_value"] == 1.0  # all ties: no evidence either way


def test_measure_uses_the_referee():
    good, bad = experiment.measure(PATEL, GOOD), experiment.measure(PATEL, BAD)
    assert good["compliant"] and good["n_broken"] == 0 and good["violation_pp"] == 0
    assert not bad["compliant"] and bad["n_broken"] == 3
    assert bad["violation_pp"] == pytest.approx(6 + 14 + 2.8, abs=0.2)  # NVDA +6pp, XOM 14pp, vol +2.8pp


def test_run_condition_stops_early_and_carries_forward(monkeypatch):
    """The Chair fixes the portfolio in round 1; rounds 2-3 just repeat the compliant state."""
    calls = []
    monkeypatch.setattr(experiment, "chair_revise_with",
                        lambda c, p, text, stances=None: calls.append(text) or Proposal(weights=GOOD, thesis="t", reasons={}))
    history = experiment.run_condition(PATEL, Proposal(weights=BAD, thesis="t", reasons={}), "explained")
    assert [s["compliant"] for s in history] == [False, True, True, True]
    assert len(calls) == 1 and "41.0%" in calls[0]  # explained feedback has the numbers


def test_summarize_and_finding_from_fake_trials():
    def trial(rounds_self, rounds_bare, rounds_expl):
        def cond(k):
            states = [{"compliant": i >= k if k is not None else False, "n_broken": 0 if (k is not None and i >= k) else 1,
                       "violation_pp": 0.0, "violation_count": 0, "weights": {}} for i in range(4)]
            return {"rounds": states, "rounds_to_comply": k, "capital_moved": 0.1}
        return {"conditions": {"self": cond(rounds_self), "bare": cond(rounds_bare), "explained": cond(rounds_expl)}}
    s = experiment.summarize([trial(None, 2, 1), trial(3, 1, 1), trial(None, None, 2)])
    assert s["explained"]["per_round"][-1]["compliance"][0] == 1.0
    assert s["self"]["per_round"][-1]["compliance"][0] == pytest.approx(1 / 3)
    assert (s["C_vs_B"]["fewer"], s["C_vs_B"]["same"], s["C_vs_B"]["more"]) == (2, 1, 0)
    text = experiment.finding_text(s)
    assert "100% with the explained" in text and "33% with self-check" in text


def test_eval_metrics_from_rows():
    rows = [
        {"feasible": True, "first_failed": 2, "last_failed": 1, "final_failed": 0, "repaired": True,
         "capital_moved_by_repair": 0.2, "sharpe_change": 0.1, "verdict": "VIOLATIONS_REPAIRED",
         "conflict_set": [], "planted_conflict": None, "rounds": 4, "stances": ["concede", "defend"]},
        {"feasible": True, "first_failed": 0, "last_failed": 0, "final_failed": 0, "repaired": False,
         "capital_moved_by_repair": None, "sharpe_change": None, "verdict": "PASS",
         "conflict_set": [], "planted_conflict": None, "rounds": 1, "stances": []},
        {"feasible": False, "first_failed": 1, "last_failed": 1, "final_failed": None, "repaired": False,
         "capital_moved_by_repair": None, "sharpe_change": None, "verdict": "RULES_INFEASIBLE",
         "conflict_set": ["R3", "R4"], "planted_conflict": ["R4", "R3"], "rounds": 1, "stances": []},
    ]
    m = run_eval.compute_metrics(rows)
    assert m["M1_first_violates"] == 0.5 and m["M2_last_own_violates"] == 0.5 and m["M3_final_passes"] == 1.0
    assert m["M4_median_capital_moved"] == 0.2 and m["M5_infeasible_detected"] == 1
    assert m["M5_conflict_matches_planted"] == 1 and m["M6_concede"] == 0.5 and m["M6_mean_rounds"] == 2


def test_a_failed_revision_fails_the_trial_instead_of_scoring_it(monkeypatch):
    """An API error (e.g. rate limit) must not count as 'the AI made no progress'."""
    def boom(*a, **k):
        raise RuntimeError("Error code: 429 - rate limit exceeded")
    monkeypatch.setattr(experiment, "chair_revise_with", boom)
    with pytest.raises(RuntimeError, match="429"):
        experiment.run_condition(PATEL, Proposal(weights=BAD, thesis="t", reasons={}), "explained")


def test_run_all_stops_starting_trials_after_a_failure_streak(monkeypatch):
    """After 3 failed LLM calls in a row, new client-trials are skipped (not scored); finished ones are kept."""
    import asyncio
    from committee import llm
    monkeypatch.setattr(llm, "_failure_streak", {"n": 0})
    calls = []

    def fake_trial(client, trial):
        calls.append(trial)
        if trial == 1:
            return {"conditions": {m: {"rounds_to_comply": 0} for m in experiment.MODES}}
        llm._failure_streak["n"] = 3  # this trial's LLM calls kept failing
        raise RuntimeError("503 UNAVAILABLE")
    monkeypatch.setattr(experiment, "run_trial", fake_trial)
    jobs = [(PATEL, t) for t in (1, 2, 3, 4)]
    trials, counts = asyncio.run(experiment.run_all(jobs, concurrency=1))
    assert len(trials) == 1 and counts == {"planned": 4, "failed": 1, "skipped": 2}
    assert calls == [1, 2]
