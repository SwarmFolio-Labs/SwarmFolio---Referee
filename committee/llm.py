"""
The LLM layer (MASTER 8): one function, complete_json(), that asks an LLM a question
and always gives back a validated Pydantic object.

This is the ONLY file that imports LangChain. The provider (asi1, gemini, anthropic)
is a single setting in config.py, so the rest of the committee never cares which LLM it is.
"""

import contextvars
import hashlib
import json
import logging
import os
import re
import threading
import time
from contextlib import contextmanager

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, ValidationError

import config

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")

# One JSON line per real LLM call (seconds + tokens). Silent unless someone attaches a handler
# (the experiment writes them to a file, to see why calls are slow).
call_log = logging.getLogger("swarmfolio.llm")

# Analysts get a little creativity; the Chair should be steady and repeatable.
TEMPERATURE = {"analyst": 0.2, "chair": 0.0}

# The experiment (MASTER 10.3) needs several genuinely different samples of the same question:
# a higher temperature, and a trial tag in the prompt so each trial gets its own cache entry.
# A context variable carries this through asyncio.to_thread without changing any signatures.
_sampling: contextvars.ContextVar[dict | None] = contextvars.ContextVar("sampling", default=None)


# A "fresh run" skips the cache completely: no saved answers are reused and none are written, so a
# fresh demo run can never overwrite the curated cached answers. Carried like _sampling (contextvar).
_fresh: contextvars.ContextVar[bool] = contextvars.ContextVar("fresh", default=False)


@contextmanager
def fresh_run(on: bool = True):
    """Inside this block every LLM call asks the model again (no cache read, no cache write)."""
    token = _fresh.set(on or _fresh.get())
    try:
        yield
    finally:
        _fresh.reset(token)


def is_fresh() -> bool:
    """True inside fresh_run(): the answers are new, not replayed from the cache."""
    return _fresh.get()


@contextmanager
def sampling(temperature: float, tag: str):
    """Inside this block every LLM call uses `temperature` and ends its prompt with `tag`."""
    token = _sampling.set({"temperature": temperature, "tag": tag})
    try:
        yield
    finally:
        _sampling.reset(token)


# Live mode: the Fetch agents switch this on (agents/brains.py) to use the fast LIVE_MODEL with
# capped answers. The experiment and eval never turn it on, so they keep their own model.
_live = {"on": False}

# The experiment can use another provider than .env's LLM_PROVIDER (e.g. Gemini), so the live
# agents keep ASI:One's quota for the demo. None = use config.LLM_PROVIDER.
_provider_override = {"name": None}
# One fixed model for every role, with NO fallback (so a whole experiment run uses a single model).
_model_override = {"id": None}


def use_live_model() -> None:
    """Make every LLM call in this process use config.LIVE_MODEL with capped answers (asi1 only)."""
    _live["on"] = True


def use_provider(name: str) -> None:
    """Make every LLM call in this process go to this provider ("asi1", "gemini" or "anthropic")."""
    if name not in config.MODELS:
        raise ValueError(f"Unknown provider {name!r} (use one of {', '.join(config.MODELS)})")
    _provider_override["name"] = name


def use_model(model_id: str) -> None:
    """Pin every LLM call in this process to this one model, and turn the fallback model off."""
    _model_override["id"] = model_id


def provider() -> str:
    """The provider answering right now."""
    return _provider_override["name"] or config.LLM_PROVIDER


def _is_live() -> bool:
    return _live["on"] and provider() == "asi1"


def model_id_for(role: str) -> str:
    """The model that answers for this role right now (the live model when live mode is on)."""
    if _model_override["id"]:
        return _model_override["id"]
    if _is_live():
        return config.LIVE_MODEL
    return config.MODELS[provider()][role]


