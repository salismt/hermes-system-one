import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from system_one import BudgetExceeded, Caps, Settings, SystemOne, SystemOneError, resolve, simplify  # noqa: E402

Q = {"urgent": {"type": "noul", "instructions": "Does `m` convey urgency?"},
     "team": {"type": "choice", "instructions": "Which team?", "criteria": {"billing": "Payments", "tech": "Bugs"}}}
OK = {"model": "d1.2-ultra", "usage": {"input_tokens": 1000, "output_tokens": 0},
      "answers": {"urgent": {"type": "noul", "noul": 0.91234},
                  "team": {"type": "choice", "choice": "billing", "confidence": 0.8,
                           "probabilities": {"billing": 0.8, "tech": 0.2}}}}


class FakePost:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, body, headers, timeout):
        self.calls.append({"url": url, "body": json.loads(body), "headers": headers})
        status, payload = self.responses.pop(0)
        return status, {"x-request-id": "req-1"}, json.dumps(payload).encode()


def client(tmp_path, post, **kw):
    caps = kw.pop("caps", Caps(total_usd=1.0, daily_usd=0.5, per_call_usd=0.05))
    s = Settings(caps=caps, retries=1, **kw)
    return SystemOne(s, tmp_path / "spend.sqlite", lambda env: "k-" + env, post=post)


def test_liquid_request_shape_and_ledger(tmp_path):
    post = FakePost((200, OK))
    r = client(tmp_path, post, provider="liquid").ask({"m": "payouts failing"}, Q, tag="t")
    call = post.calls[0]
    assert call["url"] == "https://api.liquid.ai/decisions/v1/systemone"
    assert call["headers"]["Authorization"] == "Bearer k-LIQUID_API_KEY"
    assert set(call["body"]) == {"state", "model", "questions"} and call["body"]["model"] == "d1.2-ultra"
    assert r["provider"] == "liquid" and r["request_id"] == "req-1"
    assert r["usd"] == pytest.approx(1000 * 0.042 / 1e6)
    assert simplify(r["answers"]) == {"urgent": 0.912, "team": {"choice": "billing",
                                                                "probabilities": {"billing": 0.8, "tech": 0.2}}}


def test_jev_default_and_per_call_override(tmp_path):
    post = FakePost((200, OK), (200, OK))
    c = client(tmp_path, post)
    c.ask("hi", Q)
    c.ask("hi", Q, provider="liquid", model="d1.2")
    assert post.calls[0]["url"] == "https://api.typesafe.ai/v1/systemone"
    assert post.calls[0]["body"]["model"] == "jev-1.14.0"
    assert post.calls[1]["body"]["model"] == "d1.2"
    assert c.ledger.by_provider().keys() == {"jev", "liquid"}


def test_liquid_d12_is_cheaper(tmp_path):
    assert resolve("liquid", model="d1.2").price_per_token < resolve("liquid").price_per_token


def test_custom_needs_url_model_price():
    with pytest.raises(ValueError, match="base_url"):
        resolve("custom")
    with pytest.raises(ValueError, match="price"):
        resolve("custom", base_url="https://x.example", model="m")
    r = resolve("custom", base_url="https://x.example/", model="m", usd_per_mtok=0.1)
    assert r.url == "https://x.example/v1/systemone" and r.key_env == "SYSTEM_ONE_API_KEY"


def test_rejects_plain_http():
    with pytest.raises(ValueError, match="https"):
        resolve("custom", base_url="http://evil.example", model="m", usd_per_mtok=1)


def test_caps_block_before_sending(tmp_path):
    post = FakePost()
    c = client(tmp_path, post, caps=Caps(total_usd=1.0, daily_usd=0.0, per_call_usd=None))
    with pytest.raises(BudgetExceeded, match="daily cap"):
        c.ask("hi", Q)
    c = client(tmp_path, post, caps=Caps(total_usd=None, daily_usd=None, per_call_usd=1e-9))
    with pytest.raises(BudgetExceeded, match="per-call"):
        c.ask("hi", Q)
    assert post.calls == []


def test_total_cap_counts_previous_spend(tmp_path):
    post = FakePost((200, {**OK, "usage": {"input_tokens": 10_000_000}}))
    c = client(tmp_path, post, caps=Caps(total_usd=0.45, daily_usd=None, per_call_usd=None))
    c.ask("hi", Q)  # records $0.42
    with pytest.raises(BudgetExceeded, match="total cap"):
        c.ask("x" * 300_000 * 10, Q)


def test_run_cap(tmp_path):
    post = FakePost((200, {**OK, "usage": {"input_tokens": 1_000_000}}))
    c = client(tmp_path, post, caps=Caps(None, None, None))
    c.ask("hi", Q, tag="scan-1")
    with pytest.raises(BudgetExceeded, match="run cap"):
        c.ask("hi", Q, tag="scan-1", run_cap_usd=0.042)


def test_dry_run_sends_nothing(tmp_path):
    post = FakePost()
    r = client(tmp_path, post).ask("hi", Q, dry_run=True)
    assert r["dry_run"] and post.calls == []


def test_http_error_is_error_not_answer(tmp_path):
    post = FakePost((422, {"detail": "bad question"}))
    with pytest.raises(SystemOneError, match="422"):
        client(tmp_path, post).ask("hi", Q)


def test_retries_5xx_then_succeeds(tmp_path, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    post = FakePost((503, {}), (200, OK))
    assert client(tmp_path, post).ask("hi", Q)["answers"]
    assert len(post.calls) == 2


def test_missing_key(tmp_path):
    s = Settings(caps=Caps(None, None, None))
    c = SystemOne(s, tmp_path / "s.sqlite", lambda env: None, post=FakePost())
    with pytest.raises(SystemOneError, match="TYPESAFE_API_KEY"):
        c.ask("hi", Q)


def test_non_system_one_body(tmp_path):
    with pytest.raises(SystemOneError, match="non-System-One"):
        client(tmp_path, FakePost((200, {"choices": []}))).ask("hi", Q)


def test_accepts_sdk_style_objects(tmp_path):
    class Obj:
        def model_dump(self, exclude_none=False):
            return {"type": "noul", "instructions": "x?"}
    post = FakePost((200, OK))
    client(tmp_path, post).ask("hi", {"q": Obj()})
    assert post.calls[0]["body"]["questions"] == {"q": {"type": "noul", "instructions": "x?"}}


def test_plugin_provider_enum_matches_registry():
    import importlib.util
    spec = importlib.util.spec_from_file_location("so_plugin", Path(__file__).resolve().parents[1] / "__init__.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    from system_one import BUILTIN
    assert m.PROVIDERS == list(BUILTIN)


def test_settings_keys_avoid_hermes_reserved_roots():
    # Hermes rejects plugin settings whose first segment is model/plugins/security/settings.
    import re
    keys = re.findall(r"^  ([a-z_]+):", (Path(__file__).resolve().parents[1] / "plugin.yaml").read_text(), re.M)
    assert keys and not {"model", "plugins", "security", "settings"} & set(keys)
