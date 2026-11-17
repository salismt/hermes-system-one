# system-one: decision models for Hermes Agent

A [Hermes Agent](https://github.com/NousResearch/hermes-agent) plugin that gives the agent typed
judgments with calibrated probabilities from **System One decision models**. These models answer
questions like "which team owns this ticket?" or "is this message urgent?" in one forward pass.
They generate no text and bill input tokens only.

Every provider that speaks the System One contract can be used, and you switch between them in
settings:

| Provider | Who | Endpoint | Models | Price / 1M input | Key |
| --- | --- | --- | --- | --- | --- |
| `jev` (default) | TypeSafe | `https://api.typesafe.ai` | `jev-1.14.0` | $0.042 | `TYPESAFE_API_KEY` |
| `liquid` | Liquid AI | `https://api.liquid.ai/decisions` | `d1.2-ultra` (default), `d1.2` | $0.042 / $0.02 | `LIQUID_API_KEY` |
| `upstage` | Upstage | `https://api.upstage.ai` (Korea: `kr.api.upstage.ai`) | `solar-decide` (default), `solar-decide-flash` | $0.10 / set your own | `UPSTAGE_API_KEY` |
| `azure` | Microsoft-Decision-1 | your Azure AI Foundry resource | your deployment name | $0.042 | `AZURE_FOUNDRY_API_KEY` |
| `local` | **self-hosted**: llama.cpp, laya-serve, … | `http://127.0.0.1:8080` (yours) | whatever your server runs | free | optional |
| `custom` | any other hosted endpoint | any `https://` URL you set | any | you set it | `SYSTEM_ONE_API_KEY` |

Prices were checked on 2026-11-17 from each provider's own pages. Upstage doesn't publish a
price for `solar-decide-flash`, so set `usd_per_mtok` yourself if you use it.

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
| `provider` | `jev` | `jev`, `liquid`, `upstage`, `azure`, `local` or `custom` |
| `model_name` | blank | Blank uses the provider's default. Required for `azure` (your deployment name) and `custom` |
| `base_url` | blank | `azure`: your Foundry resource endpoint. `local`: your server. `upstage`: optional Korea region. `custom`: required. Can't be changed for `jev` or `liquid` |
| `usd_per_mtok` | `0` | Price per 1M input tokens. `0` uses the built-in list price (`local` is free). Required for `custom` |
| `total_cap_usd` | `5.0` | All-time cap across providers |
| `daily_cap_usd` | `0.5` | Cap per calendar day |
| `per_call_cap_usd` | `0.05` | Refuses any single request estimated above this |
| `cap_utc_offset_hours` | `0` | Timezone that decides which calendar day the daily cap counts |
| `allow_provider_override` | `false` | Let the agent send a single call to another provider whose key is set |
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

See [Key safety](#key-safety) for exactly where a key can and cannot go.

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
- `model` overrides the configured model for a single call.
- `provider` sends a single call to another provider, which is handy for comparing Jev and Liquid
  on the same request. It is refused unless you turn on `allow_provider_override`, because you
  decide which vendor receives your data.
- `tag` labels the call in the spend ledger.

Errors come back as `{"error": ..., "kind": "unsupported" | "budget_exceeded" | "provider_error" | "invalid_request"}`.
They are never turned into an answer.

## Use from your own scripts

`system_one/` is a standard-library-only package with no Hermes imports, so a cron script or
service can use the same providers and caps:

```python
import os, sys
sys.path.insert(0, os.path.expanduser("~/.hermes/plugins/system-one"))
from system_one import SystemOne, Settings, Caps, noul, simplify

s1 = SystemOne(Settings(provider="liquid", caps=Caps(total_usd=5, daily_usd=0.5, per_call_usd=0.05)),
               ledger_path="spend.sqlite", get_key=os.environ.get)
r = s1.ask({"message": "Help! My payouts have been failing."},
           {"urgent": noul("Does `message` convey urgency?")}, tag="my-job")
print(simplify(r["answers"]))   # e.g. {'urgent': 0.95}
```

Build questions with the plugin's helpers. They produce plain dicts in the exact shape the TypeSafe
SDK sends, so no SDK is needed:

```python
from system_one import noul, choice, score, box, question

qs = {
    "urgent": noul("Does `message` convey urgency?",
                   {"true": "The sender needs action today.", "false": "Nothing is time-bound."}),
    "team":   choice("Which team should handle `message`?", {"billing": "Payments", "technical": "Bugs"}),
    "tags":   choice("Which topics apply?", {"refund": "...", "outage": "..."}, multiple=True),  # Liquid d1.2+
    "anger":  score("How frustrated is the sender?", ["Calm", "Frustrated", "Very angry"]),
    "invoice": question("text", "What is the invoice number in `message`?"),                 # Liquid d1.2+
}
```

TypeSafe SDK objects (`Choice`, `Noul`, `Score`) still work, since anything with `model_dump()` is
accepted. Don't use the SDK's own client against Liquid: as of typesafe-sdk 0.7.5 it raises on the
missing `x-typesafe-request-id` header after the call has been billed.

### What each model accepts

The client checks every request against the chosen model before sending, so a request that can't
work fails with `UnsupportedRequest` (tool result kind `unsupported`) and costs nothing.

| Provider / model | Question types | Limits |
| --- | --- | --- |
| `jev` | noul, choice, score, box | |
| `liquid` `d1.2`, `d1.2-ultra` | noul, choice (+`multiple`), score, text, number, date, spans, box, boxes | 128 questions, 4.5 MB body |
| `liquid` `d1`, `d1.1`, `d1-ultra` (deprecated) | noul, choice, score | 128 questions, 4.5 MB body |
| `upstage` | noul, choice, score | at most 26 options per choice |
| `azure` | noul, choice, score | text only, 32,768 tokens (enforced by Azure) |
| `local`, `custom` | not checked: depends on your server and model | not checked |

`simplify()` passes through any answer shape it doesn't model (multi-select choice, text, spans
and so on) unchanged.

## Self-hosted models

Run a decision model on your own machine and point the plugin at it with provider `local`.
Nothing leaves your network and nothing is billed. Any server that implements
`POST /v1/systemone` works. Two common ones:

### Option A: llama.cpp (any GGUF decision model)

llama.cpp's `llama-server` has served `/v1/systemone` since v0.6.0 (October 2026). Check with
`llama-server --version`; Homebrew may still have an older build (`brew upgrade llama.cpp`).

```bash
# a small, fast model from the llama.cpp team (812 MB)
llama-server -hf ggml-org/Kev-0.8B-GGUF:Q8_0 --port 8080

# or Liquid's open-weight d1 (1.1 GB at Q4_K_M; text, images and video)
llama-server -hf LiquidAI/d1-2B-GGUF:Q4_K_M --port 8080

# already downloaded the .gguf? point at the file instead
llama-server -m ./d1-2B-Q4_K_M.gguf --port 8080
```

With the `llama` CLI from llama.app, `llama serve -hf <repo>` does the same.

Then in Hermes:

```bash
hermes config set plugins.entries.system-one.settings.provider local
# default base_url is http://127.0.0.1:8080; set it only if your server runs elsewhere
```

Decision models with published GGUFs include `ggml-org/Kev-4B-GGUF`, `ggml-org/Kev-0.8B-GGUF`,
`ggml-org/Julia-1-GGUF` (144M, 50+ languages), `ggml-org/Laya-GGUF`, `ggml-org/Clef-GGUF`,
`LiquidAI/d1-2B-GGUF`, `LiquidAI/d1-Omni-2B-GGUF` and `LiquidAI/d1-omni-600M-GGUF`. llama.cpp
answers `noul`, `choice` and `score` (score takes 2 to 10 levels). Liquid's extraction types
(text, number, spans, boxes) need the Liquid API, Transformers or mlx-vlm, not llama.cpp.

To serve several models from one server, run `llama serve` with no model (router mode: models
load on demand) and set `model_name` to the one you want, e.g. `ggml-org/Kev-4B-GGUF:Q8_0`.
With one model loaded, `model_name` is ignored.

Tested with this plugin on llama.cpp 1.0.0 (macOS, Apple Silicon) on the docs example "My
payouts have been failing for 3 days":

| Model | department | urgent | Time | Cost |
| --- | --- | --- | --- | --- |
| `LiquidAI/d1-2B-GGUF` Q4_K_M | billing 0.98 | 0.69 | 365 ms | $0 |
| `ggml-org/Kev-0.8B-GGUF` Q8_0 | technical 0.56 (billing 0.42) | 0.59 | 398 ms | $0 |
| hosted `jev-1.14.0`, for comparison | billing 0.88 | 0.95 | | $0.000017 |

A type the server doesn't support (e.g. `text` on llama.cpp) comes back as a provider error
(HTTP 400 naming the supported types), never as an answer.

### Option B: laya-serve (Laya, Apache 2.0)

```bash
pip install "laya[serve]"
LAYA_PRELOAD=1 laya-serve          # http://0.0.0.0:8000
```

```bash
hermes config set plugins.entries.system-one.settings.provider local
hermes config set plugins.entries.system-one.settings.base_url http://127.0.0.1:8000
```

`model_name` can be `english`, `multilingual` or `typed-decisions`, or blank to let Laya pick.
If you set `LAYA_API_KEY` on the server, enter the same value as **Self-hosted server key** in
the plugin settings (`SYSTEM_ONE_LOCAL_API_KEY`). Laya's `confidence` is computed differently
from Jev's, so re-check any confidence threshold you carry over.

### Running the server on another machine

Plain `http://` is accepted only for `localhost`, `127.0.0.1` and `::1`, so your questions never
cross a network unencrypted. For a GPU box elsewhere, either:

- put it behind HTTPS (e.g. Caddy or nginx with a certificate) and set
  `base_url: https://gpu.example.internal`; or
- tunnel it to your machine with `ssh -N -L 8080:127.0.0.1:8080 gpu-box` and keep the default
  `base_url`.

### Before you rely on a local model

Open models vary a lot in accuracy. Several independent comparisons put most of them well
behind the hosted models on zero-shot decisions. Run your own labelled examples through both
before switching a production workflow. The plugin's `provider` argument (with
`allow_provider_override` on) makes that comparison a one-line change.

