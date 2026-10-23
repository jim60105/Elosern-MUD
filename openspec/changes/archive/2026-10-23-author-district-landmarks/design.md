# Design

## Context

Source of truth: `docs/superpowers/specs/2026-10-22-world-map-drawer-design.md`, introduced by approved commit `9a9200b45c406a3d28ec15b27fa4cf04380151ba`, and parent architecture `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`. §9 row 3 remains one content-authoring change, budgeted as 5h roster/name authoring, 1h regeneration and 2h focused integrity/reachability verification. See proposal.md for motivation and prerequisites. The prototype is a layout/interaction reference only; its old river, forest and political geometry must never become runtime data.

## Goals / Non-Goals

Implement only the assigned slice described below. No elevation, travel automation, new quests, shipping mechanics, compatibility layer or data migration. Existing canonical identities, knowledge ownership and deterministic offline play remain intact.

## Decisions

Use the existing validated seed registry as the only source and expand it in place, preserving stable keys already declared. Author names as Traditional Chinese JRPG sword-and-magic geography, not NPC dialogue. Read the fantasy-name-generator and zh-TW terminology skills during implementation before name authoring. No extra named cities, quests, settlements or NPCs are introduced by map landmarks. Reuse an existing grid node when valid; wilderness landmarks are canonical positions and need no permanent room spawning.

Distribute Voronoi seeds across reachable non-forest nominal territories around the approximately 200 km target; do not insert additional forest landmarks to reach a count. Keep minimum spacing and rerun the established deterministic tool, adjusting authored positions to satisfy validation. The prototype has outdated geography and only 109 rough outlines; neither its seeds nor names are final content. Keep hidden elven/dungeon places hidden under the later panel policy.

Accept approximate roster count/size as authoring targets while preserving hard coverage, identity, spacing and barrier requirements. Document meaningful geographic rationale and the regeneration command in existing authoring documentation, without a second duplicated approved-value table.

## Risks / Trade-offs

Names alone are insufficient: changed seeds alter coverage and real world payload size. Validate full final partition in this change so later transport measurement uses real data.

## Implementation verification contract

Implementation MUST run the smallest affected Evennia label, Node file, Vitest file, or managed browser class, never broad suites or CI shard commands locally. Every local test command must stay below ten minutes. Use `uv run --locked --env-file=<path> evennia test --settings test_settings.py --keepdb <focused.label>`, with `MUD_TEST_SETTINGS=1` in that env file. Pure tool tests use a focused `uv run --locked python -m unittest <module>`; client units use a single-file runner.

Register every new/moved non-browser package test module in exactly one `.github/evennia-shards.json` shard; register every new browser class/method in `.github/browser-shards.json`. Keep synthetic mechanism fixtures independent of production lore. Production content integrity tests need a first-line `Data-contract test: <reason>` and matching `tools/test_data_freeze.json` entry.

Use `uv run --locked python -m tools.spec_traceability --repo-root <equivalent-root> list` to obtain canonical IDs, never guess them. Before sync, create a disposable ordinary directory containing the complete current implementation, tests, manifests and tooling (not a git worktree), and apply all prerequisite/current spec deltas to its copied main specs in dependency order. Keep literal intended `covers_requirement` annotations in the actual implementation; they may be unknown to unsynced root specs. Run `check` with `--repo-root <equivalent-root>` and run the copied `tools.contract_gate` from that complete equivalent directory before handoff. Do not demand a root contract-gate pass before specs are synced. After sync, run the normal root traceability check and contract gate with unchanged annotations. Associate only substantive discoverable Python assertions; a focused Python wrapper that actually executes JS/browser assertions is valid, source-presence checks are not. CI alone runs complete evidence verification.

All changed server, movement and panel logging uses named imports from `world.observability`, stable snake_case events and contextual business identifiers. Changed cross-system/I/O boundaries emit the applicable catalog event; exception branches re-raise, log through the facade with `exc=`, or carry a reasoned lint exemption. Patch the caller's log binding in tests. Run the observability lint with focused tests when a logging path changes. Never add freeze-list entries.

Before implementation handoff run strict validation and the copied contract gate from the complete equivalent merged-spec directory described above. After main-spec sync run `uv run --locked python -m tools.contract_gate` at the actual root. Update existing behavior documentation; no unrelated features, migrations or compatibility aliases. Proposal creation does not run implementation tests.
