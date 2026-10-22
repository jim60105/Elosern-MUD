# Design

## Context

Source of truth: `docs/superpowers/specs/2026-10-22-world-map-drawer-design.md`, introduced by approved commit `9a9200b45c406a3d28ec15b27fa4cf04380151ba`, and parent architecture `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`. §9 row 6 world-view sub-change, budgeted as 4h layered renderer/LOD, 2h animation/accessibility and 2h focused story/visual/unit verification. See proposal.md for motivation and prerequisites. The prototype is a layout/interaction reference only; its old river, forest and political geometry must never become runtime data.

## Goals / Non-Goals

Implement only the assigned slice described below. No elevation, travel automation, new quests, shipping mechanics, compatibility layer or data migration. Existing canonical identities, knowledge ownership and deterministic offline play remain intact.

## Decisions

Consume only validated world_map, never import server lore or prototype geometry/name tables. Draw exactly the approved ordered layers; use server filtered lit geometry and treat unlit identities as opaque. Sea/land/common border layers are common knowledge, while detailed rivers/ridge/roads require supplied lit shapes. Do not infer undisclosed landmarks through client hit testing or outlines. Render labels as screen-space overlays with a 16 CSS px floor and collision hiding by stable priority; never scale glyph text with world zoom. Inclusive span thresholds are <=1000 for lit district/place and <=450 for 未探明; nation labels follow continent/country states. Nearby trail cells obey server resolution metadata (1 or 5 km).

Selections return semantic identity and the permitted supplied details to the host. A lit deep-forest selection includes both national affiliations; an unlit district remains nameless. The host owns the actual right detail drawer and quest list, preventing duplicate client state. The world view receives/exposes controlled viewport data via the pure shared module.

Track the last presented lit set only in session view memory, keyed to transport/puppet epoch. Initial load/reopen must not replay all lit districts; only a new unlit-to-lit transition observed while open yields a 600 ms landmark-origin ink mask and one live announcement. Use existing motion/reduced-motion preferences, including reduced/off instant placement. Rendering a new payload must not alter persistent knowledge. Focus and keyboard remain in real HTML/text controls.

## Real-component visual workflow

Storybook stories MUST import the real production components and use schema-valid panel fixtures, never mount/copy `WorldMapPrototype.vue` as evidence. Reproduce approved option-A scenarios and add the slice-specific accessibility/interaction cases. Each relevant story `play` MUST assert real DOM behavior. During implementation start the project Storybook workflow, use the `agent-browser` skill to open the affected real-component stories, exercise keyboard/pointer interactions and save captures. Repeat relevant geometry in the live client under `.elosern-root`; review/remove conflicting `styles/app-shell.css` overrides. Screenshot existence alone is insufficient: inspect captures and record observed behavior. Keep component-story ownership/coverage manifests current. Run focused story/component/browser selections, never broad suites. Use shared tokens, UI scale and at least 16 CSS px labels; hide lower-priority labels rather than shrink them.


## Risks / Trade-offs

The prototype violates some final geography/privacy rules and is only a visual reference. A naive animation on every mount reannounces all old discoveries. Screen-space text and server trail resolution must remain coherent under zoom.

## Implementation verification contract

Implementation MUST run the smallest affected Evennia label, Node file, Vitest file, or managed browser class, never broad suites or CI shard commands locally. Every local test command must stay below ten minutes. Use `uv run --locked --env-file=<path> evennia test --settings test_settings.py --keepdb <focused.label>`, with `MUD_TEST_SETTINGS=1` in that env file. Pure tool tests use a focused `uv run --locked python -m unittest <module>`; client units use a single-file runner.

Register every new/moved non-browser package test module in exactly one `.github/evennia-shards.json` shard; register every new browser class/method in `.github/browser-shards.json`. Keep synthetic mechanism fixtures independent of production lore. Production content integrity tests need a first-line `Data-contract test: <reason>` and matching `tools/test_data_freeze.json` entry.

Use `tools.spec_traceability list` to obtain canonical IDs, never guess them. Because active deltas are not indexed, obtain new/retired IDs by running `uv run --locked python -m tools.spec_traceability list` against a disposable equivalent spec tree with these deltas merged, using `--repo-root <equivalent-root>` before the `list` or `check` subcommand. Apply literal `covers_requirement` annotations to real discoverable Python assertions (including managed browser assertions for client behavior); do not leave unknown active-delta IDs in the unsynced repository. Run `check` against the equivalent merged tree with those tests before sync, and the normal root `check` after sync. A pre-sync root pass alone does not establish coverage of this change. Existing IDs remain checked at root; CI alone runs full evidence verification.

All changed server, movement and panel logging uses named imports from `world.observability`, stable snake_case events and contextual business identifiers. Changed cross-system/I/O boundaries emit the applicable catalog event; exception branches re-raise, log through the facade with `exc=`, or carry a reasoned lint exemption. Patch the caller's log binding in tests. Run the observability lint with focused tests when a logging path changes. Never add freeze-list entries.

Before implementation handoff run `uv run --locked python -m tools.contract_gate` and `openspec validate <change> --strict`. Update existing development/game documentation for changed behavior; do not add unrelated features, migrations or compatibility aliases. Proposal creation does not run implementation tests.
