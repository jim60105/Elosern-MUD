# Design

## Context

Source of truth: `docs/superpowers/specs/2026-10-22-world-map-drawer-design.md`, introduced by approved commit `9a9200b45c406a3d28ec15b27fa4cf04380151ba`, and parent architecture `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`. §9 row 6 area-view sub-change, after its pure viewport and server panel; 4h renderer, 1h stories and 2h focused unit/visual verification. See proposal.md for motivation and prerequisites. The prototype is a layout/interaction reference only; its old river, forest and political geometry must never become runtime data.

## Goals / Non-Goals

Implement only the assigned slice described below. No elevation, travel automation, new quests, shipping mechanics, compatibility layer or data migration. Existing canonical identities, knowledge ownership and deterministic offline play remain intact.

## Decisions

AreaMapView consumes the validated area model plus viewport state and emits selection/move/view changes. It does not request server data itself or clone local_map. Reuse existing radial graph layout for coordinate-free instance/interior nodes without inventing canonical positions; settlement projection reads metres exactly, and wilderness positions/visited flags follow its panel scale. Only the existing adjacent descriptor exposes 前往 and emits its exact intent; preserve disabled/missing actions as non-travel selection. Keep gateway leads_to visible as approved far-side text.

Expose view controls/state so MapDrawer can own per-tab session memory, opening fit and keyboard navigation. A map_id/frame key/unit change clears incompatible selection/viewport and re-fits current adjacency; never reuse settlement metre state for wilderness km or radial rooms. Implement scale-true round metric dots and caption with consistent units; reuse the minimap scale-true design without depending on its auto-scale island geometry. Collision handling hides low-priority labels rather than shrinking below 16 px; full names remain available in textual selection. The final host supplies chrome and offscreen pointers, so do not create a second drawer or duplicate shell.

Implementation notes: 前往 emits `{ exit_ref, destination, current_node }`, where `current_node` is the area payload's canonical current node (the same canonical ID space `explore.move` validates). The existing `onMapMove` handler still builds `current_node` from the minimap model, so the final drawer cutover must forward the emitted `current_node` instead; this slice does not rewire that runtime handler. The selection reading is a separate `AreaMapDetail` child rendered through a `detail` slot, so the final drawer can replace it (or pass `showDetail: false`) without a second drawer. Arrow keys move focus spatially between nodes and auto-pan to keep the focused node visible; Shift+arrows stay free for the host's pan. Radial (instance/interior) views still open centred on the current room at a zoom that fits its neighbours, but widen to show every room. Radial units carry no distance, so a tighter fit would only send roads off the frame. 前往 is sent once per published area body; a repeated activation waits for the server's republish. When the map signature changes, a host-supplied `selected` that names a node of the new map is kept, and the drawer's session memory relies on this. Cutover checklist for the final drawer: forward the emitted `current_node` into `explore.move`, and supply per-tab `view`/`selected`.

## Real-component visual workflow

Storybook stories MUST import the real production components and use schema-valid panel fixtures, never mount/copy `WorldMapPrototype.vue` as evidence. Reproduce approved option-A scenarios and add the slice-specific accessibility/interaction cases. Each relevant story `play` MUST assert real DOM behavior. During implementation start the project Storybook workflow, use the `agent-browser` skill to open the affected real-component stories, exercise keyboard/pointer interactions and save captures. Repeat relevant geometry in the live client under `.elosern-root`; review/remove conflicting `styles/app-shell.css` overrides. Screenshot existence alone is insufficient: inspect captures and record observed behavior. Keep component-story ownership/coverage manifests current. Run focused story/component/browser selections, never broad suites. Use shared tokens, UI scale and at least 16 CSS px labels; hide lower-priority labels rather than shrink them.


### Executable traceability owner

Add a discoverable Python executed-evidence wrapper in proposed `tests.test_map_client_contracts` that launches only this slice's selected JS assertions and fails on their assertion failure. Annotate wrapper test methods with tool-derived requirement IDs, never source-presence checks; run `uv run --locked python -m unittest tests.test_map_client_contracts.AreaViewContracts` for this slice. This top-level module is outside the Evennia shard manifest; any package/browser owners still require their own exact manifests.

## Risks / Trade-offs

The old graph code may assume local_map visibility names and its 64-node window. Reuse only the radial placement mechanics, with an explicit area-map model adapter and no whole-area truncation.

## Implementation verification contract

Implementation MUST run the smallest affected Evennia label, Node file, Vitest file, or managed browser class, never broad suites or CI shard commands locally. Every local test command must stay below ten minutes. Use `uv run --locked --env-file=<path> evennia test --settings test_settings.py --keepdb <focused.label>`, with `MUD_TEST_SETTINGS=1` in that env file. Pure tool tests use a focused `uv run --locked python -m unittest <module>`; client units use a single-file runner.

Register every new/moved non-browser package test module in exactly one `.github/evennia-shards.json` shard; register every new browser class/method in `.github/browser-shards.json`. Keep synthetic mechanism fixtures independent of production lore. Production content integrity tests need a first-line `Data-contract test: <reason>` and matching `tools/test_data_freeze.json` entry.

Use `uv run --locked python -m tools.spec_traceability --repo-root <equivalent-root> list` to obtain canonical IDs, never guess them. Before sync, create a disposable ordinary directory containing the complete current implementation, tests, manifests and tooling (not a git worktree), and apply all prerequisite/current spec deltas to its copied main specs in dependency order. Keep literal intended `covers_requirement` annotations in the actual implementation; they may be unknown to unsynced root specs. Run `check` with `--repo-root <equivalent-root>` and run the copied `tools.contract_gate` from that complete equivalent directory before handoff. Do not demand a root contract-gate pass before specs are synced. After sync, run the normal root traceability check and contract gate with unchanged annotations. Associate only substantive discoverable Python assertions; a focused Python wrapper that actually executes JS/browser assertions is valid, source-presence checks are not. CI alone runs complete evidence verification.

All changed server, movement and panel logging uses named imports from `world.observability`, stable snake_case events and contextual business identifiers. Changed cross-system/I/O boundaries emit the applicable catalog event; exception branches re-raise, log through the facade with `exc=`, or carry a reasoned lint exemption. Patch the caller's log binding in tests. Run the observability lint with focused tests when a logging path changes. Never add freeze-list entries.

Before implementation handoff run strict validation and the copied contract gate from the complete equivalent merged-spec directory described above. After main-spec sync run `uv run --locked python -m tools.contract_gate` at the actual root. Update existing behavior documentation; no unrelated features, migrations or compatibility aliases. Proposal creation does not run implementation tests.
