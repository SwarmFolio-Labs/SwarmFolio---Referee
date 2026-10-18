"""Offline tests for committee/llm.py (MASTER 8). A fake chat model stands in for the real LLM."""

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
        monkeypatch.setattr(llm, "get_model", lambda role: model)
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
