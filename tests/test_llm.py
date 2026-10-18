"""Offline tests for committee/llm.py (MASTER 8). A fake chat model stands in for the real LLM."""

import os

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from pydantic import BaseModel

from committee import llm


class Answer(BaseModel):
    ticker: str
    weight: float


class CountingFake(FakeListChatModel):
    """A fake LLM that replies from a list and counts how often it was called."""
    calls: int = 0
    prompts: list = []

    def invoke(self, *args, **kwargs):
        self.calls += 1
        self.prompts.append(args[0][-1][1])  # the human message text
        return super().invoke(*args, **kwargs)


@pytest.fixture
def fake(monkeypatch, tmp_path):
    """Point the cache at a temp folder and let each test choose the fake's replies."""
    monkeypatch.setattr(llm, "CACHE_DIR", str(tmp_path))

    def make(replies):
        model = CountingFake(responses=replies)
        monkeypatch.setattr(llm, "get_model", lambda role, model_id=None: model)
        return model
    return make


def test_parses_fenced_json(fake):
    """Fake models can't do with_structured_output, so this goes through the parser fallback."""
    fake(['```json\n{"ticker": "JNJ", "weight": 0.3}\n```'])
    assert llm.complete_json("analyst", "sys", "user", Answer) == Answer(ticker="JNJ", weight=0.3)


def test_retries_once_after_bad_json(fake):
    model = fake(["not json at all", '{"ticker": "MSFT", "weight": 0.7}'])
    assert llm.complete_json("chair", "sys", "user", Answer).ticker == "MSFT"
    assert model.calls == 2


def test_gives_up_after_two_bad_replies(fake):
    fake(["nope", '{"ticker": "MSFT"}'])
    with pytest.raises(ValueError, match="invalid JSON twice"):
        llm.complete_json("chair", "sys", "user", Answer)


def test_second_identical_call_comes_from_cache(fake):
    model = fake(['{"ticker": "JNJ", "weight": 0.3}'])
    first = llm.complete_json("analyst", "sys", "user", Answer)
    second = llm.complete_json("analyst", "sys", "user", Answer)
    assert first == second
    assert model.calls == 1  # the second answer never touched the LLM