## Azure: Microsoft-Decision-1

1. In Azure AI Foundry, deploy **Microsoft-Decision-1** from the model catalog.
2. From the deployment's details page, copy the **resource endpoint**, the **deployment name** and
   the **API key**.
3. Configure the plugin:

```bash
hermes config set plugins.entries.system-one.settings.provider azure
hermes config set plugins.entries.system-one.settings.base_url https://<resource>.services.ai.azure.com
hermes config set plugins.entries.system-one.settings.model_name <deployment-name>
```

Enter the key as **Azure AI Foundry API key** in the plugin settings (`AZURE_FOUNDRY_API_KEY`).
The plugin calls `<resource>/providers/microsoft/v1/systemone` with the `api-key` header. Use the
bare resource endpoint: no project path, no `/openai`. If you paste the full endpoint, the
`/providers/microsoft/v1/systemone` suffix is removed for you. The host must end in
`.services.ai.azure.com`, `.cognitiveservices.azure.com` or `.openai.azure.com`, so a typo can't
send your key elsewhere. Microsoft Entra ID tokens aren't supported yet; use the API key.

## The System One contract

A provider is compatible when it accepts:

```
POST {base_url}/v1/systemone
Authorization: Bearer <key>
Content-Type: application/json

{"model": "...", "state": <string | object>, "questions": {"<id>": {"type": "...", ...}}}
```

