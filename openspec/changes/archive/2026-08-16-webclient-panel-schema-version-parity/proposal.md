## Why

The `character` panel's schema version diverged across the three places that define
it: `web/webclient/presentation/registry.py` registers it at version 2, while the
presenter module declares `CHARACTER_SCHEMA_VERSION = 3` and the client mirror
`PANEL_ALLOWLIST` in `web/static/webclient/js/elosern/protocol.js` expects 3. The
registry's common unavailable builder stamps the unavailable form with the
registered version (2), and the client's `validatePanel` rejects any panel whose
`schema_version` differs from the allowlist value (3) — so the moment the character
presenter cannot render (combat, creation pending, unreadable canonical data, or an
unexpected exception), the client drops the **entire** snapshot or update message,
taking every other panel and narrative metadata down with it. The bug is latent
only because the character presenter is rarely unavailable; the failure mode is
complete presentation loss.

## What Changes

- Fix the primary asymmetry: the production registry registers the `character`
  panel's schema version from `CHARACTER_SCHEMA_VERSION` (3) instead of a stale
  literal 2.
- Eliminate the whole divergence class server-side: `build_production_registry()`
  derives **every** panel's `schema_version` from its presenter module's
  `<PANEL>_SCHEMA_VERSION` constant (lazy import, matching the existing presenter
  imports). The `status` module gains the missing `STATUS_SCHEMA_VERSION = 1`
  constant and uses it in its payload — it was the only panel module without one.
- Remove the dead unavailable-form branches from all eight per-panel validators in
  `protocol.js` (`available === false` interception in `validatePanel` makes them
  unreachable); the character variant delegates to the version-1 `validateStatusPanel`
  and would reject a v3 unavailable payload if ever reached. `validatePanel` +
  `validateUnavailablePanel` become the single client-side unavailable path.
- Add a dual-direction schema-version parity contract pinning, for all eight
  panels: presenter-module constant == registry registration == JS
  `PANEL_ALLOWLIST` value == JS per-panel available-form re-check literal. The
  live-object half lives in `web/webclient/presentation/tests/test_registry.py`;
  the import-free text-extraction half is a new top-level `tests/` contract
  mirroring the existing bounds-parity contracts.
- Extend the JS protocol tests: unavailable-form coverage routes through
  `validatePanel` with the allowlist version, `PANEL_ALLOWLIST` mirror assertions
  cover all eight panels, and a regression test proves a character unavailable
  payload at version 3 is accepted while version 2 is rejected.
- Spec delta: `webclient-oob-protocol` requirements state that the unavailable
  form's `schema_version` equals the panel's registered version, and that the
  registry version derives from the panel schema's single server-side constant
  with the client allowlist kept in parity by a contract test.

No released users exist, so no migrations or backward-compatibility layers are
introduced.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `webclient-oob-protocol`: modify `every-panel-payload-has-an-exact-availability-discriminator` to require the unavailable form's `schema_version` to equal the panel's registered version (with an accept-v3/reject-v2 character scenario), and modify `presenter-registration-and-execution-are-isolated-and-read-only` to require the registered version to derive from the panel module's single constant, mirrored in the client allowlist under a parity contract.

## Impact

- `web/webclient/presentation/registry.py` — registration values become module-constant references.
- `web/webclient/presentation/status.py` — new `STATUS_SCHEMA_VERSION` constant; payload uses it.
- `web/static/webclient/js/elosern/protocol.js` — dead unavailable branches removed from all eight per-panel validators; no wire-format change.
- `web/static/webclient/js/tests/protocol.test.js` — unavailable tests rerouted through `validatePanel`; allowlist assertions completed.
- `web/webclient/presentation/tests/test_registry.py` — production-registry version assertions.
- `tests/test_panel_schema_version_parity_contract.py` — new top-level parity contract.
- `openspec/specs/webclient-oob-protocol/spec.md` — delta merged on archive.
- No player commands, wire schemas, or stored data change; `docs/game/commands.md` untouched.