def test_strip_fences():
    assert llm._strip_fences('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert llm._strip_fences('{"a": 1}') == '{"a": 1}'


def test_sampling_changes_temperature_and_prompt(fake):
    """Inside llm.sampling(), prompts carry the trial tag, so each trial gets its own cache entry."""
    model = fake(['{"ticker": "JNJ", "weight": 0.3}', '{"ticker": "MSFT", "weight": 0.7}'])
    first = llm.complete_json("chair", "sys", "user", Answer)
    with llm.sampling(0.7, "Trial 2"):
        second = llm.complete_json("chair", "sys", "user", Answer)
    assert first.ticker == "JNJ" and second.ticker == "MSFT"  # not served from the first call's cache
    assert model.prompts[-1].startswith("user\n\n(Trial 2)")


def test_sampling_sets_model_temperature(monkeypatch):
    monkeypatch.setattr(llm.config, "LLM_PROVIDER", "asi1")
    monkeypatch.setenv("ASI1_API_KEY", "test-not-a-real-key")
    with llm.sampling(0.7, "Trial 1"):
        assert llm.get_model("chair").temperature == 0.7
    assert llm.get_model("chair").temperature == 0.0


def test_live_mode_uses_live_model_with_capped_tokens(monkeypatch):
    """Live agents: fast model, capped answers, and their own cache entries."""
    monkeypatch.setattr(llm.config, "LLM_PROVIDER", "asi1")
    monkeypatch.setenv("ASI1_API_KEY", "test-not-a-real-key")
    normal_path = llm._cache_path("chair", "sys", "user")
    assert llm.get_model("chair").max_tokens is None
    llm.use_live_model()
    model = llm.get_model("chair")
    assert model.model_name == llm.config.LIVE_MODEL and model.max_tokens == llm.config.LIVE_MAX_TOKENS["chair"]
    assert llm.get_model("analyst").max_tokens == llm.config.LIVE_MAX_TOKENS["analyst"]
    assert llm._cache_path("chair", "sys", "user") != normal_path


def test_live_mode_is_ignored_for_other_providers(monkeypatch):
    monkeypatch.setattr(llm.config, "LLM_PROVIDER", "anthropic")
    llm.use_live_model()
    assert llm.model_id_for("chair") == llm.config.MODELS["anthropic"]["chair"]


# ---------- Gemini: waiting out 429/503, fallback model, failure streak ----------

class Overloaded(Exception):
    """Looks like Google's error: an HTTP code and (sometimes) a retryDelay hint."""
    def __init__(self, code=503, text="UNAVAILABLE"):
        super().__init__(f"{code} {text}")
        self.code = code


class Flaky(CountingFake):
    """Fails `fail_times` times with an overload error, then answers."""
    fail_times: int = 0
    error_code: int = 503

    def invoke(self, *args, **kwargs):
        if self.fail_times > 0:
            self.fail_times -= 1
            self.calls += 1
            raise Overloaded(self.error_code, 'quota "retryDelay": "7s"' if self.error_code == 429 else "UNAVAILABLE")
        return super().invoke(*args, **kwargs)


@pytest.fixture
def gemini(monkeypatch, tmp_path):
    """Gemini provider, temp cache, no real sleeping; returns (make_model, used_model_ids, sleeps)."""
    monkeypatch.setattr(llm, "CACHE_DIR", str(tmp_path))
    llm.use_provider("gemini")
    used, sleeps = [], []
    monkeypatch.setattr(llm.time, "sleep", lambda s: sleeps.append(s))

    def make(fail_times, code=503):
        model = Flaky(responses=['{"ticker": "JNJ", "weight": 0.3}'] * 3, fail_times=fail_times, error_code=code)
        monkeypatch.setattr(llm, "get_model", lambda role, model_id=None: used.append(model_id) or model)
        return model
    return make, used, sleeps


def test_gemini_overload_waits_then_succeeds(gemini):
    make, used, sleeps = gemini
    make(fail_times=1)
    assert llm.complete_json("chair", "s", "u", Answer).ticker == "JNJ"
    assert sleeps == [5]                       # backoff 5 s (no Retry-After given)
    assert used == ["gemini-3.5-flash"] * 2    # still the main model after 1 failure
    assert llm.failure_streak() == 0


def test_gemini_falls_back_to_lite_after_two_failures_and_caches_under_it(gemini):
    make, used, sleeps = gemini
    make(fail_times=2, code=429)
    llm.complete_json("chair", "s", "u", Answer)
    assert sleeps == [7, 7]                    # honours Google's retryDelay hint
    assert used[-1] == llm.config.GEMINI_FALLBACK_MODEL
    assert os.path.exists(llm._cache_path("chair", "s", "u", llm.config.GEMINI_FALLBACK_MODEL))
    assert not os.path.exists(llm._cache_path("chair", "s", "u", "gemini-3.5-flash"))
    llm.complete_json("chair", "s", "u", Answer)  # second ask: found under the fallback key
    assert len(used) == 3


def test_gemini_gives_up_after_four_waits_and_counts_the_streak(gemini):
    make, used, sleeps = gemini
    make(fail_times=10)
    with pytest.raises(Overloaded):
        llm.complete_json("chair", "s", "u", Answer)
    assert len(sleeps) == llm.MAX_WAITS and llm.failure_streak() == 1
    with pytest.raises(Overloaded):
        llm.complete_json("chair", "s", "other", Answer)
    assert llm.failure_streak() == 2


def test_non_retryable_errors_are_not_retried(gemini):
    make, used, sleeps = gemini
    make(fail_times=1, code=400)
    with pytest.raises(Overloaded):
        llm.complete_json("chair", "s", "u", Answer)
    assert sleeps == []


def test_asi1_errors_are_not_retried_here(fake, monkeypatch):
    """Only Gemini gets the wait-and-retry; the live agents on ASI:One keep failing fast."""
    model = fake([])
    monkeypatch.setattr(llm.time, "sleep", lambda s: (_ for _ in ()).throw(AssertionError("slept")))
    monkeypatch.setattr(model.__class__, "invoke", lambda self, *a, **k: (_ for _ in ()).throw(Overloaded(429)))
    with pytest.raises(Overloaded):
        llm.complete_json("chair", "s", "u", Answer)


def test_retry_after_parsing():
    assert llm._retry_after(Exception('429 RESOURCE_EXHAUSTED {"retryDelay": "17s"}')) == 17
    assert llm._retry_after(Exception("nothing here")) is None
    assert llm._status_code(Overloaded(503)) == 503


def test_pinned_model_never_falls_back(gemini):
    """use_model(): every call uses that one model, even after many 429/503s (it just keeps waiting)."""
    make, used, sleeps = gemini
    llm.use_model("gemini-3.5-flash-lite")
    make(fail_times=3)
    llm.complete_json("chair", "s", "u", Answer)
    assert set(used) == {"gemini-3.5-flash-lite"} and len(sleeps) == 3
    assert llm.model_id_for("analyst") == "gemini-3.5-flash-lite"


def test_fresh_run_skips_the_cache_both_ways(fake, tmp_path):
    """A fresh run asks the model again and leaves the cached answer untouched."""
    model = fake(['{"ticker": "JNJ", "weight": 0.3}', '{"ticker": "MSFT", "weight": 0.7}'])
    assert llm.complete_json("chair", "s", "u", Answer).ticker == "JNJ"     # cached now
    with llm.fresh_run():
        assert llm.is_fresh()
        assert llm.complete_json("chair", "s", "u", Answer).ticker == "MSFT"  # asked again
    assert not llm.is_fresh()
    assert llm.complete_json("chair", "s", "u", Answer).ticker == "JNJ"     # cache unchanged
    assert model.calls == 2
    with llm.fresh_run(False):
        assert not llm.is_fresh()
