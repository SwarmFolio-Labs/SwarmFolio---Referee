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


def use_live_model() -> None:
    """Make every LLM call in this process use config.LIVE_MODEL with capped answers (asi1 only)."""
    _live["on"] = True


def _is_live() -> bool:
    return _live["on"] and config.LLM_PROVIDER == "asi1"


def model_id_for(role: str) -> str:
    """The model that answers for this role right now (the live model when live mode is on)."""
    if _is_live():
        return config.LIVE_MODEL
    return config.MODELS[config.LLM_PROVIDER][role]


def get_model(role: str):
    """Build the LangChain chat model for this role ("analyst" or "chair") and the current provider."""
    provider = config.LLM_PROVIDER
    model_id = model_id_for(role)
    temperature = TEMPERATURE[role]
    if _sampling.get() is not None:
        temperature = _sampling.get()["temperature"]

    # Imports live inside each branch so you only need the package for the provider you use.
    if provider == "asi1":
        from langchain_openai import ChatOpenAI
        # ASI:One speaks the OpenAI API, so the OpenAI class works with a different base URL.
        max_tokens = config.LIVE_MAX_TOKENS[role] if _is_live() else None  # None = no cap
        return ChatOpenAI(model=model_id, base_url=config.ASI1_BASE_URL,
                          api_key=os.getenv("ASI1_API_KEY"), temperature=temperature, max_tokens=max_tokens)
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model_id, google_api_key=os.getenv("GEMINI_API_KEY"),
                                      temperature=temperature)
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model_id, api_key=os.getenv("ANTHROPIC_API_KEY"),
                             temperature=temperature)
    raise ValueError(f"Unknown LLM_PROVIDER {provider!r} (use asi1, gemini or anthropic)")


def _cache_path(role: str, system: str, user: str) -> str:
    """The cache file for this exact question: a hash of provider + model + system + user prompt."""
    provider = config.LLM_PROVIDER
    model_id = model_id_for(role)  # live and experiment answers never share a cache entry
    key = hashlib.sha256(f"{provider}\n{model_id}\n{system}\n{user}".encode()).hexdigest()
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


def _log_call(role: str, step: str, schema: type[BaseModel], seconds: float, reply=None, ok: bool = True) -> None:
    """Record one LLM call: how long it took and how many tokens went in and out."""
    usage = getattr(reply, "usage_metadata", None) or {}
    call_log.info(json.dumps({
        "time": time.strftime("%H:%M:%S"), "provider": config.LLM_PROVIDER, "role": role, "step": step,
        "model": model_id_for(role), "schema": schema.__name__, "seconds": round(seconds, 2), "ok": ok,
        "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
    }))


def _ask_structured(model, role: str, system: str, user: str, schema: type[BaseModel]) -> BaseModel | None:
    """Plan A: let LangChain force the schema. Returns None if the provider can't do it."""
    start = time.time()
    try:
        # include_raw=True also hands back the raw reply, which carries the token counts.
        out = model.with_structured_output(schema, include_raw=True).invoke([("system", system), ("human", user)])
    except NotImplementedError:
        return None  # this model has no structured output at all: use Plan B
    except Exception:
        _log_call(role, "structured", schema, time.time() - start, ok=False)
        return None  # the call or its output failed: use Plan B
    result = out.get("parsed")
    if isinstance(result, dict):
        try:
            result = schema.model_validate(result)
        except ValidationError:
            result = None
    ok = isinstance(result, schema)
    _log_call(role, "structured", schema, time.time() - start, out.get("raw"), ok=ok)
    return result if ok else None


def _ask_with_parser(model, role: str, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
    """Plan B: put the JSON format in the prompt, parse the reply, and retry once if it's invalid."""
    parser = PydanticOutputParser(pydantic_object=schema)
    prompt = f"{user}\n\n{parser.get_format_instructions()}\nReply with the JSON only."
    start = time.time()
    reply = model.invoke([("system", system), ("human", prompt)])
    try:
        result = schema.model_validate_json(_strip_fences(_text_of(reply)))
        _log_call(role, "parser", schema, time.time() - start, reply)
        return result
    except ValidationError as error:
        _log_call(role, "parser", schema, time.time() - start, reply, ok=False)
        # One retry, telling the model exactly what was wrong.
        retry = f"{prompt}\n\nYour last reply was not valid. The error was:\n{error}\nFix it and reply with the JSON only."
        start = time.time()
        reply = model.invoke([("system", system), ("human", retry)])
        try:
            result = schema.model_validate_json(_strip_fences(_text_of(reply)))
            _log_call(role, "retry", schema, time.time() - start, reply)
            return result
        except ValidationError as error2:
            _log_call(role, "retry", schema, time.time() - start, reply, ok=False)
            raise ValueError(f"The LLM gave invalid JSON twice for {schema.__name__}: {error2}") from error2


def complete_json(role: str, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
    """
    Ask the LLM and return a validated `schema` object.
    Same question twice -> the second answer comes from cache/ instantly (free and reproducible).
    """
    if _sampling.get() is not None:
        user = f"{user}\n\n({_sampling.get()['tag']})"  # different trial -> different prompt -> own cache entry
    path = _cache_path(role, system, user)
    if os.path.exists(path):
        with open(path) as f:
            return schema.model_validate(json.load(f))

    model = get_model(role)
    result = _ask_structured(model, role, system, user, schema)
    if result is None:
        result = _ask_with_parser(model, role, system, user, schema)

    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(path, "w") as f:
        f.write(result.model_dump_json(indent=2))
    return result
