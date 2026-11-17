"""Question builders: plain dicts in the System One wire format. No SDK needed.

They produce exactly what the TypeSafe SDK sends (``{"type", "instructions", "criteria"}``), so
existing question wording moves over unchanged. Which types a model accepts is checked by the
client against ``providers.capabilities()`` before anything is sent.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

Instructions = Any  # a string, or an object/array (structured instructions, image or audio parts)


def _q(qtype: str, instructions: Instructions, **fields: Any) -> dict:
    if instructions in (None, ""):
        raise ValueError(f"{qtype} question needs instructions")
    out = {"type": qtype, "instructions": instructions}
    out.update({k: v for k, v in fields.items() if v is not None})
    return out


def noul(instructions: Instructions, criteria: Mapping[str, Any] | None = None) -> dict:
    """Probability that a statement is true. ``criteria`` = optional {"true": ..., "false": ...}."""
    if criteria is not None and not set(criteria) <= {"true", "false"}:
        raise ValueError("noul criteria keys must be 'true' and/or 'false'")
    return _q("noul", instructions, criteria=dict(criteria) if criteria is not None else None)


def choice(instructions: Instructions, criteria: Mapping[str, Any], *, multiple: bool | None = None) -> dict:
    """One option from ``criteria`` ({option_name: description}). ``multiple=True`` = every option
    that applies (Liquid d1.2 / d1.2-ultra)."""
    if not criteria:
        raise ValueError("choice needs at least one option in criteria")
    return _q("choice", instructions, criteria=dict(criteria), multiple=True if multiple else None)


def score(instructions: Instructions, criteria: Sequence[Any] | Mapping[str, Any]) -> dict:
    """A position on ordered levels: a list of level descriptions, lowest first."""
    if not criteria:
        raise ValueError("score needs at least two levels in criteria")
    crit = dict(criteria) if isinstance(criteria, Mapping) else list(criteria)
    if len(crit) < 2:
        raise ValueError("score needs at least two levels in criteria")
    return _q("score", instructions, criteria=crit)


def box(instructions: Instructions) -> dict:
    """Locate one object in an image in the state."""
    return _q("box", instructions)


def question(qtype: str, instructions: Instructions, **fields: Any) -> dict:
    """Any other type a provider documents (e.g. Liquid ``text``, ``number``, ``date``, ``spans``,
    ``boxes``). Fields are passed through as written; see the provider's docs for their names."""
    return _q(qtype, instructions, **fields)


__all__ = ["noul", "choice", "score", "box", "question"]
