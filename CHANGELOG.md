# Changelog

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
