# Design

## Context

Source of truth: `docs/superpowers/specs/2026-10-22-world-map-drawer-design.md`, introduced by approved commit `9a9200b45c406a3d28ec15b27fa4cf04380151ba`, and parent architecture `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`. §9 row 5 presenter/narrative sub-change, after the separate 6h transport work; 4h filtered presenter/cache/trail, 2h arrival narrative and 2h focused tests/docs. See proposal.md for motivation and prerequisites. The prototype is a layout/interaction reference only; its old river, forest and political geometry must never become runtime data.

## Goals / Non-Goals

Implement only the assigned slice described below. No elevation, travel automation, new quests, shipping mechanics, compatibility layer or data migration. Existing canonical identities, knowledge ownership and deterministic offline play remain intact.

## Decisions

Extend the area-owned exact scope validator to {scope:area|world} and route world to a registered version-1 world_map presenter. Use the exact upstream world wire shape/validators and reuse on-demand policy; movement publishes no map. Cache common simplified geometry and per-district static lit content independently of player state. Build each response by filtering the current player knowledge; never cache a full player-visible panel under a district-only key. Unlit output has an opaque district key and outline only; no secret fields or production registry embedded in JavaScript. Deep forest may report both nations only after permitted selection data is available, without adding a national border inside it.

Place policy is (non-hidden AND district lit) OR exact place visited; hidden places always require visit. Trail comes only from visited wild nodes, sorted/deduplicated into deterministic row runs. Use 1 km cells through 20000 inclusive, then 5 km deduplicated row runs with resolution metadata, including potentially large downsampled coverage in transport-bound measurement. World player location for coordinate-free interiors uses the enclosing anchor/site when canonically available; do not invent room coordinates.

Resolve accepted destinations server-side and filter before any serializer/cache. For unlit destinations round to nearest 50 km with a deterministic tie rule; send approximate flag and derive visible distance/bearing from the rounded point only. Never send exact canonical node IDs or hidden landmark positions as alternate metadata. Area bearing/distance behavior remains its separate approved contract. Validate serialized JSON recursively for leakage with synthetic secret sentinels, not only UI hiding. Reuse measured transport limits and repeat the focused actual socket test with this real assembled presenter output.

For discovery, at the existing successful movement completion capture whether the canonical destination landmark was already visited before calling unchanged record_arrival; after successful settlement, parse knowledge again and confirm the exact landmark ID is now recorded before appending discovery to that same movement narrative. A corrupt record or swallowed write failure leaves it unlit and emits no discovery. Use the existing movement transaction/commit boundary so rollback cannot emit prose. Do not modify knowledge schema/writer or introduce lit flags. Support normal grid, wilderness and gateway arrival through the shared seam; no discovery from teleports, reads or reconnect. Emit existing operational boundary events through the facade, without leaking secret content into protocol diagnostics.

## Risks / Trade-offs

Exact destination coordinates can leak through IDs, distances or unfiltered caches even when the visible x/y is rounded. First-arrival detection after record_arrival alone loses the pre-visit fact; before commit it risks false announcements.

## Implementation verification contract

Implementation MUST run the smallest affected Evennia label, Node file, Vitest file, or managed browser class, never broad suites or CI shard commands locally. Every local test command must stay below ten minutes. Use `uv run --locked --env-file=<path> evennia test --settings test_settings.py --keepdb <focused.label>`, with `MUD_TEST_SETTINGS=1` in that env file. Pure tool tests use a focused `uv run --locked python -m unittest <module>`; client units use a single-file runner.

Register every new/moved non-browser package test module in exactly one `.github/evennia-shards.json` shard; register every new browser class/method in `.github/browser-shards.json`. Keep synthetic mechanism fixtures independent of production lore. Production content integrity tests need a first-line `Data-contract test: <reason>` and matching `tools/test_data_freeze.json` entry.

Use `uv run --locked python -m tools.spec_traceability --repo-root <equivalent-root> list` to obtain canonical IDs, never guess them. Before sync, create a disposable ordinary directory containing the complete current implementation, tests, manifests and tooling (not a git worktree), and apply all prerequisite/current spec deltas to its copied main specs in dependency order. Keep literal intended `covers_requirement` annotations in the actual implementation; they may be unknown to unsynced root specs. Run `check` with `--repo-root <equivalent-root>` and run the copied `tools.contract_gate` from that complete equivalent directory before handoff. Do not demand a root contract-gate pass before specs are synced. After sync, run the normal root traceability check and contract gate with unchanged annotations. Associate only substantive discoverable Python assertions; a focused Python wrapper that actually executes JS/browser assertions is valid, source-presence checks are not. CI alone runs complete evidence verification.

All changed server, movement and panel logging uses named imports from `world.observability`, stable snake_case events and contextual business identifiers. Changed cross-system/I/O boundaries emit the applicable catalog event; exception branches re-raise, log through the facade with `exc=`, or carry a reasoned lint exemption. Patch the caller's log binding in tests. Run the observability lint with focused tests when a logging path changes. Never add freeze-list entries.

Before implementation handoff run strict validation and the copied contract gate from the complete equivalent merged-spec directory described above. After main-spec sync run `uv run --locked python -m tools.contract_gate` at the actual root. Update existing behavior documentation; no unrelated features, migrations or compatibility aliases. Proposal creation does not run implementation tests.
