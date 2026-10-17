"""
Wire messages between the Fetch.ai agents (MASTER 5.5).

FROZEN after A0. A uAgents `Model` is Pydantic v1, but our models (models.py)
are Pydantic v2, and the two don't mix. So every message just carries JSON
text: the sender packs a v2 model into a string, the receiver unpacks it.
"""

from pydantic import BaseModel
from uagents import Model


class AnalysisRequestMsg(Model):
    agent: str
    payload: str  # AnalysisRequest as JSON


class MemoMsg(Model):
    payload: str  # Memo as JSON


class ReviewRequestMsg(Model):
    agent: str
    payload: str  # ReviewRequest as JSON


class StanceMsg(Model):
    payload: str  # Stance as JSON


class VerifyRequestMsg(Model):
    payload: str  # VerifyRequest as JSON


class ReceiptMsg(Model):
    payload: str  # Receipt as JSON


class ErrorMsg(Model):
    error: str  # sent back instead of crashing


def pack(model: BaseModel) -> str:
    """Turn a Pydantic v2 model into JSON text for a wire message."""
    return model.model_dump_json()


def unpack(cls, text: str):
    """Turn JSON text from a wire message back into a Pydantic v2 model of type `cls`."""
    return cls.model_validate_json(text)
