"""Natural-language catalog search — converts a free-form sentence into structured search
filters (a topic keyword + a state, the only two dimensions our catalog search actually
supports). Bounded by a strict timeout (see service.py) so an unavailable/slow LLM degrades
instantly to plain keyword search over the raw text — natural-language parsing is a
convenience layer on top of the always-working keyword search, never a replacement for it."""

from pydantic import BaseModel

from app.models.scheme import SchemeOut


class NLSearchRequest(BaseModel):
    text: str


class NLSearchDraft(BaseModel):
    """LLM structured-output schema for one parse attempt."""

    topic: str
    """The core subject to search for, with location/filler words stripped — e.g. "farmer
    income support" from "I'm a farmer looking for income support in Maharashtra"."""
    state: str | None = None


class NLSearchResponse(BaseModel):
    interpreted_topic: str
    interpreted_state: str | None
    used_ai: bool
    """False when the LLM was unavailable/timed out and the raw text was used as a plain
    keyword search instead — never hidden from the caller."""
    schemes: list[SchemeOut]
