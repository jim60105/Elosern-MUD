# Design

## Context

Source of truth: `docs/superpowers/specs/2026-10-22-world-map-drawer-design.md`, introduced by approved commit `9a9200b45c406a3d28ec15b27fa4cf04380151ba`, and parent architecture `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`. §9 row 2 is split: this 5h registry/lighting slice precedes the separate 8h partition slice; the combined row exceeds the 8h limit. See proposal.md for motivation and prerequisites. The prototype is a layout/interaction reference only; its old river, forest and political geometry must never become runtime data.

## Goals / Non-Goals

Implement only the assigned slice described below. No elevation, travel automation, new quests, shipping mechanics, compatibility layer or data migration. Existing canonical identities, knowledge ownership and deterministic offline play remain intact.

## Decisions

Use frozen dataclasses and keyed module-level registries following existing lore conventions. Keep the six approved fields and one unique landmark per district. Resolve grid geometry through settlement anchor transforms for spacing/reachability; do not create rooms during validation. Keep world/lore declarations read-only and put knowledge parsing/lighting in world/rules.

Seed the registry with a small, real usable set of geographically valid named districts sufficient for the later partition tool, including the single deep-forest region district and seeds in each non-forest nominal territory/component. This is an actual validated registry, not mocks, placeholders or a second temporary registry. The content-authoring change expands it to the approved 110–130 total. Declare a positive minimum Voronoi spacing in one place and report it in authoring docs; 100 km is the proposed authoring choice within the approximately 200 km district target. The deep-forest region exception does not require one seed per nation.

Read parsed visited identities using the existing map-knowledge API. Do not alter record_arrival, add lit flags, or attach names/geometry to persisted knowledge. First-arrival narrative is explicitly owned by the later world panel change.

## Risks / Trade-offs

A seed inside a grid needs a correct local-to-world anchor transform. A region district can belong to both nations; do not duplicate the forest solely to match political boundaries.

## Implementation verification contract

Implementation MUST run the smallest affected Evennia label, Node file, Vitest file, or managed browser class, never broad suites or CI shard commands locally. Every local test command must stay below ten minutes. Use `uv run --locked --env-file=<path> evennia test --settings test_settings.py --keepdb <focused.label>`, with `MUD_TEST_SETTINGS=1` in that env file. Pure tool tests use a focused `uv run --locked python -m unittest <module>`; client units use a single-file runner.

Register every new/moved non-browser package test module in exactly one `.github/evennia-shards.json` shard; register every new browser class/method in `.github/browser-shards.json`. Keep synthetic mechanism fixtures independent of production lore. Production content integrity tests need a first-line `Data-contract test: <reason>` and matching `tools/test_data_freeze.json` entry.

Use `tools.spec_traceability list` to obtain canonical IDs, never guess them. Because active deltas are not indexed, obtain new/retired IDs by running `uv run --locked python -m tools.spec_traceability list` against a disposable equivalent spec tree with these deltas merged, using `--repo-root <equivalent-root>` before the `list` or `check` subcommand. Apply literal `covers_requirement` annotations to real discoverable Python assertions (including managed browser assertions for client behavior); do not leave unknown active-delta IDs in the unsynced repository. Run `check` against the equivalent merged tree with those tests before sync, and the normal root `check` after sync. A pre-sync root pass alone does not establish coverage of this change. Existing IDs remain checked at root; CI alone runs full evidence verification.

All changed server, movement and panel logging uses named imports from `world.observability`, stable snake_case events and contextual business identifiers. Changed cross-system/I/O boundaries emit the applicable catalog event; exception branches re-raise, log through the facade with `exc=`, or carry a reasoned lint exemption. Patch the caller's log binding in tests. Run the observability lint with focused tests when a logging path changes. Never add freeze-list entries.

Before implementation handoff run `uv run --locked python -m tools.contract_gate` and `openspec validate <change> --strict`. Update existing development/game documentation for changed behavior; do not add unrelated features, migrations or compatibility aliases. Proposal creation does not run implementation tests.
