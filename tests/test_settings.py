import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from system_one import Caps, Settings  # noqa: E402


def test_defaults():
    s = Settings.from_mapping({})
    assert (s.provider, s.model, s.timeout_s) == ("jev", "", 90.0)
    assert s.caps == Caps(5.0, 0.5, 0.05, 0.0)


def test_user_values_and_cap_rules():
    s = Settings.from_mapping({"provider": " Liquid ", "model_name": "d1.2", "total_cap_usd": -1,
                               "daily_cap_usd": 0, "per_call_cap_usd": "0.01", "cap_utc_offset_hours": 7,
                               "timeout_s": None})
    assert s.provider == "liquid" and s.model == "d1.2"
    assert s.caps == Caps(None, 0.0, 0.01, 7.0)   # -1 = no cap, 0 = block all
    assert s.timeout_s == 90.0
    assert s.resolved().url == "https://api.liquid.ai/decisions/v1/systemone"


def test_parser_covers_every_numeric_setting_in_manifest():
    manifest = (Path(__file__).resolve().parents[1] / "plugin.yaml").read_text()
    init = (Path(__file__).resolve().parents[1] / "__init__.py").read_text()
    keys = set(re.findall(r"^  ([a-z_]+):\n    type: (?:str|float|int)", manifest, re.M))
    keys -= {"cap_timezone"}
    for k in keys:
        assert f'"{k}"' in init, f"{k} declared in plugin.yaml but not passed to Settings.from_mapping"
