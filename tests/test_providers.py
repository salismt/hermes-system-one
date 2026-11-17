"""Upstage, Azure (Microsoft-Decision-1) and self-hosted providers: URLs, auth headers, host rules."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from system_one import Caps, Settings, SystemOne, SystemOneError, UnsupportedRequest, choice, noul, resolve  # noqa: E402

OK = json.dumps({"model": "m", "usage": {"input_tokens": 10}, "answers": {"q": {"type": "noul", "noul": 0.9}}}).encode()


def run(tmp_path, keys, **settings):
    calls = []
    def post(url, body, headers, t):
        calls.append({"url": url, "body": json.loads(body), "headers": headers})
        return 200, {}, OK
    s = SystemOne(Settings(caps=Caps(None, None, None), **settings), tmp_path / "s.sqlite",
                  lambda env: keys.get(env), post=post)
    s.ask("x", {"q": noul("q?")})
    return calls[0]


# --- Upstage Solar Decide -------------------------------------------------------------------------
def test_upstage_default(tmp_path):
    c = run(tmp_path, {"UPSTAGE_API_KEY": "up-123456"}, provider="upstage")
    assert c["url"] == "https://api.upstage.ai/v1/systemone"
    assert c["headers"]["Authorization"] == "Bearer up-123456" and c["body"]["model"] == "solar-decide"


def test_upstage_korea_region_allowed_but_not_other_hosts():
    assert resolve("upstage", base_url="https://kr.api.upstage.ai").url == "https://kr.api.upstage.ai/v1/systemone"
    with pytest.raises(ValueError, match="not allowed"):
        resolve("upstage", base_url="https://api.upstage.ai.evil.com")


def test_upstage_flash_needs_a_price():
    with pytest.raises(ValueError, match="no price known"):
        resolve("upstage", model="solar-decide-flash")
    assert resolve("upstage", model="solar-decide-flash", usd_per_mtok=0.05).price_per_token == pytest.approx(5e-8)


def test_upstage_choice_option_limit():
    r = resolve("upstage")
    big = choice("Which?", {f"o{i}": "x" for i in range(27)})
    with pytest.raises(UnsupportedRequest, match="at most 26 choice options"):
        r.check({"questions": {"c": big}}, 100)
    r.check({"questions": {"c": choice("Which?", {f"o{i}": "x" for i in range(26)})}}, 100)


# --- Microsoft-Decision-1 on Azure AI Foundry ---------------------------------------------------
def test_azure_endpoint_auth_and_deployment(tmp_path):
    c = run(tmp_path, {"AZURE_FOUNDRY_API_KEY": "az-123456"}, provider="azure",
            base_url="https://my-res.services.ai.azure.com", model="decision-prod")
    assert c["url"] == "https://my-res.services.ai.azure.com/providers/microsoft/v1/systemone"
    assert c["headers"]["api-key"] == "az-123456" and "Authorization" not in c["headers"]
    assert c["body"]["model"] == "decision-prod"


def test_azure_accepts_pasted_full_endpoint():
    r = resolve("azure", base_url="https://r.cognitiveservices.azure.com/providers/microsoft/v1/systemone/",
                model="d")
    assert r.url == "https://r.cognitiveservices.azure.com/providers/microsoft/v1/systemone"


@pytest.mark.parametrize("url,match", [("", "needs base_url"), ("https://evil.example", "not allowed"),
                                       ("https://azure.com.evil.example", "not allowed"),
                                       ("https://r.services.ai.azure.com/api/projects/p", "bare resource endpoint")])
def test_azure_url_rules(url, match):
    with pytest.raises(ValueError, match=match):
        resolve("azure", base_url=url, model="d")


def test_azure_needs_deployment_name():
    with pytest.raises(ValueError, match="deployment name"):
        resolve("azure", base_url="https://r.services.ai.azure.com")


# --- self-hosted --------------------------------------------------------------------------------
def test_local_defaults_no_key_no_model_free(tmp_path):
    c = run(tmp_path, {}, provider="local")
    assert c["url"] == "http://127.0.0.1:8080/v1/systemone"
    assert "Authorization" not in c["headers"] and "model" not in c["body"]
    assert resolve("local").price_per_token == 0.0


def test_local_with_key_and_model(tmp_path):
    c = run(tmp_path, {"SYSTEM_ONE_LOCAL_API_KEY": "lk-123456"}, provider="local",
            base_url="http://localhost:8000", model="english")
    assert c["url"] == "http://localhost:8000/v1/systemone"
    assert c["headers"]["Authorization"] == "Bearer lk-123456" and c["body"]["model"] == "english"


@pytest.mark.parametrize("url", ["http://192.168.1.20:8080", "http://my-gpu-box:8080"])
def test_local_plain_http_only_to_loopback(url):
    with pytest.raises(ValueError, match="https"):
        resolve("local", base_url=url)
    resolve("local", base_url="https://gpu.internal.example:8443")


def test_local_is_not_capability_checked():
    resolve("local").check({"questions": {"t": {"type": "anything"}}}, 10**9)


def test_bad_local_key_still_refused_without_echo(tmp_path):
    s = SystemOne(Settings(provider="local", caps=Caps(None, None, None)), tmp_path / "s.sqlite",
                  lambda env: "bad key 1234", post=lambda *a: (_ for _ in ()).throw(AssertionError("sent")))
    with pytest.raises(SystemOneError) as e:
        s.ask("x", {"q": noul("q?")})
    assert "bad key" not in str(e.value)


# --- the built-in table stays sane --------------------------------------------------------------
def test_every_builtin_key_env_is_a_secret_field_in_the_manifest():
    from system_one import BUILTIN
    manifest = (Path(__file__).resolve().parents[1] / "plugin.yaml").read_text()
    for p in BUILTIN.values():
        assert f"env: {p.key_env}" in manifest, p.key_env


def test_manifest_provider_choices_match_registry():
    import re
    from system_one import BUILTIN
    manifest = (Path(__file__).resolve().parents[1] / "plugin.yaml").read_text()
    choices = re.search(r"provider:\n    type: str\n    choices: \[([^\]]+)\]", manifest).group(1)
    assert [c.strip() for c in choices.split(",")] == list(BUILTIN)
