# Changelog

## 0.4.1 (2026-11-17)

- New provider `ollama`: decision models served by Ollama's own `/v1/systemone` endpoint on
  `http://127.0.0.1:11434`. Default model `laya` (Convai Innovations, 421M); also `tev1` (Together
  AI, 4B) and `tev1:0.8b`. No key, free. Laya and Tev1 limits (noul/choice/score, 64 questions,
  26 options or score levels, 64 KiB body) are checked before sending, for every tag
  (`laya:421m-english-bf16` and so on). Other Ollama models are passed through unchecked.
  Tested live with Ollama 0.40.16.
- Self-hosting guide now leads with Ollama; the laya-serve instructions are removed (Laya runs in
  Ollama without a separate server). `local` stays for llama.cpp and other servers.
- New capability limit `max_score_levels`.
- Spend-cap messages show small amounts readably (`$0.0000169`, not `$0.0000`).
- README rewritten: hero and how-it-works GIFs, provider table with test status, a measured
  same-request comparison chart (`launch/make_chart.py`), key safety as a table.

## 0.4.0 (2026-11-17)

New providers, all on the same System One contract:

- `upstage`: Upstage Solar Decide (`solar-decide` at $0.10/1M; `solar-decide-flash`, price not
  published, so set `usd_per_mtok`). Global or Korea region (`kr.api.upstage.ai`). At most 26
  options per choice, checked before sending.
- `azure`: Microsoft-Decision-1 on your Azure AI Foundry resource. Calls
  `/providers/microsoft/v1/systemone` with the `api-key` header; `model_name` is your
  deployment name. The resource host must end in `.services.ai.azure.com`,
  `.cognitiveservices.azure.com` or `.openai.azure.com`.
- `local`: your own self-hosted server (llama.cpp `llama-server`, `laya-serve`, or any
  `/v1/systemone` server). Default `http://127.0.0.1:8080`, key optional, model optional, free.
  README: step-by-step self-hosting, tested on llama.cpp 1.0.0 with Liquid d1-2B and Kev-0.8B.

Also:

- Providers now carry their own path, auth header, base-URL rule (fixed, host allowlist, or any)
  and whether a key or model is required. Keys still only go to their provider's hosts.
- A pasted full endpoint URL is trimmed to the base URL.
- Requests to a model with an empty `model` setting omit the field.

## 0.3.2 (2026-11-17)

- `requires_hermes` raised to `>=0.23`, the oldest Hermes this plugin has been tested on (0.23.1).
  No code change.

## 0.3.1 (2026-11-17)

- `Settings.from_mapping(settings_dict)`: the one parser for the plugin's settings (defaults, `-1`
  = no cap, `0` = block). The tool uses it, and scripts that read the user's Hermes settings
  should call it instead of re-implementing the rules.

## 0.3.0 (2026-11-17)

- **No SDK needed.** `system_one.noul / choice / score / box / question` build questions as plain
  dicts in the exact wire shape the TypeSafe SDK sends, so wording moves over unchanged. SDK
  objects (anything with `model_dump()`) are still accepted.
- **Model-aware checks before sending.** Each provider/model declares the question types and
  limits it accepts. A request that can't work is refused with `UnsupportedRequest` (tool kind
  `unsupported`) before any spend:
  - Jev: noul, choice, score, box.
  - Liquid d1.2 / d1.2-ultra: those plus text, number, date, spans, boxes and `choice` with
    `multiple`; at most 128 questions and a 4.5 MB body.
  - Deprecated Liquid d1, d1.1, d1-ultra: noul, choice, score.
  - `custom`: not checked.
- Answers in shapes the client doesn't model (e.g. multi-select choice) are passed through
  unchanged by `simplify()`.
- Background: typesafe-sdk 0.7.5 (latest) raises on `response.request_id` against Liquid, which
  sends no `x-typesafe-request-id` header, after the call is already billed. This client never
  needed that header.

## 0.2.0 (2026-11-17), first public release

- `system_one` tool: typed questions (noul, choice, score, and whatever else the provider
  supports) against any System One provider: `jev` (TypeSafe), `liquid` (Liquid AI d1.2 /
  d1.2-ultra) or `custom`.
- Settings: provider, model, custom endpoint and price, API keys (secret fields stored in
  `.env`), total / daily / per-call spend caps, cap timezone, payload log,
  `allow_provider_override`.
- Spend caps checked before every request; local SQLite ledger in
  `plugin-data/system-one/`.
- `/system-one` status command.
- Bundled skill `system-one:system-one`, adapted from TypeSafe's MIT `typesafe-ai` skill.
- Key safety: built-in keys go only to their own host, https only (http to exact loopback
  hostnames), no redirects, keys never echoed in errors, logs or the ledger. See the README.
- Standard library only; no dependencies.

Earlier 0.1.x builds were never released. Don't use 0.1.0: it has the key-safety issues fixed
in 0.1.1.