def get_model(role: str, model_id: str | None = None):
    """Build the LangChain chat model for this role ("analyst" or "chair") and the current provider.
    model_id overrides the usual model (used for the Gemini fallback)."""
    name = provider()
    model_id = model_id or model_id_for(role)
    temperature = TEMPERATURE[role]
    if _sampling.get() is not None:
        temperature = _sampling.get()["temperature"]

    # Imports live inside each branch so you only need the package for the provider you use.
    if name == "asi1":
        from langchain_openai import ChatOpenAI
        # ASI:One speaks the OpenAI API, so the OpenAI class works with a different base URL.
        max_tokens = config.LIVE_MAX_TOKENS[role] if _is_live() else None  # None = no cap
        return ChatOpenAI(model=model_id, base_url=config.ASI1_BASE_URL,
                          api_key=os.getenv("ASI1_API_KEY"), temperature=temperature, max_tokens=max_tokens)
    if name == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        # max_retries=1: no hidden retries inside the library; complete_json does the waiting itself.
        return ChatGoogleGenerativeAI(model=model_id, google_api_key=os.getenv("GEMINI_API_KEY"),
                                      temperature=temperature, max_retries=1)
    if name == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model_id, api_key=os.getenv("ANTHROPIC_API_KEY"),
                             temperature=temperature)
    raise ValueError(f"Unknown LLM_PROVIDER {name!r} (use asi1, gemini or anthropic)")


