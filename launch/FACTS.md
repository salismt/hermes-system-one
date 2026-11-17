# FACTS: the only text allowed on screen

Every string below is real: measured on 2026-11-17 through this plugin (system-one 0.4.1) on a
MacBook (Apple Silicon), or copied from the plugin's own output and README. Copy strings
verbatim. You may shorten with "…" only. Do not invent numbers, model names, commands or messages.

## Product copy

- Wordmark: `system-one`
- Pitch line 1: `One tool for every decision model.`
- Pitch line 2: `Switch the provider. Keep the code.`
- Sub-pitch: `Typed judgments with calibrated probabilities for Hermes Agent.`
- Install: `hermes plugins install salismt/hermes-system-one`
- Count line: `7 providers · 1 contract · spend capped before every call`
- Gate labels (mechanism piece): `system_one tool`, `model check`, `spend cap`, `provider`, `answers`
- Pass caption: `checked, sent, answered`
- Fail caption: `refused before sending · nothing billed`
- Provider names, in this order: `jev`, `liquid`, `upstage`, `azure`, `ollama`, `local`, `custom`
- Provider subtitles: `jev` = `TypeSafe`, `liquid` = `Liquid AI`, `upstage` = `Upstage Solar Decide`,
  `azure` = `Microsoft-Decision-1`, `ollama` = `Laya · Tev1`, `local` = `llama.cpp`, `custom` = `any endpoint`

## The request (the docs example, used in every run below)

- State: `Help! My payouts have been failing for 3 days.`
- Questions:
  - `department` · choice · `Which team should handle this?` · `billing` / `technical` / `sales`
  - `is_urgent` · noul · `Does this convey urgency?`
  - `frustration` · score · `How frustrated is the customer?` · `Calm` / `Frustrated` / `Very angry`

## Switch commands (real CLI)

- `hermes config set plugins.entries.system-one.settings.provider jev`
- `hermes config set plugins.entries.system-one.settings.provider liquid`
- `hermes config set plugins.entries.system-one.settings.provider ollama`
- Short form allowed on screen: `provider jev`, `provider liquid`, `provider ollama`

## Measured answers (same request, same code, only the provider setting changed)

| Provider · model | department | is_urgent | Time | Cost |
| --- | --- | --- | --- | --- |
| `jev · jev-1.14.0` | `billing 0.87` | `0.94` | `1.6 s` | `$0.0000169` |
| `liquid · d1.2-ultra` | `billing 0.91` | `0.92` | `486 ms` | `$0.00000559` |
| `liquid · d1.2` | `billing 0.91` | `0.87` | `391 ms` | `$0.00000266` |
| `ollama · laya` | `billing 0.84` | `0.74` | `68 ms` | `$0 · on your machine` |
| `ollama · tev1` (4B) | `billing 0.91` | `0.85` | `316 ms` | `$0 · on your machine` |
| `ollama · tev1:0.8b` | `technical 0.81` | `0.99` | `65 ms` | `$0 · on your machine` |
| `local · d1-2B (llama.cpp)` | `billing 0.98` | `0.69` | `365 ms` | `$0 · on your machine` |
| `local · Kev-0.8B (llama.cpp)` | `technical 0.56` | `0.59` | `398 ms` | `$0 · on your machine` |

Caption for any piece that shows these: `One request, measured once per model. Not a benchmark.`

## Real refusal messages (printed by the plugin, nothing was sent)

- Unsupported type, Laya asked for a `text` answer:
  `question 'invoice': type 'text' is not supported by ollama/laya (supported: choice, noul, score)`
- Spend cap:
  `per-call cap $0.00000001 (this call est. $0.00000449)`
- The extraction request that triggers the first one:
  state `Invoice INV-2291 was charged twice.` · question `invoice` · text · `What is the invoice number?`