(the path is `/providers/microsoft/v1/systemone` on Azure), and answers `200` with `{"model": "...", "usage": {"input_tokens": N, ...}, "answers": {"<id>": {"type": "...", ...}}}`.
To add a built-in provider, add an entry to `system_one/providers.py` and to `PROVIDERS` in
`__init__.py` (a test keeps the two in sync), and add a secret field to `plugin.yaml`.

## Key safety

What happens to an API key you enter:

- **Storage.** Keys are `secret` settings. Hermes stores them in `~/.hermes/.env` (per profile),
  never in `config.yaml`. The plugin reads them only through Hermes's profile-scoped
  `get_secret()` and never opens `.env` or any other credential file itself.
- **Where a key goes.** A key is sent only in its provider's auth header (`Authorization: Bearer`,
  or `api-key` for Azure), and only to that provider's hosts:
  - `TYPESAFE_API_KEY` to `api.typesafe.ai` and `LIQUID_API_KEY` to `api.liquid.ai`. `base_url`
    can't be changed for these.
  - `UPSTAGE_API_KEY` to `api.upstage.ai` or `kr.api.upstage.ai`.
  - `AZURE_FOUNDRY_API_KEY` to hosts ending in `.services.ai.azure.com`,
    `.cognitiveservices.azure.com` or `.openai.azure.com`.
  - Only the dedicated `SYSTEM_ONE_LOCAL_API_KEY` and `SYSTEM_ONE_API_KEY` follow a `base_url`
    you choose.
