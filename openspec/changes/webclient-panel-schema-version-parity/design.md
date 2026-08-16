## Context

The OOB presentation system defines each panel's schema version in three places:

1. `web/webclient/presentation/registry.py` — `PresenterSpec.schema_version`,
   which the registry's common unavailable builder
   (`PresentationRegistry.build_unavailable`) stamps onto the unavailable form.
2. Each presenter module's `<PANEL>_SCHEMA_VERSION` constant, stamped onto the
   available form.
3. `web/static/webclient/js/elosern/protocol.js` — `PANEL_ALLOWLIST`, the client
   mirror used by `validatePanel` to gate every panel before dispatch.

An audit found the `character` panel asymmetric: registry=2, module=3, allowlist=3.
Independent verification of the codebase confirms the full picture:

- **Only `character` is asymmetric in value.** All other panels agree
  (art/status/local_map/services/creation/exploration=1, context_actions=3).
- **`status.py` is the only panel module without a version constant** — its
  payload hardcodes `"schema_version": 1` (status.py:53), so it cannot be pinned
  by any parity test.
- **All eight JS per-panel validators carry a dead `available === false` branch**
  (protocol.js lines 550, 842, 1107, 1592, 2166, 2499, 2746, 2959).
  `validatePanel` (protocol.js:3040) checks `payload.schema_version` against the
  allowlist and returns `validateUnavailablePanel` before dispatch (3050-3051), so
  the per-panel unavailable branches are unreachable. The character branch is
  doubly wrong: it delegates to `validateStatusPanel`, which pins version 1.
- **Consequence**: a character unavailable payload ships at version 2; the client
  rejects the whole `ui_snapshot`/`ui_update` envelope (`validateCommonMetadata`
  is all-or-nothing per message), dropping every panel and narrative metadata.
- **No test pins schema versions across the three locations.** Existing top-level
  parity contracts (`tests/test_exploration_parity_contract.py`,
  `tests/test_services_parity_contract.py`, `tests/test_creation_parity_contract.py`)
  pin only `MAX_*` bounds.

Architectural source of truth: `docs/superpowers/specs/2026-08-02-webclient-oob-foundation-design.md`
states panels' values "contain their own schema version" and that a presenter
failure emits the registry-owned unavailable payload while other panels continue —
the fix realigns implementation with that contract. `AGENTS.md`: no released
users, so no migrations or backward-compatibility layers.

## Goals / Non-Goals

**Goals:**
- Make the wire schema version for every panel one number everywhere:
  available form, unavailable form, registry, client allowlist.
- Remove the divergence *class* server-side, not just the `character` literal.
- Give the `status` panel a declared version constant so all eight panels can be
  uniformly pinned.
- Collapse the client's unavailable path into the single, already-correct
  `validatePanel` → `validateUnavailablePanel` route.
- Guard all three locations with deterministic tests in both directions.

**Non-Goals:**
- No wire-format or protocol-version change; no new panel; no schema bumps.
- No behavioral change to available-form validation (per-panel version re-checks
  and bounds stay).
- No change to the registry's duplicate-rejection, isolation, or correlation-ID
  behavior.
- No documentation of player commands; no docs/ content changes.

## Decisions

### D1: The registry derives every schema version from its panel module constant

`build_production_registry()` registers `schema_version=<PANEL>_SCHEMA_VERSION`
for all eight panels. The constants are imported lazily inside
`build_production_registry()` alongside the already-lazy presenter imports,
because the presenter modules import `PanelUnavailableError` from this module —
module-level constant imports would create a circular import. This makes the
server-side divergence class impossible: the available form (module constant) and
the unavailable form (registry spec) cannot disagree.

*Alternative rejected*: correcting only the `character` literal to 3. Minimal
diff, but the bug occurred precisely because a literal can drift; it leaves the
class alive for the next schema bump.

### D2: `status.py` gains `STATUS_SCHEMA_VERSION = 1` and uses it

`status.py` is the only panel module without a version constant; its payload
hardcodes the version (status.py:53). Add the constant and reference it in the
payload dict. This makes every panel module uniformly declarative and lets the
parity contract enumerate eight panels with the same extraction rule.

