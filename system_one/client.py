"""One budget-checked call to any System One provider. Standard library only.

Works inside Hermes (the plugin tool) and outside it (a cron script that puts this folder on
``sys.path``). Nothing here imports Hermes; the plugin passes in the key and the ledger path.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from . import __version__
from .providers import Resolved, UnsupportedRequest, resolve  # noqa: F401
from .spend import BudgetExceeded, Caps, Ledger, estimate_tokens

REQUEST_ID_HEADERS = ("x-typesafe-request-id", "x-request-id", "request-id")
MAX_RESPONSE_BYTES = 8 * 1024 * 1024  # answers are small; refuse anything absurd


def _redact(text: str, secret: str) -> str:
    if secret and len(secret) >= 4:
        text = text.replace(secret, "«redacted»")
    return text


def _valid_key(key: str | None, env: str) -> str:
    key = (key or "").strip()
    if not key:
        raise SystemOneError(f"{env} is not set")
    if any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in key):
        # Never echo the key: http.client's own error would print it in full.
        raise SystemOneError(f"{env} contains whitespace or control characters; re-enter it")
    return key


def _retry_after(value: str | None, attempt: int) -> float:
    try:
        wait = float(value) if value else 0.0
    except (TypeError, ValueError):
        wait = 0.0  # HTTP-date form or junk: use backoff
    if not wait or wait < 0:
        wait = 1.5 * (attempt + 1)
    return min(wait, 10.0)


class SystemOneError(RuntimeError):
    """The provider failed or answered with something that is not a System One response."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def _question_dict(q: Any) -> dict:
    """Accept plain dicts or SDK question objects (anything with ``model_dump``)."""
    if isinstance(q, Mapping):
        return dict(q)
    dump = getattr(q, "model_dump", None)
    if callable(dump):
        return dump(exclude_none=True)
    raise TypeError(f"question must be a dict or have model_dump(), got {type(q).__name__}")


def build_body(model: str, state: Any, questions: Mapping[str, Any]) -> dict:
    if not questions:
        raise ValueError("at least one question is required")
    return {"state": state, "model": model, "questions": {k: _question_dict(v) for k, v in questions.items()}}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):  # never forward the bearer key to another origin
        return None


def _default_post(url: str, body: bytes, headers: dict, timeout: float) -> tuple[int, dict, bytes]:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, (e.read(4096) or b"")


@dataclass
class Settings:
    provider: str = "jev"
    model: str = ""
    base_url: str = ""
    usd_per_mtok: float | None = None
    caps: Caps = field(default_factory=Caps)
    timeout_s: float = 90.0
    retries: int = 2  # on 429 / 5xx / network errors only

    @classmethod
    def from_mapping(cls, s: Mapping[str, Any] | None) -> "Settings":
        """Parse the plugin's settings dict (``plugins.entries.system-one.settings``), with the same
        defaults and cap rules as the Hermes tool. The one place these rules live: scripts that
        read the user's Hermes settings call this instead of re-implementing them."""
        s = dict(s or {})

        def num(key, default):
            v = s.get(key, default)
            return default if v in (None, "") else float(v)

        def cap(key, default):
            v = num(key, default)
            return None if v < 0 else v  # -1 = no cap, 0 = block every call

        return cls(provider=str(s.get("provider") or "jev").strip().lower(),
                   model=str(s.get("model_name") or "").strip(),
                   base_url=str(s.get("base_url") or "").strip(),
                   usd_per_mtok=num("usd_per_mtok", 0) or None,
                   caps=Caps(total_usd=cap("total_cap_usd", 5.0), daily_usd=cap("daily_cap_usd", 0.5),
                             per_call_usd=cap("per_call_cap_usd", 0.05),
                             utc_offset_hours=num("cap_utc_offset_hours", 0)),
                   timeout_s=num("timeout_s", 90) or 90.0)

    def resolved(self, provider: str | None = None, model: str | None = None) -> Resolved:
        same = provider in (None, "", self.provider)
        return resolve(provider or self.provider,
                       model=(model or (self.model if same else "")),
                       base_url=(self.base_url if same else ""),
                       usd_per_mtok=(self.usd_per_mtok if same else None))