- **Transport.** `https://` only. Plain `http://` is allowed only to `localhost`, `127.0.0.1` or
  `::1`, matched by exact hostname, so `localhost.evil.com` is refused. URLs carrying credentials,
  a query or a fragment are refused. Redirects are never followed: a `3xx` is an error, so a key
  can't be bounced to another host. TLS certificates are verified by Python's default context.
- **Never echoed.** Keys with inner whitespace or control characters are rejected before any
  request, with a message that doesn't contain the key (Python's HTTP stack would otherwise print
  the whole header). Any provider error body or transport error that contains the key is
  redacted, the exception chain is dropped, and the text goes through Hermes's secret scrubber
  before the model sees it.
- **Never stored.** The spend ledger and the optional payload log hold no headers and no keys. The
  payload log is created with mode `0600`.
- **`/system-one`** shows only whether each key is set.
- **No dependencies, no self-update, no shell, no `eval`.** The client uses only the Python
  standard library. Tests block all network access.

Known limits:

- The agent runs with your permissions. An agent that can run shell commands can read
  `~/.hermes/.env` without this plugin. The plugin's guarantee is narrower: it doesn't add a new
  path for a key to leave your machine.
- The caps use an estimate before sending. Two calls running at the same moment can both pass the
  check, so the real spend can go slightly over a cap. Set provider-side limits too where the
  provider offers them.

## Privacy and cost disclosure

- The `state` and `questions` you send go to the selected provider: TypeSafe (`api.typesafe.ai`),
  Liquid AI (`api.liquid.ai`), Upstage (`api.upstage.ai`), your Azure Foundry resource, your own
  self-hosted server, or your custom endpoint. Nothing else leaves the machine. With `local` on
  `localhost`, nothing leaves the machine at all.
- Requests cost money on the provider's account. Built-in list prices were checked on 2026-11-17
  (Jev $0.042, Liquid d1.2-ultra $0.042 and d1.2 $0.02 per 1M input tokens). Confirm current
  prices with the provider. The caps use the estimate before sending and the reported
  `usage.input_tokens` after.
- The ledger (`spend.sqlite`) and the optional payload log live in
  `~/.hermes/plugin-data/system-one/`, outside the plugin folder, so they survive updates.
- The plugin never updates itself. Updates arrive only through `hermes plugins update`.

## Develop

```bash
python -m pytest -q                                   # unit tests, no network
hermes plugins validate . --install-deps              # same check the catalog CI runs
hermes plugins doctor . --ci
```

## License

MIT. The bundled skill is adapted from TypeSafe's `typesafe-ai` skill (MIT, (c) 2026 TypeSafe AI).
See [LICENSE](LICENSE).
