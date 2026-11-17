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

    def price_per_token(self, model: str, override_usd_per_mtok: float | None = None) -> float:
        if override_usd_per_mtok and override_usd_per_mtok > 0:
            return override_usd_per_mtok / 1_000_000
        rate = self.usd_per_mtok.get(model, self.usd_per_mtok.get("*"))
        if rate is None:
            raise ValueError(f"no price known for {self.name}/{model}; set usd_per_mtok in the plugin settings")
        return rate / 1_000_000


# List prices checked 2026-11-17. Prices change: confirm on each provider's pricing page.
BUILTIN: dict[str, Provider] = {
    "jev": Provider(
        name="jev",
        base_url="https://api.typesafe.ai",
        default_model="jev-1.14.0",
        key_env="TYPESAFE_API_KEY",
        usd_per_mtok={"*": 0.042},
        docs="https://docs.typesafe.ai/go/models.md",
    ),
    "liquid": Provider(
        name="liquid",
        base_url="https://api.liquid.ai/decisions",
        default_model="d1.2-ultra",
        key_env="LIQUID_API_KEY",
        usd_per_mtok={"d1.2-ultra": 0.042, "d1.2": 0.02},
        docs="https://docs.liquid.ai/lfm/models/d1",
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


@dataclass(frozen=True)
class Resolved:
    """A provider with the user's settings applied: everything one request needs except the key."""
    provider: str
    base_url: str
    model: str
    key_env: str
    price_per_token: float

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
    return Resolved(name, url, mdl, p.key_env, p.price_per_token(mdl, usd_per_mtok))
