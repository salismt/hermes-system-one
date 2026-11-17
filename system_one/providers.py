"""Provider registry for System One decision-model APIs.

Every provider here speaks the same contract: ``POST {base_url}/v1/systemone`` with a JSON body
``{"model", "state", "questions"}`` and a bearer key, answering ``{"model", "usage", "answers"}``.
Switching providers is a config change, never a code change.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit

SYSTEM_ONE_PATH = "/v1/systemone"


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    default_model: str
    key_env: str
    # USD per 1M input tokens, per model. "*" is the fallback for models not listed.
    usd_per_mtok: dict[str, float] = field(default_factory=dict)
    docs: str = ""
    # model -> capabilities; "*" is the fallback. None = unknown, nothing is checked (custom).
    caps: dict[str, "Capabilities"] | None = None

    def price_per_token(self, model: str, override_usd_per_mtok: float | None = None) -> float:
        if override_usd_per_mtok and override_usd_per_mtok > 0:
            return override_usd_per_mtok / 1_000_000
        rate = self.usd_per_mtok.get(model, self.usd_per_mtok.get("*"))
        if rate is None:
            raise ValueError(f"no price known for {self.name}/{model}; set usd_per_mtok in the plugin settings")
        return rate / 1_000_000


@dataclass(frozen=True)
class Capabilities:
    """What a model accepts. Requests outside it are refused before sending (and before billing)."""
    types: frozenset[str]
    choice_multiple: bool = False
    max_questions: int | None = None
    max_body_bytes: int | None = None


_JEV = Capabilities(frozenset({"noul", "choice", "score", "box"}))            # docs.typesafe.ai/go/primitives
_LIQUID_D12 = Capabilities(frozenset({"noul", "choice", "score", "text", "number", "date", "spans", "box",
                                      "boxes"}), choice_multiple=True, max_questions=128,
                           max_body_bytes=4_500_000)                          # docs.liquid.ai/api/guides/decisions
_LIQUID_OLD = Capabilities(frozenset({"noul", "choice", "score"}), max_questions=128,
                           max_body_bytes=4_500_000)                          # deprecated d1, d1.1, d1-ultra


# List prices checked 2026-11-17. Prices change: confirm on each provider's pricing page.
BUILTIN: dict[str, Provider] = {
    "jev": Provider(
        name="jev",
        base_url="https://api.typesafe.ai",
        default_model="jev-1.14.0",
        key_env="TYPESAFE_API_KEY",
        usd_per_mtok={"*": 0.042},
        docs="https://docs.typesafe.ai/go/models.md",
        caps={"*": _JEV},
    ),
    "liquid": Provider(
        name="liquid",
        base_url="https://api.liquid.ai/decisions",
        default_model="d1.2-ultra",
        key_env="LIQUID_API_KEY",
        usd_per_mtok={"d1.2-ultra": 0.042, "d1.2": 0.02},
        docs="https://docs.liquid.ai/lfm/models/d1",
        caps={"d1.2-ultra": _LIQUID_D12, "d1.2": _LIQUID_D12, "d1.1": _LIQUID_OLD, "d1-ultra": _LIQUID_OLD,
              "d1": _LIQUID_OLD},
    ),
    "custom": Provider(
        name="custom",
        base_url="",  # set base_url in the plugin settings
        default_model="",  # set model in the plugin settings
        key_env="SYSTEM_ONE_API_KEY",
        usd_per_mtok={},  # set usd_per_mtok in the plugin settings
        docs="Any endpoint that implements the System One contract.",
    ),
}


_LOOPBACK = {"localhost", "127.0.0.1", "::1"}


def check_url(url: str) -> None:
    """https:// to any host, or plain http:// to loopback only. No credentials in the URL."""
    u = urlsplit(url)
    if u.username or u.password or u.fragment or u.query:
        raise ValueError("base_url must not contain credentials, a query or a fragment")
    if not u.hostname:
        raise ValueError("base_url has no host")
    if u.scheme == "https":
        return
    if u.scheme == "http" and u.hostname in _LOOPBACK:
        return
    raise ValueError("base_url must be https:// (plain http:// is allowed only for localhost)")


class UnsupportedRequest(ValueError):
    """The request can't work on this provider/model. Raised before sending, so nothing is billed."""


@dataclass(frozen=True)
class Resolved:
    """A provider with the user's settings applied: everything one request needs except the key."""
    provider: str
    base_url: str
    model: str
    key_env: str
    price_per_token: float
    caps: Capabilities | None = None

    def check(self, body: dict, body_bytes: int) -> None:
        c = self.caps
        if c is None:
            return
        qs = body.get("questions") or {}
        if c.max_questions is not None and len(qs) > c.max_questions:
            raise UnsupportedRequest(f"{self.provider}/{self.model} takes at most {c.max_questions} questions "
                                     f"per request (got {len(qs)})")
        if c.max_body_bytes is not None and body_bytes > c.max_body_bytes:
            raise UnsupportedRequest(f"{self.provider}/{self.model} takes request bodies up to "
                                     f"{c.max_body_bytes} bytes (got {body_bytes})")
        for qid, q in qs.items():
            t = q.get("type")
            if t not in c.types:
                raise UnsupportedRequest(f"question {qid!r}: type {t!r} is not supported by "
                                         f"{self.provider}/{self.model} (supported: {', '.join(sorted(c.types))})")
            if t == "choice" and q.get("multiple") and not c.choice_multiple:
                raise UnsupportedRequest(f"question {qid!r}: choice with multiple is not supported by "
                                         f"{self.provider}/{self.model}")

    @property
    def url(self) -> str:
        return self.base_url.rstrip("/") + SYSTEM_ONE_PATH


def resolve(provider: str, *, model: str = "", base_url: str = "",
            usd_per_mtok: float | None = None) -> Resolved:
    name = (provider or "jev").strip().lower()
    if name not in BUILTIN:
        raise ValueError(f"unknown provider {name!r}; choose one of: {', '.join(BUILTIN)}")
    p = BUILTIN[name]
    base_url = (base_url or "").strip()
    if base_url and name != "custom":
        # A built-in provider's key only ever goes to that provider's own host. Otherwise one
        # changed setting (e.g. by a prompt-injected agent) would send the user's key elsewhere.
        raise ValueError(f"base_url only applies to provider 'custom' (it would redirect {p.key_env})")
    url = base_url or p.base_url
    mdl = (model or p.default_model).strip()
    if not url:
        raise ValueError(f"provider {name!r} needs base_url in the plugin settings")
    check_url(url)
    if not mdl:
        raise ValueError(f"provider {name!r} needs model in the plugin settings")
    caps = None if p.caps is None else p.caps.get(mdl, p.caps.get("*"))
    return Resolved(name, url, mdl, p.key_env, p.price_per_token(mdl, usd_per_mtok), caps)
