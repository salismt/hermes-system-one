import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from system_one import (Caps, Settings, SystemOne, UnsupportedRequest, box, choice, noul,  # noqa: E402
                        question, resolve, score, simplify)

OK = json.dumps({"model": "m", "usage": {"input_tokens": 10}, "answers": {}}).encode()


def mk(tmp_path, provider="jev", model=""):
    calls = []
    def post(url, body, headers, t):
        calls.append(json.loads(body))
        return 200, {}, OK
    s = SystemOne(Settings(provider=provider, model=model, caps=Caps(None, None, None)),
                  tmp_path / "s.sqlite", lambda e: "key-1234", post=post)
    return s, calls


def test_builders_match_sdk_wire_shape():
    assert noul("Is it?") == {"type": "noul", "instructions": "Is it?"}
    assert noul("Is it?", {"true": "a", "false": "b"}) == {"type": "noul", "instructions": "Is it?",
                                                          "criteria": {"true": "a", "false": "b"}}
    assert choice("Which?", {"x": "X"}) == {"type": "choice", "instructions": "Which?", "criteria": {"x": "X"}}
    assert choice("Which?", {"x": "X"}, multiple=True)["multiple"] is True
    assert score("How?", ["lo", "hi"]) == {"type": "score", "instructions": "How?", "criteria": ["lo", "hi"]}
    assert box("Where is the mug?") == {"type": "box", "instructions": "Where is the mug?"}
    assert question("text", "Invoice number?") == {"type": "text", "instructions": "Invoice number?"}
    assert list(noul("q", {"true": "a"})) == ["type", "instructions", "criteria"]  # SDK key order


@pytest.mark.parametrize("bad", [lambda: noul(""), lambda: noul("q", {"yes": "a"}), lambda: choice("q", {}),
                                 lambda: score("q", ["only one"])])
def test_builders_reject_malformed(bad):
    with pytest.raises(ValueError):
        bad()


def test_sdk_objects_produce_same_body_if_sdk_installed():
    sdk = pytest.importorskip("typesafe_sdk")
    pairs = [(sdk.Noul(instructions="q", criteria={"true": "a", "false": "b"}), noul("q", {"true": "a", "false": "b"})),
             (sdk.Choice(instructions="q", criteria={"x": "X", "y": "Y"}), choice("q", {"x": "X", "y": "Y"})),
             (sdk.Score(instructions="q", criteria=["a", "b", "c"]), score("q", ["a", "b", "c"]))]
    for obj, d in pairs:
        assert obj.model_dump(exclude_none=True) == d


def test_jev_refuses_liquid_only_type_before_sending(tmp_path):
    s, calls = mk(tmp_path, "jev")
    with pytest.raises(UnsupportedRequest, match="'text' is not supported by jev"):
        s.ask("x", {"inv": question("text", "Invoice number?")})
    with pytest.raises(UnsupportedRequest, match="multiple"):
        s.ask("x", {"tags": choice("Tags?", {"a": "A", "b": "B"}, multiple=True)})
    assert calls == [] and s.ledger.spent() == 0


def test_liquid_d12_accepts_extended_types(tmp_path):
    s, calls = mk(tmp_path, "liquid")
    s.ask("x", {"inv": question("text", "Invoice number?"),
                "tags": choice("Tags?", {"a": "A", "b": "B"}, multiple=True), "n": noul("q")})
    assert calls and calls[0]["questions"]["tags"]["multiple"] is True


def test_liquid_deprecated_model_has_only_core_types(tmp_path):
    with pytest.raises(UnsupportedRequest, match="d1.1"):
        resolve("liquid", model="d1.1", usd_per_mtok=0.02).check({"questions": {"t": {"type": "text"}}}, 10)


def test_liquid_limits(tmp_path):
    s, calls = mk(tmp_path, "liquid")
    with pytest.raises(UnsupportedRequest, match="at most 128 questions"):
        s.ask("x", {f"q{i}": noul("q") for i in range(129)})
    with pytest.raises(UnsupportedRequest, match="bytes"):
        s.ask("x" * 4_600_000, {"q": noul("q")})
    assert calls == []


def test_dry_run_also_validates(tmp_path):
    s, _ = mk(tmp_path, "jev")
    with pytest.raises(UnsupportedRequest):
        s.ask("x", {"t": question("spans", "PII?")}, dry_run=True)


def test_custom_is_not_checked():
    r = resolve("custom", base_url="https://x.example", model="m", usd_per_mtok=1)
    r.check({"questions": {"t": {"type": "anything"}}}, 10**9)


def test_simplify_keeps_unknown_choice_shape():
    raw = {"type": "choice", "choices": {"a": 0.9, "b": 0.6}}
    assert simplify({"tags": raw}) == {"tags": raw}
