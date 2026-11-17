# system-one: decision models for Hermes Agent

A [Hermes Agent](https://github.com/NousResearch/hermes-agent) plugin that gives the agent typed
judgments with calibrated probabilities from **System One decision models**. These models answer
questions like "which team owns this ticket?" or "is this message urgent?" in one forward pass.
They generate no text and bill input tokens only.

Every provider that speaks the System One contract can be used, and you switch between them in
settings:

| Provider | Endpoint | Models | Key |
| --- | --- | --- | --- |
| `jev` (default) | `https://api.typesafe.ai` | `jev-1.14.0` | `TYPESAFE_API_KEY` |
| `liquid` | `https://api.liquid.ai/decisions` | `d1.2-ultra` (default), `d1.2` | `LIQUID_API_KEY` |
| `custom` | any `https://` endpoint you set | any | `SYSTEM_ONE_API_KEY` |

What you get:

- **`system_one` tool.** The agent sends a `state` and typed `questions` (`noul`, `choice`, `score`,
  plus whatever else the provider supports) and gets the provider's answers back unchanged.
- **Spend caps checked before every request**: total, daily and per call, recorded in a local
  SQLite ledger.
- **`/system-one` command**, which shows the active provider, model, endpoint, price, spend against
  the caps, and which keys are set.
- **Bundled skill `system-one:system-one`**: how to design state and write questions that hold up
  (judgments from the model, decisions in code).

## Install

```bash
hermes plugins install salismt/hermes-system-one
hermes plugins enable system-one
```

For local development, clone this repo into `~/.hermes/plugins/system-one` and run
`hermes plugins enable system-one`.

The tool stays hidden until the active provider's API key is set, so the agent never offers a
tool that can't run.

## Configure

All settings live under `plugins.entries.system-one.settings`. Desktop shows them as a form under
**Settings > Plugins > system-one**. From the CLI:

```bash
# provider and model
hermes config set plugins.entries.system-one.settings.provider liquid
hermes config set plugins.entries.system-one.settings.model_name d1.2      # blank = provider default

# caps (USD). -1 = no cap, 0 = block every call
hermes config set plugins.entries.system-one.settings.total_cap_usd 5
hermes config set plugins.entries.system-one.settings.daily_cap_usd 0.5
hermes config set plugins.entries.system-one.settings.per_call_cap_usd 0.05
hermes config set plugins.entries.system-one.settings.cap_utc_offset_hours 7   # which day "daily" means
```

Settings are read on every call, so a change applies to the next request with no restart.

| Setting | Default | Meaning |
| --- | --- | --- |
| `provider` | `jev` | `jev`, `liquid` or `custom` |
| `model_name` | blank | Blank uses the provider's default model |
| `base_url` | blank | Required for `custom`. Overrides a built-in endpoint. `/v1/systemone` is appended |
| `usd_per_mtok` | `0` | Price per 1M input tokens. `0` uses the built-in list price. Required for `custom` |
| `total_cap_usd` | `5.0` | All-time cap across providers |
| `daily_cap_usd` | `0.5` | Cap per calendar day |
| `per_call_cap_usd` | `0.05` | Refuses any single request estimated above this |
| `cap_utc_offset_hours` | `0` | Timezone that decides which calendar day the daily cap counts |
| `timeout_s` | `90` | Request timeout |
| `log_payloads` | `false` | Append requests and answers to `payloads.jsonl` (the state may be private) |

### API keys

Keys are secrets, so they go in `~/.hermes/.env`, never in `config.yaml`. In Desktop, enter them in
the masked fields on the plugin's settings page. From a shell, add the line to `~/.hermes/.env`:

```bash
TYPESAFE_API_KEY=...      # provider jev
LIQUID_API_KEY=liquid_... # provider liquid (console.liquid.ai > Dashboard > API Keys)
SYSTEM_ONE_API_KEY=...    # provider custom
```

The plugin reads keys through Hermes's profile-scoped secret lookup and sends them only as a
bearer token to the configured endpoint. Redirects are never followed, so a key can't leak to
another host.

## Use

Ask the agent in plain language ("classify these tickets by team with system_one"), or have it
call the tool directly:

```json
{
  "state": "Help! My payouts have been failing for 3 days.",
  "questions": {
    "department": {"type": "choice", "instructions": "Which team should handle this?",
                   "criteria": {"billing": "Payments, invoicing, refunds",
                                "technical": "Bugs, outages, integrations",
                                "sales": "Pricing, upgrades, new accounts"}},
    "is_urgent": {"type": "noul", "instructions": "Does this convey urgency?"},
    "frustration": {"type": "score", "instructions": "How frustrated is the customer?",
                    "criteria": ["Calm", "Frustrated", "Very angry"]}
  }
}
```

Result (real `jev-1.14.0` response, trimmed):

```json
{"provider": "jev", "model": "jev-1.14.0",
 "answers": {"department": {"type": "choice", "choice": "billing", "probabilities": {"billing": 0.88, "technical": 0.12, "sales": 0.0}},
             "is_urgent": {"type": "noul", "noul": 0.95},
             "frustration": {"type": "score", "score": 1.01, "probabilities": {"0": 0.0, "1": 0.98, "2": 0.02}}},
 "usage": {"input_tokens": 402}, "usd": 1.688e-05}
```

Optional arguments:

- `dry_run: true` estimates tokens and cost and sends nothing.
- `provider` and `model` override the configured ones for a single call, which is handy for
  comparing Jev and Liquid on the same request.
- `tag` labels the call in the spend ledger.

Errors come back as `{"error": ..., "kind": "budget_exceeded" | "provider_error" | "invalid_request"}`.
They are never turned into an answer.

## Use from your own scripts

`system_one/` is a standard-library-only package with no Hermes imports, so a cron script or
service can use the same providers and caps:

```python
import os, sys
sys.path.insert(0, os.path.expanduser("~/.hermes/plugins/system-one"))
from system_one import SystemOne, Settings, Caps, simplify

s1 = SystemOne(Settings(provider="liquid", caps=Caps(total_usd=5, daily_usd=0.5, per_call_usd=0.05)),
               ledger_path="spend.sqlite", get_key=os.environ.get)
r = s1.ask({"message": "Help! My payouts have been failing."},
           {"urgent": {"type": "noul", "instructions": "Does `message` convey urgency?"}}, tag="my-job")
print(simplify(r["answers"]))   # e.g. {'urgent': 0.95}
```

Questions may be plain dicts, or TypeSafe SDK objects (`Choice`, `Noul`, `Score`), since anything
with `model_dump()` works.

## The System One contract

A provider is compatible when it accepts:

```
POST {base_url}/v1/systemone
Authorization: Bearer <key>
Content-Type: application/json

{"model": "...", "state": <string | object>, "questions": {"<id>": {"type": "...", ...}}}
```

and answers `200` with `{"model": "...", "usage": {"input_tokens": N, ...}, "answers": {"<id>": {"type": "...", ...}}}`.
To add a built-in provider, add an entry to `system_one/providers.py` and to `PROVIDERS` in
`__init__.py` (a test keeps the two in sync), and add a secret field to `plugin.yaml`.

## Privacy and cost disclosure

- The `state` and `questions` you send go to the selected provider: TypeSafe (`api.typesafe.ai`),
  Liquid AI (`api.liquid.ai`) or your custom endpoint. Nothing else leaves the machine.
- Requests cost money on the provider's account. Built-in list prices were checked on 2026-11-17
  (Jev $0.042, Liquid d1.2-ultra $0.042 and d1.2 $0.02 per 1M input tokens). Confirm current
  prices with the provider. The caps use the estimate before sending and the reported
  `usage.input_tokens` after.
- The ledger (`spend.sqlite`) and the optional payload log live in
  `~/.hermes/plugin-data/system-one/`, outside the plugin folder, so they survive updates.
- The plugin never updates itself.

## Develop

```bash
python -m pytest -q                                   # unit tests, no network
hermes plugins validate . --install-deps              # same check the catalog CI runs
hermes plugins doctor . --ci
```

## License

MIT. The bundled skill is adapted from TypeSafe's `typesafe-ai` skill (MIT, (c) 2026 TypeSafe AI).
See [LICENSE](LICENSE).
