# Design

## Context

The shared `_GraphBuilder.add_node` in `web/webclient/presentation/local_map/builder.py` emits exact node dictionaries for grid, wilderness and interior adapters. Both `_validate_node` and browser `validateLocalMapNode` currently accept the same nine fields. The browser `nodeModel` copies coordinates/actions but has no gateway field. `gateways.py` already owns `_grid_gateway_at`, `_wilderness_gateway_at`, `_wild_region_label` and `_gateway_far_side_label`; reuse these helpers. See proposal.md for motivation and the approved design §4.1, §6.1–§6.2, §8 for acceptance.

## Goals / Non-Goals

Make gateway metadata authoritative transport and preserve it in the model. Do not change coordinates, map knowledge, move authorization, schema_version, overlay rendering or radial layout. This slice is a complete protocol cutover; the later island renderer consumes it.

## Decisions

Add `gateway=None` to the builder API and include it on every emitted node. Populate registered grid gate-room metadata for current and in-view grid rooms with the existing far-side region helper; populate adjacent wilderness grid-gate targets with the settlement helper. Set null for ordinary nodes and coordinate-free adapters. Preserve the design's registry semantics for remembered nodes without changing their existing edge-marker presentation. Handle builder deduplication without losing metadata when an already-present gateway node is enriched. No new label registry or server screen coordinates.

Require `gateway` under both exact node-field checks. Validate null or an exact object containing only `leads_to`, using the existing non-empty/whitespace and Unicode code-point bound of 256 (`LOCAL_MAP_MAX_STRING` on the browser). Include the field in normalized output and pass it through `nodeModel` unchanged. Keep schema_version 1 because both ends ship together. No omission defaults in validators and no compatibility alias.

Update every authored local-map node fixture/caller across Python support helpers, Node protocol/model tests, Storybook `stories/fixtures/local_map.js`, inline Core stories, Vue tests and managed-browser payload factories. Use builder defaults for production non-gateway callers, but fixtures passed to exact validation must include the field explicitly or through their shared factory. Recalculate serialized-size assertions with null/object gateway overhead without weakening the 65,536-byte limit.

## Risks / Trade-offs

An incomplete fixture cutover disables the map under exact validation. Cover current gate, visible gate, wilderness-adjacent grid gate, ordinary and interior nodes. Do not rename or restructure test modules for this field addition. The server's read-only presenter stays read-only and retains existing exception boundaries.

## Focused evidence

Extend `web.webclient.presentation.tests.test_local_map.test_schema.LocalMapSchemaTests` and the existing `test_grid_gateways`/`test_wilderness` modules with registry-derived synthetic gateway cases. Run each affected test method/class separately. Run `node --test web/static/webclient/js/tests/protocol_local_map.test.js` and `node --test web/static/webclient/js/tests/local_map.test.js` as separate commands. Verify unchanged `World/LocalMap` gate/action stories visually with agent-browser after fixture cutover; no gate UI is added in this slice.

## Verification workflow (required during implementation)

### Traceability gate ordering

Existing-title IDs can use the normal live-tree gates. When implementation adds IDs absent from unsynchronized main specs, use a complete disposable directory snapshot of the current implementation, manifests and tooling with predecessor/current deltas applied to its equivalent main-spec tree. This is an ordinary copy, not a branch or registered git worktree. Obtain IDs with `uv run --locked python -m tools.spec_traceability --repo-root <equivalent-root> list`, then run `check` with the same root. Run the complete gate using the copied script, `uv run --locked python <equivalent-root>/tools/contract_gate.py`, so its file-derived root and subprocess working directories select that snapshot. Retain the implementation annotations unchanged. After the authorized archive step synchronizes the real main specs, repeat ordinary live-tree `tools.spec_traceability check` and `tools.contract_gate`. All task references to those gates follow this phase-aware sequence; listing IDs in the snapshot alone is insufficient, and an unsynchronized live-tree unknown-ID failure must never be suppressed.

Use `World/LocalMap` as the production component showcase and retain `Overlays/MapOverlay` plus the instance/interior stories as unchanged-surface controls. No `Design/...` prototype is needed for this approved algorithmic change; if an existing relevant Design story is used for token/chrome comparison, it cannot replace a production-component story or the real client.

Read the agent-browser skill, start the repository's existing Storybook command (`pnpm run serve-storybook`), navigate to the affected story, take an interactive snapshot, and capture a screenshot with agent-browser. Inspect the actual image for missing exits, clipping, label readability and shape/text mode distinction. Refresh element references after each story or payload change. Record story IDs, viewport, screenshot locations and observed results in the implementation handoff. Automation play assertions do not replace this visual step. The renderer and later changes must also inspect the real client because `.elosern-root` rules in `styles/app-shell.css` can override component styles absent from Storybook.

Run only the smallest focused Python label, Node file, Vitest file or managed-browser method/class that covers the changed assertions, one short batch per command. Python always uses `uv run --locked`; Evennia uses `uv run --locked --env-file=<test-env-file> evennia test --settings test_settings.py --keepdb <label>` with `MUD_TEST_SETTINGS=1` inside that env file. Use the single-token env-file spelling. Run a browser method with `uv run --locked python -m web.tests.browser.unittest_driver <module.Class.test_method>` and capture its output once. No local full suites, shard commands, complete showcase matrix or `spec_traceability verify --evidence`; keep each local command below ten minutes and browser files below five CI minutes.

For every requirement, map the concrete scenario to matching assertions. Obtain literal IDs with `uv run --locked python -m tools.spec_traceability list`; for newly added requirements run that tool on an equivalent spec tree with predecessor and current deltas synchronized, using its documented root option, without prematurely modifying the live main specs. Never hand-construct IDs. Decorate discoverable Python `test_*` methods with `covers_requirement` imported from `tools.spec_traceability`. JS-only behavior needs a focused Python executed-evidence wrapper that actually runs the relevant file and asserts success, reusing existing evidence patterns; a source-presence assertion cannot substitute for execution. Keep existing IDs when titles are unchanged and review their matching assertions after each modified contract. Run `tools.spec_traceability check` while editing and against the synchronized main contract at archive time; a pre-sync pass alone is insufficient.

Add/rename/move any non-browser Python test module only with an exact single-owner update in `.github/evennia-shards.json`. Add every new browser test class or method to `.github/browser-shards.json` in the same feature commit, without overlapping class/method ownership. Reusing an already registered module does not need a fabricated manifest change; record that ownership is unchanged. Run the focused shard-ownership contract if ownership changes, and finish with `uv run --locked python -m tools.contract_gate` and `openspec validate <change> --strict`. Before archive also run the focused `tests.test_evennia_test_optimization_contract` and `tests.test_webclient_frozen_contract` labels as required by AGENTS.md.

No new operational logging is needed for pure projection/render work. Preserve existing boundary observability. Any changed exception/logging path must use named imports from `world.observability`, stable English event IDs and business identifiers in context; patch the caller binding in tests and run `uv run --locked python -m tools.observability_lint check` with the focused tests. Do not add logging imports, silent swallowing, a freeze-list entry or a new telemetry subsystem.
