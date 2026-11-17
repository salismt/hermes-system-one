"""Regression tests for the key-safety review (skill-vetter, 2026-11-17)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from system_one import Caps, Settings, SystemOne, SystemOneError, resolve  # noqa: E402
from system_one.client import _retry_after  # noqa: E402

KEY = "liquid_SECRETKEY1234567890"
Q = {"q": {"type": "noul", "instructions": "y?"}}


def mk(tmp_path, post, key=KEY, **kw):
    return SystemOne(Settings(caps=Caps(None, None, None), retries=kw.pop("retries", 0), **kw),
                     tmp_path / "s.sqlite", lambda env: key, post=post)


@pytest.mark.parametrize("url", ["http://localhost.evil.com", "http://127.0.0.1.evil.com", "http://evil.example",
                                 "ftp://x.example", "https://user:pw@x.example", "https://x.example?k=1"])
def test_bad_custom_urls_refused(url):
    with pytest.raises(ValueError):
        resolve("custom", base_url=url, model="m", usd_per_mtok=1)


@pytest.mark.parametrize("url", ["http://localhost:8080", "http://127.0.0.1", "https://s1.example.com/api"])
def test_good_custom_urls_allowed(url):
    assert resolve("custom", base_url=url, model="m", usd_per_mtok=1).url.endswith("/v1/systemone")


@pytest.mark.parametrize("provider", ["jev", "liquid"])
def test_builtin_key_cannot_be_redirected(provider):
    with pytest.raises(ValueError, match="can't be changed for provider"):
        Settings(provider=provider, base_url="https://attacker.example").resolved()


def _no_network(*a, **k):
    raise AssertionError("must not send")


@pytest.mark.parametrize("bad", [KEY[:8] + "\n" + KEY[8:], KEY[:8] + " " + KEY[8:], KEY + "\x00"])
def test_key_with_inner_whitespace_or_control_is_rejected_without_echo(tmp_path, bad):
    with pytest.raises(SystemOneError) as e:
        mk(tmp_path, _no_network, key=bad).ask("x", Q)
    assert KEY[8:] not in str(e.value) and "whitespace" in str(e.value)


def test_surrounding_whitespace_is_stripped(tmp_path):
    seen = {}
    def post(url, body, headers, t):
        seen.update(headers)
        return 200, {}, json.dumps({"model": "m", "usage": {"input_tokens": 1}, "answers": {}}).encode()
    mk(tmp_path, post, key="  " + KEY + "  ").ask("x", Q)
    assert seen["Authorization"] == "Bearer " + KEY


def test_provider_echoing_key_is_redacted(tmp_path):
    def echo(url, body, headers, t):
        return 401, {}, json.dumps({"detail": "bad " + headers["Authorization"]}).encode()
    with pytest.raises(SystemOneError) as e:
        mk(tmp_path, echo).ask("x", Q)
    assert KEY not in str(e.value) and "redacted" in str(e.value)


def test_transport_exception_is_redacted_and_unchained(tmp_path):
    def boom(url, body, headers, t):
        raise ValueError("Invalid header value " + headers["Authorization"])
    with pytest.raises(SystemOneError) as e:
        mk(tmp_path, boom).ask("x", Q)
    assert KEY not in str(e.value)
    assert e.value.__cause__ is None and e.value.__suppress_context__


def test_redirect_is_error_not_followed(tmp_path):
    calls = []
    def redirect(url, body, headers, t):
        calls.append(url)
        return 307, {"location": "https://attacker.example/"}, b""
    with pytest.raises(SystemOneError, match="redirect"):
        mk(tmp_path, redirect).ask("x", Q)
    assert calls == ["https://api.typesafe.ai/v1/systemone"]


def test_real_opener_does_not_follow_redirects():
    import urllib.request
    from system_one.client import _NoRedirect
    req = urllib.request.Request("https://a.example/x", headers={"Authorization": "Bearer k"})
    assert _NoRedirect().redirect_request(req, None, 302, "Found", {}, "https://b.example/") is None


def test_oversized_response_refused(tmp_path):
    from system_one import client as c
    big = b"{" + b" " * (c.MAX_RESPONSE_BYTES + 10) + b"}"
    with pytest.raises(SystemOneError, match="larger"):
        mk(tmp_path, lambda *a: (200, {}, big)).ask("x", Q)


@pytest.mark.parametrize("v,expect", [("2", 2.0), ("Wed, 21 Oct 2026 07:28:00 GMT", 1.5), ("-5", 1.5),
                                      (None, 1.5), ("999", 10.0)])
def test_retry_after_parsing(v, expect):
    assert _retry_after(v, 0) == expect


def test_payload_log_is_private(tmp_path):
    ok = json.dumps({"model": "m", "usage": {"input_tokens": 1}, "answers": {}}).encode()
    s = SystemOne(Settings(caps=Caps(None, None, None)), tmp_path / "s.sqlite", lambda e: KEY,
                  post=lambda *a: (200, {}, ok), payload_log=tmp_path / "p.jsonl")
    s.ask("private text", Q)
    p = tmp_path / "p.jsonl"
    assert (p.stat().st_mode & 0o777) == 0o600
    assert KEY not in p.read_text()


def test_key_never_written_to_ledger(tmp_path):
    ok = json.dumps({"model": "m", "usage": {"input_tokens": 1}, "answers": {}}).encode()
    mk(tmp_path, lambda *a: (200, {}, ok)).ask("x", Q, tag="t")
    assert KEY.encode() not in (tmp_path / "s.sqlite").read_bytes()


def test_run_cap_tag_wildcards_are_literal(tmp_path):
    from system_one import Ledger
    led = Ledger(tmp_path / "l.sqlite")
    led.record(caps=Caps(), tag="scanA", provider="jev", model="m", request_id="r", est_tokens=1,
               input_tokens=1, usd=1.0)
    assert led.spent(tag_prefix="scan%") == 0.0 and led.spent(tag_prefix="scan_") == 0.0
    assert led.spent(tag_prefix="scan") == 1.0