### D3: Remove the dead unavailable branches from all eight JS per-panel validators

`validatePanel` + `validateUnavailablePanel` (which validates against the
allowlist version) already own the unavailable path. Remove the unreachable
`available === false` blocks from `validateStatusPanel`, `validateContextActionsPanel`,
`validateLocalMapPanel`, `validateServicesPanel`, `validateCreationPanel`,
`validateExplorationPanel`, `validateCharacterPanel`, and `validateArtPanel`. The
per-panel available-branch `schema_version` re-check is **kept**: it is reachable,
cheap, fail-closed defense in depth, and mirrors the Python validators which also
re-check the version against their module constant.

*Alternative rejected*: fixing only the character branch (or re-pointing it at the
allowlist version). All eight branches are dead by the same interception; leaving
seven latent copies of misleading "unavailable handling" in the file perpetuates
exactly the confusion that produced this bug.

### D4: Dual-direction parity contract for schema versions

Two halves, matching the repo's established contract pattern:

- **Live-object half** (`web/webclient/presentation/tests/test_registry.py`,
  plain `unittest.TestCase`): assert for all eight panels that
  `build_production_registry().spec(name).schema_version` equals the imported
  module constant. This catches a registration that stops referencing the
  constant or a constant renamed out of sync.
- **Text-extraction half** (new `tests/test_panel_schema_version_parity_contract.py`):
  top-level tests run under plain `unittest discover` without Evennia settings, so
  imports are disallowed — the existing bounds contracts use source-text regex
  extraction for the same reason. Extract, for each panel: the registry's
  `schema_version=<CONST>` reference, the module's `<CONST> = N` value, and the
  JS allowlist's `name: N` value; assert all three equal. The registry side
  requires the reference form (`schema_version=<CONST>`), so an inline literal
  fails the contract. Annotate with `covers_requirement` for the modified
  `webclient-oob-protocol` requirements.

*Alternative rejected*: a shared machine-readable JSON consumed by both Python
and JS. Overkill for eight integers, and protocol.js is deliberately standalone
vanilla JS with no build step.

### D5: JS tests reroute unavailable coverage through `validatePanel`

`protocol.test.js` currently exercises the dead branches directly
(e.g. `validateStatusPanel(unavailableStatusPanel())`,
`validateServicesPanel(unavailable)`). Update those cases to pass unavailable
payloads through `validatePanel(name, allowlistVersion, payload)` (or
`validateCommonMetadata`), and complete the `PANEL_ALLOWLIST` mirror assertions —
today only six of eight panels are pinned (status and local_map are missing).
Add a regression case proving a character unavailable payload at version 3 is
accepted and one at version 2 is rejected.

## Risks / Trade-offs

- [Text-extraction contract can rot if source formatting changes] → Anchored
  patterns (`^CONST = N`, `var PANEL_ALLOWLIST = {...}`, `schema_version=CONST`)
  matching the existing three parity contracts; a formatting change fails the
  contract loudly, which is the intended signal.
- [Circular import if constants move to module level in registry.py] → All
  imports of presenter modules stay lazy inside `build_production_registry()`,
  preserving the existing pattern that keeps registry.py importable in isolation.
- [JS test update misses a call site that relied on the dead branch] → Removing a
  dead branch changes `validate<Panel>` to throw on unavailable payloads; every
  affected call site in `protocol.test.js` fails deterministically until rerouted.
- [Per-panel validators called directly with unavailable payloads elsewhere in
  the client] → `validatePanel` is the only dispatch entry; grep-verified call
  sites in the test suite only.
- [Behavior change: unavailable payloads no longer validate through per-panel
  functions] → Internal API only; the public path (`validatePanel`) is unchanged
  in behavior for correct payloads.

## Migration Plan

No released users. The change is deployable in one commit: server constant
derivation (D1/D2), JS branch removal (D3), and the two test halves (D4/D5) land
together; any intermediate state fails either the parity contract or the JS suite.

## Open Questions

None.
