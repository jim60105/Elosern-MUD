# Design

## Context

Source of truth: `docs/superpowers/specs/2026-10-22-world-map-drawer-design.md`, introduced by approved commit `9a9200b45c406a3d28ec15b27fa4cf04380151ba`, and parent architecture `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`. §9 row 1 remains one change, budgeted as 4h geography, 2h consumer corrections and 2h tests/documentation. See proposal.md for motivation and prerequisites. The prototype is a layout/interaction reference only; its old river, forest and political geometry must never become runtime data.

## Goals / Non-Goals

Implement only the assigned slice described below. No elevation, travel automation, new quests, shipping mechanics, compatibility layer or data migration. Existing canonical identities, knowledge ownership and deterministic offline play remain intact.

## Decisions

Keep all seven region keys. A single `nation_key` cannot describe the split mountain/deep-forest regions, so retain their terrain identity and add one coordinate-sensitive nominal-claim resolver alongside geography; use existing region `nation_key` values for single-nation regions and make shared-region metadata explicitly multi-nation rather than falsely assigning one scalar nation. Migrate all nominal-claim consumers to this resolver. Derive displayed lines from the same ridge/river source; suppress line segments in deep forest. No separate authored political polyline.

Use the existing route rasterizer and passability predicates. Author exact river vertices and three ford cells together; pick vertices within the approved band with a true coastal mouth and mountain-corridor source. Author a meandering forest edge averaging Y1920 that leaves the Valhalla capital south of it. Preserve ridge height extent and travel-speed constants. Existing `region_for_coordinates` callers include monster provisioning, wilderness populations and local-map presentation; update their region enumeration windows rather than adding new region names.

Synthetic tests establish side classification and crossing mechanics; production data contracts establish anchor/harbour connectivity, shares and forest coverage without duplicating every authored vertex in a second approval table.

## Risks / Trade-offs

The 5 km partition must later preserve narrow river/ridge barriers from this 1 km geography. Changes to region enumeration windows can invalidate hunt/population assumptions; exercise those consumers with fixed inputs.

## Implementation verification contract

Implementation MUST run the smallest affected Evennia label, Node file, Vitest file, or managed browser class, never broad suites or CI shard commands locally. Every local test command must stay below ten minutes. Use `uv run --locked --env-file=<path> evennia test --settings test_settings.py --keepdb <focused.label>`, with `MUD_TEST_SETTINGS=1` in that env file. Pure tool tests use a focused `uv run --locked python -m unittest <module>`; client units use a single-file runner.

Register every new/moved non-browser package test module in exactly one `.github/evennia-shards.json` shard; register every new browser class/method in `.github/browser-shards.json`. Keep synthetic mechanism fixtures independent of production lore. Production content integrity tests need a first-line `Data-contract test: <reason>` and matching `tools/test_data_freeze.json` entry.

Use `uv run --locked python -m tools.spec_traceability --repo-root <equivalent-root> list` to obtain canonical IDs, never guess them. Before sync, create a disposable ordinary directory containing the complete current implementation, tests, manifests and tooling (not a git worktree), and apply all prerequisite/current spec deltas to its copied main specs in dependency order. Keep literal intended `covers_requirement` annotations in the actual implementation; they may be unknown to unsynced root specs. Run `check` with `--repo-root <equivalent-root>` and run the copied `tools.contract_gate` from that complete equivalent directory before handoff. Do not demand a root contract-gate pass before specs are synced. After sync, run the normal root traceability check and contract gate with unchanged annotations. Associate only substantive discoverable Python assertions; a focused Python wrapper that actually executes JS/browser assertions is valid, source-presence checks are not. CI alone runs complete evidence verification.

All changed server, movement and panel logging uses named imports from `world.observability`, stable snake_case events and contextual business identifiers. Changed cross-system/I/O boundaries emit the applicable catalog event; exception branches re-raise, log through the facade with `exc=`, or carry a reasoned lint exemption. Patch the caller's log binding in tests. Run the observability lint with focused tests when a logging path changes. Never add freeze-list entries.

Before implementation handoff run strict validation and the copied contract gate from the complete equivalent merged-spec directory described above. After main-spec sync run `uv run --locked python -m tools.contract_gate` at the actual root. Update existing behavior documentation; no unrelated features, migrations or compatibility aliases. Proposal creation does not run implementation tests.
