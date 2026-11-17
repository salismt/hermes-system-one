"""Hermes plugin: system-one.

Registers the ``system_one`` tool, the ``/system-one`` status command, and the bundled
``system-one:system-one`` skill. Settings are read on every call, so a change in
Settings > Plugins takes effect on the next request without a restart.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
PLUGIN = "system-one"
_HERE = Path(__file__).resolve().parent
PROVIDERS = ["jev", "liquid", "custom"]  # keep in sync with system_one.providers.BUILTIN (tested)


def _so():
    # Imported lazily so this file can be imported outside a package (pytest collection).
    from . import system_one
    return system_one


def _cap(v, default):
    if v is None or v == "":
        v = default
    v = float(v)
    return None if v < 0 else v


def _settings(ctx):
    so = _so()
    g = ctx.get_config
    return so.Settings(
        provider=str(g("provider", "jev") or "jev"),
        model=str(g("model_name", "") or ""),
        base_url=str(g("base_url", "") or ""),
        usd_per_mtok=float(g("usd_per_mtok", 0) or 0) or None,
        caps=so.Caps(total_usd=_cap(g("total_cap_usd", 5.0), 5.0),
                  daily_usd=_cap(g("daily_cap_usd", 0.5), 0.5),
                  per_call_usd=_cap(g("per_call_cap_usd", 0.05), 0.05),
                  utc_offset_hours=float(g("cap_utc_offset_hours", 0) or 0)),
        timeout_s=float(g("timeout_s", 90) or 90),
    )


def _get_secret(name: str):
    from agent.secret_scope import get_secret
    return get_secret(name)


def _client(ctx):
    from plugins.plugin_storage import plugin_data_dir
    d = plugin_data_dir(PLUGIN)
    return _so().SystemOne(_settings(ctx), d / "spend.sqlite", _get_secret,
                     payload_log=(d / "payloads.jsonl") if ctx.get_config("log_payloads", False) else None)


SCHEMA = {
    "name": "system_one",
    "description": (
        "Ask a System One decision model typed questions about a state and get calibrated probabilities back "
        "(no generated text). Use for classification, routing, yes/no gates, scoring and extraction: e.g. "
        "'which team owns this ticket?', 'is this message urgent?'. Question types: noul (probability a statement "
        "is true), choice (one option from criteria), score (ordered levels), plus text/number/date/spans/box where "
        "the provider supports them. Make judgments here; decide actions in code or reasoning. Load skill "
        "system-one:system-one before writing questions. Every call is checked against the user's spend caps."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "state": {
                "description": "What the questions are about: a string, or a JSON object with descriptive keys "
                               "that questions can reference by path in backticks (e.g. `ticket.body`).",
            },
            "questions": {
                "type": "object",
                "description": (
                    "Map of question id -> question. Examples: "
                    "{\"urgent\": {\"type\": \"noul\", \"instructions\": \"Does `message` convey urgency?\"}, "
                    "\"team\": {\"type\": \"choice\", \"instructions\": \"Which team should handle `message`?\", "
                    "\"criteria\": {\"billing\": \"Payments, refunds\", \"technical\": \"Bugs, outages\"}}, "
                    "\"anger\": {\"type\": \"score\", \"instructions\": \"How frustrated is the sender?\", "
                    "\"criteria\": [\"Calm\", \"Frustrated\", \"Very angry\"]}}"
                ),
                "additionalProperties": {"type": "object"},
            },
            "provider": {
                "type": "string", "enum": PROVIDERS,
                "description": "Optional one-off provider override, only honoured when the user enabled "
                               "allow_provider_override. Omit to use the configured provider.",
            },
            "model": {"type": "string", "description": "Optional one-off model override. Omit to use the configured one."},
            "dry_run": {"type": "boolean", "description": "Only estimate tokens and cost; send nothing."},
            "tag": {"type": "string", "description": "Optional label recorded in the spend ledger."},
        },
        "required": ["state", "questions"],
    },
}


def _safe(ctx, text: str) -> str:
    """Defense in depth: run every error through Hermes's own secret scrubber before the model sees it."""
    try:
        return ctx.redact_text(text, force=True)
    except Exception:
        return text


def _make_handler(ctx):
    def handler(args: dict, **kwargs) -> str:
        so = _so()
        try:
            want = (args.get("provider") or "").strip().lower()
            configured = str(ctx.get_config("provider", "jev") or "jev").strip().lower()
            if want and want != configured and not ctx.get_config("allow_provider_override", False):
                # The user chose which vendor receives their data; the model may not change that.
                return json.dumps({"error": f"provider override to {want!r} is off; the configured provider is "
                                            f"{configured!r} (setting allow_provider_override)",
                                   "kind": "invalid_request"})
            c = _client(ctx)
            r = c.ask(args.get("state"), args.get("questions") or {}, tag=str(args.get("tag") or "tool"),
                      provider=args.get("provider") or None, model=args.get("model") or None,
                      dry_run=bool(args.get("dry_run")))
            return json.dumps(r, ensure_ascii=False)
        except so.UnsupportedRequest as e:
            return json.dumps({"error": str(e), "kind": "unsupported"})
        except so.BudgetExceeded as e:
            return json.dumps({"error": f"budget: {e}", "kind": "budget_exceeded"})
        except so.SystemOneError as e:
            return json.dumps({"error": _safe(ctx, str(e)), "kind": "provider_error", "status": e.status})
        except Exception as e:  # never crash the agent loop
            return json.dumps({"error": _safe(ctx, f"{type(e).__name__}: {e}"), "kind": "invalid_request"})
    return handler


def _make_check(ctx):
    def check() -> bool:
        try:
            r = _settings(ctx).resolved()
            return bool(_get_secret(r.key_env))
        except Exception:
            return False
    return check


def _status(ctx) -> str:
    try:
        so = _so()
        s = _settings(ctx)
        r = s.resolved()
        c = _client(ctx)
        today = c.ledger.spent(c.ledger.today(s.caps))
        fmt = lambda v: "no cap" if v is None else f"${v:.2f}"  # noqa: E731
        keys = {p.key_env: bool(_get_secret(p.key_env)) for p in so.BUILTIN.values()}
        lines = [
            f"system-one {so.__version__}",
            f"provider: {r.provider}  model: {r.model}  endpoint: {r.url}",
            f"price: ${r.price_per_token * 1e6:.4f} per 1M input tokens",
            f"spend: today ${today:.6f} / {fmt(s.caps.daily_usd)}  total ${c.ledger.spent():.6f} / "
            f"{fmt(s.caps.total_usd)}  per call {fmt(s.caps.per_call_usd)}",
            f"by provider: {c.ledger.by_provider() or '{}'}",
            "keys: " + ", ".join(f"{k} {'set' if v else 'missing'}" for k, v in keys.items()),
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"system-one: {e}"


def register(ctx) -> None:
    ctx.register_tool(name="system_one", toolset="system_one", schema=SCHEMA, handler=_make_handler(ctx),
                      check_fn=_make_check(ctx), description="System One decision models", emoji="⚖️")
    ctx.register_command("system-one", lambda raw="", **kw: _status(ctx),
                         description="Show System One provider, model, keys and spend")
    skill = _HERE / "skills" / "system-one" / "SKILL.md"
    if skill.exists():
        ctx.register_skill("system-one", skill)
