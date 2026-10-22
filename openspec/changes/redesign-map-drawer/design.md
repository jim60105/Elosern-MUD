# Design

## Context

Source of truth: `docs/superpowers/specs/2026-10-22-world-map-drawer-design.md`, introduced by approved commit `9a9200b45c406a3d28ec15b27fa4cf04380151ba`, and parent architecture `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`. §9 row 6 final integration sub-change, after viewport and the two real views; 4h shell/request/pointer wiring, 2h story/keyboard work and 2h focused live walk/removal/docs. See proposal.md for motivation and prerequisites. The prototype is a layout/interaction reference only; its old river, forest and political geometry must never become runtime data.

## Goals / Non-Goals

Implement only the assigned slice described below. No elevation, travel automation, new quests, shipping mechanics, compatibility layer or data migration. Existing canonical identities, knowledge ownership and deterministic offline play remain intact.

## Decisions

Compose the two real views under the existing OverlayHost modal/focus shell. Reuse shared DrawerHeader/ARIA tab primitives and tokens, without nesting an extra modal or duplicate close header. Add a header/content slot seam only as needed for the single map header while preserving settings/help/gallery shells. Apply option A only: full map body, floating controls, quest dropdown, scale bar, selected-only ~360px detail. The fixed three-column option is rejected. MapEdgePointers is real HTML using shared rectangle clamping, distance-ordered stacks, max three visible then ＋n; its overflow and the quest list keep every accepted commission keyboard reachable.

Keep one controlled viewport per tab for the transport/puppet session. First open selects scope by current layer; return tab views preserve pan/zoom. Area initial fit includes current adjacency; world country default is 800km and fits tracked target with player only when within 800km, using only server-approved marker precision. Send map.view on open/tab change and once per committed move while open, after the existing action-result/publication commit signal, never on optimistic movement, rejected input, arbitrary status updates or closed state. Guard a closing/tab/epoch change so stale responses cannot overwrite the active view; use existing action admission/ordering without a new retry queue. The server remains read-only and does not know open drawer state.

Own modal keyboard priority before OverlayHost closes: 1/2 tabs, arrows pan, +/- stop zoom, C recenter, 0 fit, and Escape legend then details then map. Quest dropdown has its own ordinary popover dismissal without violating that chain. Final close restores opener focus; text inputs/composition/modifiers retain standard protections. Forward adjacent 前往 through the existing opaque explore.move/current-node path only. Mirror selected districts/places/commissions and all quest pointers in accessible text; never reconstruct unlit contents.

After the explicit minimap completion dependency, migrate every old map consumer/test/story, absorb still-useful `map_view.js` behavior into `map_viewport.js`, remove obsolete exports/composables and delete MapOverlay plus cellSize, rank compression and overlay-pitch branches with no shim. Preserve coordinate-free graph rendering still used by minimap/area views and unrelated movement pan helpers. Retire/remap obsolete full-map requirement annotations by actual assertion role, not global text replacement.

## Real-component visual workflow

Storybook stories MUST import the real production components and use schema-valid panel fixtures, never mount/copy `WorldMapPrototype.vue` as evidence. Reproduce approved option-A scenarios and add the slice-specific accessibility/interaction cases. Each relevant story `play` MUST assert real DOM behavior. During implementation start the project Storybook workflow, use the `agent-browser` skill to open the affected real-component stories, exercise keyboard/pointer interactions and save captures. Repeat relevant geometry in the live client under `.elosern-root`; review/remove conflicting `styles/app-shell.css` overrides. Screenshot existence alone is insufficient: inspect captures and record observed behavior. Keep component-story ownership/coverage manifests current. Run focused story/component/browser selections, never broad suites. Use shared tokens, UI scale and at least 16 CSS px labels; hide lower-priority labels rather than shrink them.

Approved real-story coverage is A_AreaCity, A_AreaCitySelected, A_AreaWilderness, A_WorldRegion, A_WorldContinent, A_WorldDistrictSelected and A_WorldNearby, plus dungeon/interior, overflow pointers, legend/Escape and reduced-motion reveal. Use real MapDrawer with its real children and play assertions for pointers, nameless unlit districts and 前往. No option-B story needs a production implementation. The final agent-browser walkthrough opens in Altoria, travels through a gate, reaches an actual landmark to light its district, then follows a commission pointer. Capture those checkpoints in the real client and inspect geometry under .elosern-root.

## Risks / Trade-offs

Panel publication completion can occur before action_result arrival; coalesce by the existing committed movement identity instead of refreshing twice. Old global hotkeys include C for party status, so modal map focus must consume C before that handler. Minimap still owns graph layout utilities that cannot be deleted wholesale.

## Implementation verification contract

Implementation MUST run the smallest affected Evennia label, Node file, Vitest file, or managed browser class, never broad suites or CI shard commands locally. Every local test command must stay below ten minutes. Use `uv run --locked --env-file=<path> evennia test --settings test_settings.py --keepdb <focused.label>`, with `MUD_TEST_SETTINGS=1` in that env file. Pure tool tests use a focused `uv run --locked python -m unittest <module>`; client units use a single-file runner.

Register every new/moved non-browser package test module in exactly one `.github/evennia-shards.json` shard; register every new browser class/method in `.github/browser-shards.json`. Keep synthetic mechanism fixtures independent of production lore. Production content integrity tests need a first-line `Data-contract test: <reason>` and matching `tools/test_data_freeze.json` entry.

Use `tools.spec_traceability list` to obtain canonical IDs, never guess them. Because active deltas are not indexed, obtain new/retired IDs by running `uv run --locked python -m tools.spec_traceability list` against a disposable equivalent spec tree with these deltas merged, using `--repo-root <equivalent-root>` before the `list` or `check` subcommand. Apply literal `covers_requirement` annotations to real discoverable Python assertions (including managed browser assertions for client behavior); do not leave unknown active-delta IDs in the unsynced repository. Run `check` against the equivalent merged tree with those tests before sync, and the normal root `check` after sync. A pre-sync root pass alone does not establish coverage of this change. Existing IDs remain checked at root; CI alone runs full evidence verification.

All changed server, movement and panel logging uses named imports from `world.observability`, stable snake_case events and contextual business identifiers. Changed cross-system/I/O boundaries emit the applicable catalog event; exception branches re-raise, log through the facade with `exc=`, or carry a reasoned lint exemption. Patch the caller's log binding in tests. Run the observability lint with focused tests when a logging path changes. Never add freeze-list entries.

Before implementation handoff run `uv run --locked python -m tools.contract_gate` and `openspec validate <change> --strict`. Update existing development/game documentation for changed behavior; do not add unrelated features, migrations or compatibility aliases. Proposal creation does not run implementation tests.
