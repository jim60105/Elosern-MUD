# Design

## Context

Source of truth: `docs/superpowers/specs/2026-10-22-world-map-drawer-design.md`, introduced by approved commit `9a9200b45c406a3d28ec15b27fa4cf04380151ba`, and parent architecture `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`. §9 row 2 is split: this 5h registry/lighting slice precedes the separate 8h partition slice; the combined row exceeds the 8h limit. See proposal.md for motivation and prerequisites. The prototype is a layout/interaction reference only; its old river, forest and political geometry must never become runtime data.

## Goals / Non-Goals

Implement only the assigned slice described below. No elevation, travel automation, new quests, shipping mechanics, compatibility layer or data migration. Existing canonical identities, knowledge ownership and deterministic offline play remain intact.

## Decisions

Use frozen dataclasses and keyed module-level registries following existing lore conventions. Keep the six approved fields and one unique landmark per district. Resolve grid landmarks through the settlement local-to-world transform for spacing and land membership; reachability uses the real grid graph and its registered gateway approaches, not provider passability of the blocked anchor footprint. Partition seed injection is fixed in compute-map-district-partition. Do not create rooms during validation. Keep world/lore declarations read-only and put knowledge parsing/lighting in world/rules.

Seed the registry with a small, real usable set of geographically valid named districts sufficient for the later partition tool, including the single deep-forest region district and seeds in each non-forest nominal territory/component. This is an actual validated registry, not mocks, placeholders or a second temporary registry. The content-authoring change expands it to the approved 110–130 total. Declare a positive minimum Voronoi spacing in one place and report it in authoring docs; 100 km is the proposed authoring choice within the approximately 200 km district target. The deep-forest region exception does not require one seed per nation.

Read parsed visited identities using the existing map-knowledge API. Do not alter record_arrival, add lit flags, or attach names/geometry to persisted knowledge. First-arrival narrative is explicitly owned by the later world panel change.

## Risks / Trade-offs

A seed inside a grid needs a correct local-to-world anchor transform. A region district can belong to both nations; do not duplicate the forest solely to match political boundaries.

## Implementation verification contract

Implementation MUST run the smallest affected Evennia label, Node file, Vitest file, or managed browser class, never broad suites or CI shard commands locally. Every local test command must stay below ten minutes. Use `uv run --locked --env-file=<path> evennia test --settings test_settings.py --keepdb <focused.label>`, with `MUD_TEST_SETTINGS=1` in that env file. Pure tool tests use a focused `uv run --locked python -m unittest <module>`; client units use a single-file runner.

Register every new/moved non-browser package test module in exactly one `.github/evennia-shards.json` shard; register every new browser class/method in `.github/browser-shards.json`. Keep synthetic mechanism fixtures independent of production lore. Production content integrity tests need a first-line `Data-contract test: <reason>` and matching `tools/test_data_freeze.json` entry.

Use `uv run --locked python -m tools.spec_traceability --repo-root <equivalent-root> list` to obtain canonical IDs, never guess them. Before sync, create a disposable ordinary directory containing the complete current implementation, tests, manifests and tooling (not a git worktree), and apply all prerequisite/current spec deltas to its copied main specs in dependency order. Keep literal intended `covers_requirement` annotations in the actual implementation; they may be unknown to unsynced root specs. Run `check` with `--repo-root <equivalent-root>` and run the copied `tools.contract_gate` from that complete equivalent directory before handoff. Do not demand a root contract-gate pass before specs are synced. After sync, run the normal root traceability check and contract gate with unchanged annotations. Associate only substantive discoverable Python assertions; a focused Python wrapper that actually executes JS/browser assertions is valid, source-presence checks are not. CI alone runs complete evidence verification.

All changed server, movement and panel logging uses named imports from `world.observability`, stable snake_case events and contextual business identifiers. Changed cross-system/I/O boundaries emit the applicable catalog event; exception branches re-raise, log through the facade with `exc=`, or carry a reasoned lint exemption. Patch the caller's log binding in tests. Run the observability lint with focused tests when a logging path changes. Never add freeze-list entries.

Before implementation handoff run strict validation and the copied contract gate from the complete equivalent merged-spec directory described above. After main-spec sync run `uv run --locked python -m tools.contract_gate` at the actual root. Update existing behavior documentation; no unrelated features, migrations or compatibility aliases. Proposal creation does not run implementation tests.
