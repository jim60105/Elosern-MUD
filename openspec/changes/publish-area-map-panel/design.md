# Design

## Context

Source of truth: `docs/superpowers/specs/2026-10-22-world-map-drawer-design.md`, introduced by approved commit `9a9200b45c406a3d28ec15b27fa4cf04380151ba`, and parent architecture `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`. §9 row 4 panel sub-change, split after resolve-map-quest-destinations; 3h graph adapters, 2h wilderness/action integration and 3h validators/tests/docs. See proposal.md for motivation and prerequisites. The prototype is a layout/interaction reference only; its old river, forest and political geometry must never become runtime data.

## Goals / Non-Goals

Implement only the assigned slice described below. No elevation, travel automation, new quests, shipping mechanics, compatibility layer or data migration. Existing canonical identities, knowledge ownership and deterministic offline play remain intact.

## Decisions

Consume the exact version-1 area schema, strict Python/JS validators and epoch-safe normalized storage from define-map-panel-protocol; do not invent another wire form or register duplicate validators. Build grid data from the sparse settlement graph, not rooms spawned on demand. Filter visits to current map/z identity. Traverse only the current interior/instance room graph, never through return exits into unrelated buildings; cross-map exits remain gateway/bearing references. For all graph layers collect known = visited union adjacent(visited), then roads with both endpoints known and at least one visited. Keep instance/interior x/y absent and preserve the radial-layout path.

Use existing local-map canonical movement/gateway resolution, not its two-hop/64-node clipping or visibility names. The exact gateway value is null or {leads_to}; all action descriptors remain opaque adjacent facts. Wilderness uses the 15×15 window, valid ground and true gateway replacement semantics. Current district name is explicitly approved area metadata; this does not authorize copying it into unlit world districts.

map.view begins with the exact area payload {scope:area}; publish-world-map-panel adds world to the same exact scope union, with no legacy validator path. Use the upstream exact on-demand policy: eager snapshots omit map bodies, same-epoch refresh retains separately delivered complete maps and new epochs clear both. Only map.view executes/publishes this presenter; no snapshot-semantic alternatives remain here. Do not persist drawer-open state or push maps from movement hooks. The final drawer change owns re-request behavior.

Measure whole visited graphs and the 225-cell wilderness window, select finite area-specific logical byte/collection limits and publish without truncating required topology. This change owns adequate area bounds and invokes the already-completed shared part codec from define-map-panel-protocol whenever existing frame limits would be exceeded; it never depends on later world transport. Existing local_map validators retain their own ceilings. The world scope is not implemented as a no-op stub in this slice.

## Risks / Trade-offs

Generic full_snapshot currently executes every registered presenter. Merely registering a costly panel would violate §5.1; the on-demand publication policy and store semantics must ship here. More than 128 nodes or 64 KB may require bounded encoding/transport support rather than silent truncation.

## Implementation verification contract

Implementation MUST run the smallest affected Evennia label, Node file, Vitest file, or managed browser class, never broad suites or CI shard commands locally. Every local test command must stay below ten minutes. Use `uv run --locked --env-file=<path> evennia test --settings test_settings.py --keepdb <focused.label>`, with `MUD_TEST_SETTINGS=1` in that env file. Pure tool tests use a focused `uv run --locked python -m unittest <module>`; client units use a single-file runner.

Register every new/moved non-browser package test module in exactly one `.github/evennia-shards.json` shard; register every new browser class/method in `.github/browser-shards.json`. Keep synthetic mechanism fixtures independent of production lore. Production content integrity tests need a first-line `Data-contract test: <reason>` and matching `tools/test_data_freeze.json` entry.

Use `uv run --locked python -m tools.spec_traceability --repo-root <equivalent-root> list` to obtain canonical IDs, never guess them. Before sync, create a disposable ordinary directory containing the complete current implementation, tests, manifests and tooling (not a git worktree), and apply all prerequisite/current spec deltas to its copied main specs in dependency order. Keep literal intended `covers_requirement` annotations in the actual implementation; they may be unknown to unsynced root specs. Run `check` with `--repo-root <equivalent-root>` and run the copied `tools.contract_gate` from that complete equivalent directory before handoff. Do not demand a root contract-gate pass before specs are synced. After sync, run the normal root traceability check and contract gate with unchanged annotations. Associate only substantive discoverable Python assertions; a focused Python wrapper that actually executes JS/browser assertions is valid, source-presence checks are not. CI alone runs complete evidence verification.

All changed server, movement and panel logging uses named imports from `world.observability`, stable snake_case events and contextual business identifiers. Changed cross-system/I/O boundaries emit the applicable catalog event; exception branches re-raise, log through the facade with `exc=`, or carry a reasoned lint exemption. Patch the caller's log binding in tests. Run the observability lint with focused tests when a logging path changes. Never add freeze-list entries.

Before implementation handoff run strict validation and the copied contract gate from the complete equivalent merged-spec directory described above. After main-spec sync run `uv run --locked python -m tools.contract_gate` at the actual root. Update existing behavior documentation; no unrelated features, migrations or compatibility aliases. Proposal creation does not run implementation tests.
