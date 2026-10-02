# Configurable HTTP User-Agent

## Why

The fix at HEAD (e1923447) proved that a default `Python-urllib/*` User-Agent breaks real endpoints: the argos-net.com Cloudflare edge 403-blocks it, latching the whole model-download track. The remedy was a hard-coded `_DOWNLOAD_USER_AGENT` constant inside `world/art/translate_ct2.py` — but the server makes outbound HTTP calls from two more places that reach the wire with no declared identity at all: `world/art/sd_worker.py` (http.client sends no User-Agent header to sd-webui) and `world/ai/client.py` (Twisted's `Agent` sends no User-Agent header to the LLM endpoint). An operator facing a similar edge policy on any of these endpoints today must patch code. The User-Agent is deployment-tunable identity, not a secret and not an import-executing dotted path, so it belongs in the project's standard environment-override layer — one value, every outbound request.

## What Changes

- New env-overridable setting `HTTP_USER_AGENT` in `server/conf/settings.py` (free-text knob via the existing `_env_str` helper: absent or empty yields the documented code default; `secret_settings.py` keeps top precedence), joined by a `.env.example` entry, a `test_settings.py` env-pop entry, and a row in the developer settings guide.
- New shared helper module `world/http_identity.py` exposing `http_user_agent()` and `user_agent_headers()` — the single source of the `User-Agent` header value, importable by `world/art/` and `world/ai/` but deliberately not by `world/rules/` (the determinism guards forbid rules modules from growing urllib/transport-shaped imports; the helper lives outside the rules import closure).
- All three runtime outbound call sites now send the configured value:
  - `world/art/translate_ct2.py::_download_model` replaces the hard-coded `_DOWNLOAD_USER_AGENT` constant (constant deleted; the existing regression test is updated in-place, not duplicated).
  - `world/art/sd_worker.py::_http_request` merges the header into its per-request `headers` dict, so every sd-webui request carries a declared identity instead of none.
  - `world/ai/client.py::_request_headers` derives a `User-Agent` entry alongside `Authorization`/`X-Title`/`HTTP-Referer`, so an explicitly configured profile header still wins (existing overlay semantics preserved).
- Out of scope by design (documented, not patched): `world/art/cutout.py` delegates weight downloads to rembg's internals (no header seam exists without monkey-patching a third-party library), and dev/CI-only scripts (`tools/import_mono_font.py`, `web/tests/browser/fixtures.py`, `scripts/*.sh`) are not the server's outbound runtime traffic.

## Capabilities

### New Capabilities

- `outbound-http-identity`: every outbound HTTP request the server makes at runtime carries the one configured `User-Agent`, sourced from the `HTTP_USER_AGENT` setting through a single shared helper, with the per-transport header-shape adaptations named.

### Modified Capabilities

- `settings-environment-overrides`: the exact env-backed inventory grows by `HTTP_USER_AGENT` (free-text knob whose empty value means the documented default, not the "server's default" empty sentinel), and the `.env.example` inventory plus the developer guide carry the new variable.
- `llm-client`: the wire-header requirement gains `User-Agent` as a derived entry that an explicit profile header may replace, matching the existing attribution-header overlay rule.

## Impact

- Affected code: `server/conf/settings.py`, `server/conf/test_settings.py`, `.env.example`, `docs/development/settings-and-environment.md`, `world/http_identity.py` (new), `world/art/translate_ct2.py`, `world/art/sd_worker.py`, `world/ai/client.py`.
- Affected tests: `world/art/tests/test_translate.py` (UA regression test re-pinned to the setting), `world/art/tests/test_sd_worker.py` (captured `request(...)` headers assertion), `world/ai/tests/test_client.py` (captured Twisted `Headers` assertion; the exact-header-set default-wire tests gain the new derived entry), `server/conf/tests/test_env_overrides/` inventory contract tests (satisfied by the settings/env-example/guide updates, no new test module needed).
- Traceability: the new `outbound-http-identity` requirements get `@covers_requirement`-annotated tests in the three existing test modules, annotated after the delta syncs into `openspec/specs/` per the repo's new-capability idiom (the checker indexes only main specs); the amended `llm-client` and `settings-environment-overrides` requirement IDs are already canonical and annotated during implementation. No shard-registry change because no new test module is added.
- Gates: focused tests for the four suites above, `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.contract_gate`.
- No player-command surface changes, so no `docs/game/commands.md` churn.
