"""Provider registry for System One decision-model APIs.

Every provider here speaks the same contract: ``POST {base_url}/v1/systemone`` with a JSON body
``{"model", "state", "questions"}`` and a bearer key, answering ``{"model", "usage", "answers"}``.
Switching providers is a config change, never a code change.
"""
from __future__ import annotations

from dataclasses import dataclass, field

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
    url = (base_url or p.base_url).strip()
    mdl = (model or p.default_model).strip()
    if not url:
        raise ValueError(f"provider {name!r} needs base_url in the plugin settings")
    if not url.startswith("https://") and not url.startswith(("http://localhost", "http://127.0.0.1")):
        raise ValueError(f"base_url must be https:// (got {url!r})")
    if not mdl:
        raise ValueError(f"provider {name!r} needs model in the plugin settings")
    return Resolved(name, url, mdl, p.key_env, p.price_per_token(mdl, usd_per_mtok))
