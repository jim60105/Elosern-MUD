# Design

## Context

Source of truth: `docs/superpowers/specs/2026-10-22-world-map-drawer-design.md`, introduced by approved commit `9a9200b45c406a3d28ec15b27fa4cf04380151ba`, and parent architecture `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`. §9 row 6 is split into viewport (5h), area view (7h), world view (8h), and final drawer integration (8h), since the complete row exceeds 8h. See proposal.md for motivation and prerequisites. The prototype is a layout/interaction reference only; its old river, forest and political geometry must never become runtime data.

## Goals / Non-Goals

Implement only the assigned slice described below. No elevation, travel automation, new quests, shipping mechanics, compatibility layer or data migration. Existing canonical identities, knowledge ownership and deterministic offline play remain intact.

## Decisions

Use centre {cx,cy}, horizontal span and measured pixel width/height. World units are km, grid units are m, wilderness cell indices convert through the provider panel scale; coordinate-free graph placement stays a separate radial renderer. Return immutable numeric results from pure functions. Scope stops are values, not a second server map model. World continent fit uses actual coastline bounds plus consistent margin and viewport aspect ratio; country/district/nearby spans are 800/200/40 km. City stop spans derive from known settlement geometry rather than copying prototype Altoria-only constants; wilderness uses the 15-cell window with two stops.

Define projection/inversion, pixel drag delta pan, anchored wheel zoom, next/previous stop, fit/recentre and edge clamping to an explicit usable rectangle. Excluding details/controls is geometry supplied by the host, not DOM querying inside the pure module. Unit tests use independently known non-square and unequal-gap inputs. Do not copy old scaleBounds min=1 into metric map stops.

The old `map_view.js` still serves live MapOverlay during this prerequisite slice; leave it intact until redesign-map-drawer migrates every remaining caller and deletes it. No alias/re-export shim. This slice adds no visual component and must not create a mock-only Storybook harness; downstream real AreaMapView, WorldMapView and MapDrawer stories exercise this module and are mandatory visual evidence in those slices.

### Executable traceability owner

Add a discoverable Python executed-evidence wrapper in proposed `tests.test_map_client_contracts` that launches only this slice's selected JS assertions and fails on their assertion failure. Annotate wrapper test methods with tool-derived requirement IDs, never source-presence checks; run `uv run --locked python -m unittest tests.test_map_client_contracts.ViewportContracts` for this slice. This top-level module is outside the Evennia shard manifest; any package/browser owners still require their own exact manifests.

## Risks / Trade-offs

A wide viewport can fit width while clipping north/south; fit must consider both axes. Projecting cell corners in one layer and centres in another causes drift in scale captions and quest markers.

## Implementation verification contract

Implementation MUST run the smallest affected Evennia label, Node file, Vitest file, or managed browser class, never broad suites or CI shard commands locally. Every local test command must stay below ten minutes. Use `uv run --locked --env-file=<path> evennia test --settings test_settings.py --keepdb <focused.label>`, with `MUD_TEST_SETTINGS=1` in that env file. Pure tool tests use a focused `uv run --locked python -m unittest <module>`; client units use a single-file runner.

Register every new/moved non-browser package test module in exactly one `.github/evennia-shards.json` shard; register every new browser class/method in `.github/browser-shards.json`. Keep synthetic mechanism fixtures independent of production lore. Production content integrity tests need a first-line `Data-contract test: <reason>` and matching `tools/test_data_freeze.json` entry.

Use `uv run --locked python -m tools.spec_traceability --repo-root <equivalent-root> list` to obtain canonical IDs, never guess them. Before sync, create a disposable ordinary directory containing the complete current implementation, tests, manifests and tooling (not a git worktree), and apply all prerequisite/current spec deltas to its copied main specs in dependency order. Keep literal intended `covers_requirement` annotations in the actual implementation; they may be unknown to unsynced root specs. Run `check` with `--repo-root <equivalent-root>` and run the copied `tools.contract_gate` from that complete equivalent directory before handoff. Do not demand a root contract-gate pass before specs are synced. After sync, run the normal root traceability check and contract gate with unchanged annotations. Associate only substantive discoverable Python assertions; a focused Python wrapper that actually executes JS/browser assertions is valid, source-presence checks are not. CI alone runs complete evidence verification.

All changed server, movement and panel logging uses named imports from `world.observability`, stable snake_case events and contextual business identifiers. Changed cross-system/I/O boundaries emit the applicable catalog event; exception branches re-raise, log through the facade with `exc=`, or carry a reasoned lint exemption. Patch the caller's log binding in tests. Run the observability lint with focused tests when a logging path changes. Never add freeze-list entries.

Before implementation handoff run strict validation and the copied contract gate from the complete equivalent merged-spec directory described above. After main-spec sync run `uv run --locked python -m tools.contract_gate` at the actual root. Update existing behavior documentation; no unrelated features, migrations or compatibility aliases. Proposal creation does not run implementation tests.
