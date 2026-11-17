# Changelog

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
