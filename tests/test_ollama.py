"""Ollama provider: Laya and Tev1 defaults, family-based capability limits."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from system_one import Caps, Settings, SystemOne, UnsupportedRequest, choice, noul, resolve, score  # noqa: E402

OK = json.dumps({"model": "laya", "usage": {"input_tokens": 9}, "answers": {"q": {"type": "noul", "noul": 0.9}}}).encode()


def test_ollama_defaults_to_laya_on_11434_without_key(tmp_path):
    calls = []
    s = SystemOne(Settings(provider="ollama", caps=Caps(None, None, None)), tmp_path / "s.sqlite",
                  lambda env: None, post=lambda u, b, h, t: calls.append((u, json.loads(b), h)) or (200, {}, OK))
    r = s.ask("x", {"q": noul("q?")})
    url, body, headers = calls[0]
    assert url == "http://127.0.0.1:11434/v1/systemone" and body["model"] == "laya"
    assert "Authorization" not in headers and r["usd"] == 0.0


@pytest.mark.parametrize("model", ["laya", "laya:421m-english-bf16", "tev1", "tev1:0.8b", "tev1:4b"])
def test_laya_and_tev1_limits_apply_to_every_tag(model):
    r = resolve("ollama", model=model)
    with pytest.raises(UnsupportedRequest, match="at most 64 questions"):
        r.check({"questions": {f"q{i}": noul("q?") for i in range(65)}}, 100)
    with pytest.raises(UnsupportedRequest, match="type 'text'"):
        r.check({"questions": {"t": {"type": "text", "instructions": "x"}}}, 100)
    with pytest.raises(UnsupportedRequest, match="at most 26 choice options"):
        r.check({"questions": {"c": choice("Which?", {f"o{i}": "x" for i in range(27)})}}, 100)
    with pytest.raises(UnsupportedRequest, match="at most 26 score levels"):
        r.check({"questions": {"s": score("How?", [f"l{i}" for i in range(27)])}}, 100)
    with pytest.raises(UnsupportedRequest, match="65536 bytes"):
        r.check({"questions": {"q": noul("q?")}}, 70_000)
    r.check({"questions": {f"q{i}": noul("q?") for i in range(64)}}, 60_000)


def test_unknown_ollama_model_is_not_checked():
    assert resolve("ollama", model="some-future-decider").caps is None


def test_ollama_on_another_machine_needs_https():
    with pytest.raises(ValueError, match="https"):
        resolve("ollama", base_url="http://10.0.0.5:11434")
    assert resolve("ollama", base_url="http://localhost:11434/v1/systemone").url == "http://localhost:11434/v1/systemone"