def _cache_path(role: str, system: str, user: str, model_id: str | None = None) -> str:
    """The cache file for this exact question: a hash of provider + model + system + user prompt.
    model_id = the model that actually answered (live, experiment and fallback answers never mix)."""
    model_id = model_id or model_id_for(role)
    key = hashlib.sha256(f"{provider()}\n{model_id}\n{system}\n{user}".encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{key}.json")


def _strip_fences(text: str) -> str:
    """LLMs love wrapping JSON in ```json ... ``` fences; take them off."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def _text_of(reply) -> str:
    """The plain text of a model reply (some providers return a list of content parts)."""
    content = reply.content
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)


def _model_name(model, role: str) -> str:
    """The model id a LangChain chat model object was built with."""
    name = getattr(model, "model_name", None) or getattr(model, "model", None)
    return str(name).removeprefix("models/") if name else model_id_for(role)


def _log_call(role: str, step: str, schema: type[BaseModel], seconds: float, reply=None, ok: bool = True,
              model: str | None = None, **extra) -> None:
    """Record one LLM call: how long it took and how many tokens went in and out."""
    usage = getattr(reply, "usage_metadata", None) or {}
    call_log.info(json.dumps({
        "time": time.strftime("%H:%M:%S"), "provider": provider(), "role": role, "step": step,
        "model": model or model_id_for(role), "schema": schema.__name__, "seconds": round(seconds, 2), "ok": ok,
        "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"), **extra,
    }))


# ---------- Waiting out overload / rate limits (Gemini) ----------

FAILURES_BEFORE_FALLBACK = 2  # after 2 overloaded/rate-limited tries, use config.GEMINI_FALLBACK_MODEL
MAX_WAITS = 4                 # then give up on this call
MAX_WAIT_S = 120              # never sleep longer than this for one retry

_streak_lock = threading.Lock()
_failure_streak = {"n": 0}    # LLM calls that finally failed, in a row (reset by any success)


def failure_streak() -> int:
    """How many complete_json calls in a row have failed (the experiment stops at 3)."""
    return _failure_streak["n"]


def _record(success: bool) -> None:
    with _streak_lock:
        _failure_streak["n"] = 0 if success else _failure_streak["n"] + 1


def _status_code(error: BaseException) -> int | None:
    """The HTTP status behind an error (looks through the chain of causes, e.g. Google's ClientError)."""
    seen = error
    while seen is not None:
        for attr in ("code", "status_code"):
            value = getattr(seen, attr, None)
            if isinstance(value, int):
                return value
        seen = seen.__cause__ or seen.__context__
    match = re.search(r"\b(429|503)\b", str(error))
    return int(match.group(1)) if match else None


def _is_retryable(error: BaseException) -> bool:
    """Overloaded (503) or rate-limited (429): worth waiting and trying again."""
    return _status_code(error) in (429, 503)


def _retry_after(error: BaseException) -> float | None:
    """Seconds the server asked us to wait: a Retry-After header, or Google's "retryDelay": "17s"."""
    seen = error
    while seen is not None:
        response = getattr(seen, "response", None)
        headers = getattr(response, "headers", None)
        if headers is not None:
            value = headers.get("retry-after") or headers.get("Retry-After")
            if value:
                try:
                    return float(value)
                except ValueError:
                    pass
        seen = seen.__cause__ or seen.__context__
    match = re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s", str(error))
    return float(match.group(1)) if match else None


def _ask_structured(model, role: str, system: str, user: str, schema: type[BaseModel]) -> BaseModel | None:
    """Plan A: let LangChain force the schema. Returns None if the provider can't do it."""
    start = time.time()
    try:
        # include_raw=True also hands back the raw reply, which carries the token counts.
        out = model.with_structured_output(schema, include_raw=True).invoke([("system", system), ("human", user)])
    except NotImplementedError:
        return None  # this model has no structured output at all: use Plan B
    except Exception as error:
        if _is_retryable(error):
            raise  # overloaded / rate-limited: complete_json waits and tries again
        _log_call(role, "structured", schema, time.time() - start, ok=False, model=_model_name(model, role))
        return None  # the call or its output failed: use Plan B
    result = out.get("parsed")
    if isinstance(result, dict):
        try:
            result = schema.model_validate(result)
        except ValidationError:
            result = None
    ok = isinstance(result, schema)
    _log_call(role, "structured", schema, time.time() - start, out.get("raw"), ok=ok, model=_model_name(model, role))
    return result if ok else None


def _ask_with_parser(model, role: str, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
    """Plan B: put the JSON format in the prompt, parse the reply, and retry once if it's invalid."""
    parser = PydanticOutputParser(pydantic_object=schema)
    prompt = f"{user}\n\n{parser.get_format_instructions()}\nReply with the JSON only."
    start = time.time()
    reply = model.invoke([("system", system), ("human", prompt)])
    try:
        result = schema.model_validate_json(_strip_fences(_text_of(reply)))
        _log_call(role, "parser", schema, time.time() - start, reply, model=_model_name(model, role))
        return result
    except ValidationError as error:
        _log_call(role, "parser", schema, time.time() - start, reply, ok=False, model=_model_name(model, role))
        # One retry, telling the model exactly what was wrong.
        retry = f"{prompt}\n\nYour last reply was not valid. The error was:\n{error}\nFix it and reply with the JSON only."
        start = time.time()
        reply = model.invoke([("system", system), ("human", retry)])
        try:
            result = schema.model_validate_json(_strip_fences(_text_of(reply)))
            _log_call(role, "retry", schema, time.time() - start, reply, model=_model_name(model, role))
            return result
        except ValidationError as error2:
            _log_call(role, "retry", schema, time.time() - start, reply, ok=False, model=_model_name(model, role))
            raise ValueError(f"The LLM gave invalid JSON twice for {schema.__name__}: {error2}") from error2


def complete_json(role: str, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
    """
    Ask the LLM and return a validated `schema` object.
    Same question twice -> the second answer comes from cache/ instantly (free and reproducible).
    On Gemini, an overloaded (503) or rate-limited (429) call waits and retries; after 2 such
    failures it moves to the lighter fallback model; after 4 it gives up.
    """
    if _sampling.get() is not None:
        user = f"{user}\n\n({_sampling.get()['tag']})"  # different trial -> different prompt -> own cache entry

    primary = model_id_for(role)
    # A pinned model (use_model) never falls back: the run must stay on one model.
    fallback = config.GEMINI_FALLBACK_MODEL if provider() == "gemini" and not _model_override["id"] else None
    for model_id in (primary, fallback):
        if is_fresh():
            break  # fresh run: never replay a saved answer
        if model_id and os.path.exists(_cache_path(role, system, user, model_id)):
            with open(_cache_path(role, system, user, model_id)) as f:
                return schema.model_validate(json.load(f))

    model_id, waits = primary, 0
    while True:
        model = get_model(role, model_id)
        try:
            result = _ask_structured(model, role, system, user, schema)
            if result is None:
                result = _ask_with_parser(model, role, system, user, schema)
            break
        except Exception as error:
            if provider() != "gemini" or not _is_retryable(error) or waits >= MAX_WAITS:
                _record(success=False)
                raise
            waits += 1
            wait = min(MAX_WAIT_S, _retry_after(error) or 5 * 2 ** (waits - 1))  # 5, 10, 20, 40 s
            _log_call(role, "wait", schema, 0, ok=False, model=model_id,
                      status=_status_code(error), wait_s=round(wait, 1))
            if waits == FAILURES_BEFORE_FALLBACK and fallback:
                model_id = fallback
            time.sleep(wait)

    _record(success=True)
    if is_fresh():
        return result  # fresh run: don't touch the cache
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(_cache_path(role, system, user, model_id), "w") as f:  # keyed on the model that answered
        f.write(result.model_dump_json(indent=2))
    return result