class SystemOne:
    """``SystemOne(settings, ledger_path, get_key).ask(state, questions)``.

    ``get_key(env_name)`` returns the API key for the provider (Hermes: ``get_secret``;
    a script: ``os.environ.get``).
    """

    def __init__(self, settings: Settings, ledger_path: Path | str, get_key: Callable[[str], str | None],
                 *, post: Callable[..., tuple[int, dict, bytes]] = _default_post,
                 payload_log: Path | str | None = None):
        self.settings = settings
        self.ledger = Ledger(Path(ledger_path))
        self._get_key = get_key
        self._post = post
        self._payload_log = Path(payload_log) if payload_log else None

    def estimate(self, state: Any, questions: Mapping[str, Any], *, provider: str | None = None,
                 model: str | None = None) -> dict:
        r = self.settings.resolved(provider, model)
        est = estimate_tokens(build_body(r.model, state, questions))
        return {"provider": r.provider, "model": r.model, "est_tokens": est,
                "est_usd": round(est * r.price_per_token, 8)}

    def ask(self, state: Any, questions: Mapping[str, Any], *, tag: str = "", provider: str | None = None,
            model: str | None = None, run_cap_usd: float | None = None, dry_run: bool = False) -> dict:
        """Returns ``{provider, model, answers, usage, request_id, usd}`` (answers as sent on the wire).

        Raises ``UnsupportedRequest`` (question type or limit the model can't take) and
        ``BudgetExceeded`` before sending, ``SystemOneError`` on any provider failure.
        A failed call is never turned into an answer.
        """
        r = self.settings.resolved(provider, model)
        body = build_body(r.model, state, questions)
        raw = json.dumps(body, ensure_ascii=False).encode()
        r.check(body, len(raw))  # UnsupportedRequest before any spend
        est = estimate_tokens(body)
        est_usd = est * r.price_per_token
        if dry_run:
            return {"dry_run": True, "provider": r.provider, "model": r.model, "est_tokens": est,
                    "est_usd": round(est_usd, 8)}
        self.ledger.check(est_usd, self.settings.caps, tag=tag, run_cap_usd=run_cap_usd)
        key = _valid_key(self._get_key(r.key_env), r.key_env)
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                   "Accept": "application/json", "User-Agent": f"hermes-system-one/{__version__}"}
        try:
            status, rh, content = self._send(r.url, raw, headers)
        except SystemOneError as e:
            raise SystemOneError(_redact(str(e), key), e.status) from None
        except Exception as e:  # anything else from the HTTP stack: redact, drop the traceback chain
            raise SystemOneError(_redact(f"{type(e).__name__}: {e}", key)) from None
        if len(content) > MAX_RESPONSE_BYTES:
            raise SystemOneError(f"{r.provider} response larger than {MAX_RESPONSE_BYTES} bytes")
        if 300 <= status < 400:
            raise SystemOneError(f"{r.provider} answered a redirect (HTTP {status}); redirects are not "
                                 f"followed so the key never leaves the configured host", status)
        if status != 200:
            snippet = _redact(content[:300].decode("utf-8", "replace"), key)
            raise SystemOneError(f"{r.provider} HTTP {status}: {snippet}", status)
        try:
            data = json.loads(content)
            answers = data["answers"]
            if not isinstance(answers, dict):
                raise TypeError
        except (ValueError, KeyError, TypeError):
            raise SystemOneError(f"{r.provider} returned a non-System-One body: {content[:200]!r}")
        usage = data.get("usage") or {}
        tok = int(usage.get("input_tokens") or est)
        usd = tok * r.price_per_token
        request_id = next((rh[h] for h in REQUEST_ID_HEADERS if h in rh), "") or data.get("request_id", "")
        self.ledger.record(caps=self.settings.caps, tag=tag, provider=r.provider, model=data.get("model", r.model),
                           request_id=request_id, est_tokens=est, input_tokens=tok, usd=usd)
        out = {"provider": r.provider, "model": data.get("model", r.model), "answers": answers,
               "usage": usage, "request_id": request_id, "usd": round(usd, 8)}
        if self._payload_log:
            self._payload_log.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(self._payload_log, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            with os.fdopen(fd, "a") as f:
                f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "tag": tag, **out,
                                    "state": state, "questions": body["questions"]}, ensure_ascii=False) + "\n")
        return out

    def _send(self, url: str, raw: bytes, headers: dict) -> tuple[int, dict, bytes]:
        last: Exception | None = None
        for attempt in range(self.settings.retries + 1):
            try:
                status, rh, content = self._post(url, raw, headers, self.settings.timeout_s)
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last = e
            else:
                if status != 429 and status < 500:
                    return status, rh, content
                last = SystemOneError(f"HTTP {status}", status)
                if attempt == self.settings.retries:
                    return status, rh, content
                time.sleep(_retry_after(rh.get("retry-after"), attempt))
                continue
            if attempt < self.settings.retries:
                time.sleep(1.5 * (attempt + 1))
        raise SystemOneError(f"network error: {last}")


def simplify(answers: Mapping[str, Any]) -> dict:
    """Compact view for code: Noul -> float, Choice/Score -> {choice, probabilities}, others unchanged."""
    out: dict[str, Any] = {}
    for name, a in answers.items():
        t = a.get("type") if isinstance(a, Mapping) else None
        if t == "noul":
            out[name] = round(float(a["noul"]), 3)
        elif t == "choice" and "choice" not in a:
            out[name] = a  # e.g. multi-select: keep the provider's shape unchanged
        elif t in ("choice", "score"):
            out[name] = {"choice": a.get("choice", a.get("score")),
                         "probabilities": {k: round(v, 3) for k, v in (a.get("probabilities") or {}).items()}}
        else:
            out[name] = a
    return out


__all__ = ["SystemOne", "Settings", "Caps", "BudgetExceeded", "SystemOneError", "build_body", "simplify"]
