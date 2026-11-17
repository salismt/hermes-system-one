"""Provider registry for System One decision-model APIs.

Every provider here speaks the same contract: ``POST {base_url}{path}`` with a JSON body
``{"model", "state", "questions"}``, answering ``{"model", "usage", "answers"}``. Providers differ
only in data (URL, path, auth header, models, prices, what each model accepts), so switching
between them is a settings change, never a code change.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit

SYSTEM_ONE_PATH = "/v1/systemone"


@dataclass(frozen=True)
class Capabilities:
    """What a model accepts. Requests outside it are refused before sending (and before billing)."""
    types: frozenset[str]
    choice_multiple: bool = False
    max_questions: int | None = None
    max_body_bytes: int | None = None
    max_choice_options: int | None = None
    max_score_levels: int | None = None


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    default_model: str
    key_env: str
    # USD per 1M input tokens, per model. "*" is the fallback for models not listed.
    usd_per_mtok: dict[str, float] = field(default_factory=dict)
    docs: str = ""
    # model -> capabilities; "*" is the fallback. None = unknown, nothing is checked.
    caps: dict[str, Capabilities] | None = None
    path: str = SYSTEM_ONE_PATH
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer "
    key_optional: bool = False          # self-hosted servers often run without a key
    # Where base_url may point. "fixed": never changed (the key only goes to the vendor's host).
    # "hosts": only to the hosts/suffixes below. "any": any https URL, or http to loopback.
    base_url_rule: str = "fixed"
    allowed_hosts: frozenset[str] = frozenset()
    allowed_host_suffixes: tuple[str, ...] = ()
    base_url_required: bool = False
    base_url_root_only: bool = False    # the URL must be a bare origin (no path)
    model_required: bool = False

    def price_per_token(self, model: str, override_usd_per_mtok: float | None = None) -> float:
        if override_usd_per_mtok and override_usd_per_mtok > 0:
            return override_usd_per_mtok / 1_000_000
        rate = self.usd_per_mtok.get(model, self.usd_per_mtok.get("*"))
        if rate is None:
            raise ValueError(f"no price known for {self.name}/{model}; set usd_per_mtok in the plugin settings")
        return rate / 1_000_000


_CORE = frozenset({"noul", "choice", "score"})
_JEV = Capabilities(frozenset({"noul", "choice", "score", "box"}))            # docs.typesafe.ai/go/models
_LIQUID_D12 = Capabilities(frozenset({"noul", "choice", "score", "text", "number", "date", "spans", "box",
                                      "boxes"}), choice_multiple=True, max_questions=128,
                           max_body_bytes=4_500_000)                          # docs.liquid.ai/api/guides/decisions
_LIQUID_OLD = Capabilities(_CORE, max_questions=128, max_body_bytes=4_500_000)  # deprecated d1, d1.1, d1-ultra
_UPSTAGE = Capabilities(_CORE, max_choice_options=26)                       # console.upstage.ai/api/systemone
_AZURE = Capabilities(_CORE)                                                  # learn.microsoft.com (Decision-1)
# ollama.com/library/laya and /tev1: 1-64 questions, 2-26 options or levels, 64 KiB bodies
_OLLAMA_S1 = Capabilities(_CORE, max_questions=64, max_body_bytes=65_536, max_choice_options=26,
                          max_score_levels=26)


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
    "upstage": Provider(
        name="upstage",
        base_url="https://api.upstage.ai",
        default_model="solar-decide",
        key_env="UPSTAGE_API_KEY",
        usd_per_mtok={"solar-decide": 0.10},  # solar-decide-flash: no published price, set usd_per_mtok
        docs="https://console.upstage.ai/api/systemone",
        caps={"*": _UPSTAGE},
        base_url_rule="hosts",
        allowed_hosts=frozenset({"api.upstage.ai", "kr.api.upstage.ai"}),  # global, Korea region
    ),
    "azure": Provider(
        name="azure",
        base_url="",  # your Foundry resource endpoint, e.g. https://<name>.services.ai.azure.com
        default_model="",  # your deployment name
        key_env="AZURE_FOUNDRY_API_KEY",
        usd_per_mtok={"*": 0.042},
        docs="https://learn.microsoft.com/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision",
        caps={"*": _AZURE},
        path="/providers/microsoft/v1/systemone",
        auth_header="api-key",
        auth_prefix="",
        base_url_rule="hosts",
        allowed_host_suffixes=(".services.ai.azure.com", ".cognitiveservices.azure.com", ".openai.azure.com"),
        base_url_required=True,
        base_url_root_only=True,
        model_required=True,
    ),
    "ollama": Provider(
        name="ollama",
        base_url="http://127.0.0.1:11434",
        default_model="laya",  # also tev1 (4B), tev1:0.8b, or any decision model you pulled
        key_env="SYSTEM_ONE_LOCAL_API_KEY",  # local Ollama has no auth; only for an auth proxy
        usd_per_mtok={"*": 0.0},
        docs="https://ollama.com/library/laya",
        caps={"laya": _OLLAMA_S1, "tev1": _OLLAMA_S1},  # matched on the name before ':'; others unchecked
        key_optional=True,
        base_url_rule="any",
    ),
    "local": Provider(
        name="local",
        base_url="http://127.0.0.1:8080",  # llama.cpp's default
        default_model="",  # optional: a single-model server ignores it
        key_env="SYSTEM_ONE_LOCAL_API_KEY",
        usd_per_mtok={"*": 0.0},
        docs="Self-hosted System One server: llama.cpp llama-server, or any /v1/systemone server.",
        caps=None,  # depends on the server and model
        key_optional=True,
        base_url_rule="any",
    ),
    "custom": Provider(
        name="custom",
        base_url="",
        default_model="",
        key_env="SYSTEM_ONE_API_KEY",
        usd_per_mtok={},  # set usd_per_mtok in the plugin settings
        docs="Any hosted endpoint that implements the System One contract.",
        base_url_rule="any",
        base_url_required=True,
        model_required=True,
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


def _normalize(url: str, p: Provider) -> str:
    url = url.strip().rstrip("/")
    if url.endswith(p.path):  # people paste the full endpoint from the docs
        url = url[: -len(p.path)].rstrip("/")
    return url


def _check_host(url: str, p: Provider) -> None:
    host = (urlsplit(url).hostname or "").lower()
    if host in p.allowed_hosts or any(host.endswith(s) for s in p.allowed_host_suffixes):
        if p.base_url_root_only and urlsplit(url).path not in ("", "/"):
            raise ValueError(f"provider {p.name!r}: base_url must be the bare resource endpoint "
                             f"(e.g. https://{host}), without a project or API path")
        return
    allowed = sorted(p.allowed_hosts) + [f"*{s}" for s in p.allowed_host_suffixes]
    raise ValueError(f"provider {p.name!r}: base_url host {host!r} is not allowed "
                     f"(it would send {p.key_env} there); allowed: {', '.join(allowed)}")


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
    path: str = SYSTEM_ONE_PATH
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer "
    key_optional: bool = False

    def check(self, body: dict, body_bytes: int) -> None:
        c = self.caps
        if c is None:
            return
        where = f"{self.provider}/{self.model or 'default'}"
        qs = body.get("questions") or {}
        if c.max_questions is not None and len(qs) > c.max_questions:
            raise UnsupportedRequest(f"{where} takes at most {c.max_questions} questions per request (got {len(qs)})")
        if c.max_body_bytes is not None and body_bytes > c.max_body_bytes:
            raise UnsupportedRequest(f"{where} takes request bodies up to {c.max_body_bytes} bytes (got {body_bytes})")
        for qid, q in qs.items():
            t = q.get("type")
            if t not in c.types:
                raise UnsupportedRequest(f"question {qid!r}: type {t!r} is not supported by {where} "
                                         f"(supported: {', '.join(sorted(c.types))})")
            if t == "choice" and q.get("multiple") and not c.choice_multiple:
                raise UnsupportedRequest(f"question {qid!r}: choice with multiple is not supported by {where}")
            n = len(q.get("criteria") or {}) if t == "choice" else 0
            if c.max_choice_options is not None and n > c.max_choice_options:
                raise UnsupportedRequest(f"question {qid!r}: {where} takes at most {c.max_choice_options} "
                                         f"choice options (got {n}); split it or shortlist first")
            n = len(q.get("criteria") or []) if t == "score" else 0
            if c.max_score_levels is not None and n > c.max_score_levels:
                raise UnsupportedRequest(f"question {qid!r}: {where} takes at most {c.max_score_levels} "
                                         f"score levels (got {n})")

    @property
    def url(self) -> str:
        return self.base_url.rstrip("/") + self.path


def resolve(provider: str, *, model: str = "", base_url: str = "",
            usd_per_mtok: float | None = None) -> Resolved:
    name = (provider or "jev").strip().lower()
    if name not in BUILTIN:
        raise ValueError(f"unknown provider {name!r}; choose one of: {', '.join(BUILTIN)}")
    p = BUILTIN[name]
    given = _normalize(base_url, p) if (base_url or "").strip() else ""
    if given and p.base_url_rule == "fixed":
        # A built-in vendor's key only ever goes to that vendor's own host. Otherwise one changed
        # setting (e.g. by a prompt-injected agent) would send the user's key elsewhere.
        raise ValueError(f"base_url can't be changed for provider {name!r} (it would redirect {p.key_env})")
    url = given or p.base_url
    if not url:
        raise ValueError(f"provider {name!r} needs base_url in the plugin settings")
    check_url(url)
    if p.base_url_rule == "hosts":
        _check_host(url, p)
    mdl = (model or p.default_model).strip()
    if not mdl and p.model_required:
        what = "your deployment name" if name == "azure" else "a model"
        raise ValueError(f"provider {name!r} needs model_name in the plugin settings ({what})")
    caps = None
    if p.caps is not None:  # exact model, then its family ("laya:421m-english-bf16" -> "laya"), then "*"
        caps = p.caps.get(mdl) or p.caps.get(mdl.split(":", 1)[0]) or p.caps.get("*")
    return Resolved(name, url, mdl, p.key_env, p.price_per_token(mdl or "*", usd_per_mtok), caps,
                    p.path, p.auth_header, p.auth_prefix, p.key_optional)
