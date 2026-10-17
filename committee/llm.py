"""
The LLM layer (MASTER 8): one function, complete_json(), that asks an LLM a question
and always gives back a validated Pydantic object.

This is the ONLY file that imports LangChain. The provider (asi1, gemini, anthropic)
is a single setting in config.py, so the rest of the committee never cares which LLM it is.
"""

import hashlib
import json
import os
import re

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, ValidationError

import config

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")

# Analysts get a little creativity; the Chair should be steady and repeatable.
TEMPERATURE = {"analyst": 0.2, "chair": 0.0}


def get_model(role: str):
    """Build the LangChain chat model for this role ("analyst" or "chair") and the current provider."""
    provider = config.LLM_PROVIDER
    model_id = config.MODELS[provider][role]
    temperature = TEMPERATURE[role]

    # Imports live inside each branch so you only need the package for the provider you use.
    if provider == "asi1":
        from langchain_openai import ChatOpenAI
        # ASI:One speaks the OpenAI API, so the OpenAI class works with a different base URL.
        return ChatOpenAI(model=model_id, base_url=config.ASI1_BASE_URL,
                          api_key=os.getenv("ASI1_API_KEY"), temperature=temperature)
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
    model_id = config.MODELS[provider][role]
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


def _ask_structured(model, system: str, user: str, schema: type[BaseModel]) -> BaseModel | None:
    """Plan A: let LangChain force the schema. Returns None if the provider can't do it."""
    try:
        result = model.with_structured_output(schema).invoke([("system", system), ("human", user)])
    except Exception:
        return None  # not supported, or the model's output didn't fit: use Plan B
    if isinstance(result, schema):
        return result
    if isinstance(result, dict):
        try:
            return schema.model_validate(result)
        except ValidationError:
            return None
    return None


def _ask_with_parser(model, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
    """Plan B: put the JSON format in the prompt, parse the reply, and retry once if it's invalid."""
    parser = PydanticOutputParser(pydantic_object=schema)
    prompt = f"{user}\n\n{parser.get_format_instructions()}\nReply with the JSON only."
    try:
        return schema.model_validate_json(_strip_fences(_text_of(model.invoke([("system", system), ("human", prompt)]))))
    except ValidationError as error:
        # One retry, telling the model exactly what was wrong.
        retry = f"{prompt}\n\nYour last reply was not valid. The error was:\n{error}\nFix it and reply with the JSON only."
        reply = model.invoke([("system", system), ("human", retry)])
        try:
            return schema.model_validate_json(_strip_fences(_text_of(reply)))
        except ValidationError as error2:
            raise ValueError(f"The LLM gave invalid JSON twice for {schema.__name__}: {error2}") from error2


def complete_json(role: str, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
    """
    Ask the LLM and return a validated `schema` object.
    Same question twice -> the second answer comes from cache/ instantly (free and reproducible).
    """
    path = _cache_path(role, system, user)
    if os.path.exists(path):
        with open(path) as f:
            return schema.model_validate(json.load(f))

    model = get_model(role)
    result = _ask_structured(model, system, user, schema)
    if result is None:
        result = _ask_with_parser(model, system, user, schema)

    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(path, "w") as f:
        f.write(result.model_dump_json(indent=2))
    return result
