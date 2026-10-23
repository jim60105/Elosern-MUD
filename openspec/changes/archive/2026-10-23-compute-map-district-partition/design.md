# Design

## Context

Source of truth: `docs/superpowers/specs/2026-10-22-world-map-drawer-design.md`, introduced by approved commit `9a9200b45c406a3d28ec15b27fa4cf04380151ba`, and parent architecture `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`. §9 row 2 partition sub-change, split from establish-map-districts to keep deterministic routing, outline generation and recomputation testing within 8h. See proposal.md for motivation and prerequisites. The prototype is a layout/interaction reference only; its old river, forest and political geometry must never become runtime data.

## Goals / Non-Goals

Implement only the assigned slice described below. No elevation, travel automation, new quests, shipping mechanics, compatibility layer or data migration. Existing canonical identities, knowledge ownership and deterministic offline play remain intact.

## Decisions

Use a deterministic multi-source Dijkstra on 540×540 cells; order equal distances by stable district key, then coordinates. Reserve region-district cells before Voronoi propagation. Sample the existing 1 km terrain for each edge, not only 5 km endpoints, to prevent thin-river/ridge jumps; reject diagonal corner cutting and national-border crossings even at passes/fords. Preserve actual walking reachability through same-nation passes/fords. Resolve grid landmarks by their local-to-world transform and reachable gateway injection below; do not collapse them to a blocked anchor cell.

Use the exact fragment/refinement algorithm below for coast, barriers and 1km lookup; sea never acquires an owner. Every disconnected legal Voronoi component needs a seed; fail generation with actionable component coordinates rather than crossing barriers or leaving cells unowned. Regions take priority even if they span nations. Trace/smooth outlines deterministically without altering ownership, smoothing across national borders, or creating misleading gaps/overlaps. Store inputs/version fingerprint with frozen RLE data; runtime imports decode/read only.

Expose a focused `uv run --locked python -m tools.map_district_partition` generator (proposed path), and a recomputation test comparing the complete generated artifact, not only counts or a self-derived expected hash. No new service, elevation model, runtime generation or new movement graph.

### Exact ownership raster and landmark injection

The 5km raster contains 540×540 tiles, each with 25 underlying 1km cell-centre samples. Reserve region-district cells first. In each remaining tile split walkable samples into 8-connected fragments by nominal nation and legal 1km movement, rejecting diagonal corner cutting through a blocked side. A tile can have multiple fragments; never give a mixed coast/river/nation tile one indiscriminate owner. Coarse vertices are these fragments. Edges join fragments in adjacent raster tiles only when a legal 1km boundary transition exists, charging 1 for a cardinal tile step or sqrt(2) for diagonal tile steps; travel inside one fragment has zero extra coarse cost. Resolution remains a 5km walking-distance raster while thin barriers/coast samples retain exact classification. Equal-distance assignment uses district key then coordinate order.

A wilderness seed belongs to the fragment containing its exact walkable 1km sample. A grid landmark uses its canonical settlement transform, even inside a provider-invalid footprint. Inject that seed into same-nation fragments containing the registered gateway approach cells reachable from that landmark through the real sparse grid graph. Those approaches are zero-distance sources; no path may skip a national/river/ridge partition barrier. Assign containing footprint land samples to that seed explicitly after checking no conflicting seed or border/region mismatch. A walkable source in every remaining legal component is mandatory; reject an unseeded component rather than crossing a barrier.

Walkable 1km land inherits fragment ownership. Remaining polygon-land but nonwalkable samples (ridge, river, non-seeded settlement footprint) are display ownership only: choose the nearest already-owned same-nation non-region land sample by squared centre distance, then district key/sample coordinate; never create propagation edges. Deep-forest region ownership wins first. Sea has no owner. Owned river ground never becomes walkable. Store 5km ownership runs plus exact 1km exception runs for tiles whose land samples differ, with sea distinguished. Lookup first checks polygon land, then region/exception ownership, then coarse runs. Trace outlines from exact 1km ownership; smoothing changes neither lookup nor national boundaries. Recompute both frozen layers exactly.

Miniature tests independently pin a tile split by national border, coast, thin river and ridge, a blocked inland display sample, and a footprint-contained grid landmark whose reachable approach lies in an adjacent tile. Assert exact owners and legal propagation, not only hashes/counts. Budget remains 8h: 3h fragments/Dijkstra, 2h refinements/seed injection, 1h output/lookup and 2h focused tests/docs.

## Risks / Trade-offs

Raster edge validation costs more offline but preserves one-cell barriers. The initial small registry is valid input; the next authoring slice adds the final content and regenerates using this exact tool.

## Implementation notes

- A walkable pocket enclosed on all eight sides by a claimed grid-landmark footprint (Altoria's footprint mask encloses two such cells) is nobody's walking ground. It is assigned to the footprint's district along with the footprint instead of failing as an unseeded component. Every other unseeded component still fails generation with its coordinates.
- Region-district ownership is stored in the same tile/exception layers as Voronoi ownership, so the runtime lookup is polygon land, then exception tile, then tile run, with the frozen file as its only ownership source.
- Under the corner rule, fragment connectivity equals four-connectivity of same-nation domain cells; region, footprint, blocked and other-nation cells count as blocked sides.

## Implementation verification contract

Implementation MUST run the smallest affected Evennia label, Node file, Vitest file, or managed browser class, never broad suites or CI shard commands locally. Every local test command must stay below ten minutes. Use `uv run --locked --env-file=<path> evennia test --settings test_settings.py --keepdb <focused.label>`, with `MUD_TEST_SETTINGS=1` in that env file. Pure tool tests use a focused `uv run --locked python -m unittest <module>`; client units use a single-file runner.

Register every new/moved non-browser package test module in exactly one `.github/evennia-shards.json` shard; register every new browser class/method in `.github/browser-shards.json`. Keep synthetic mechanism fixtures independent of production lore. Production content integrity tests need a first-line `Data-contract test: <reason>` and matching `tools/test_data_freeze.json` entry.

Use `uv run --locked python -m tools.spec_traceability --repo-root <equivalent-root> list` to obtain canonical IDs, never guess them. Before sync, create a disposable ordinary directory containing the complete current implementation, tests, manifests and tooling (not a git worktree), and apply all prerequisite/current spec deltas to its copied main specs in dependency order. Keep literal intended `covers_requirement` annotations in the actual implementation; they may be unknown to unsynced root specs. Run `check` with `--repo-root <equivalent-root>` and run the copied `tools.contract_gate` from that complete equivalent directory before handoff. Do not demand a root contract-gate pass before specs are synced. After sync, run the normal root traceability check and contract gate with unchanged annotations. Associate only substantive discoverable Python assertions; a focused Python wrapper that actually executes JS/browser assertions is valid, source-presence checks are not. CI alone runs complete evidence verification.

All changed server, movement and panel logging uses named imports from `world.observability`, stable snake_case events and contextual business identifiers. Changed cross-system/I/O boundaries emit the applicable catalog event; exception branches re-raise, log through the facade with `exc=`, or carry a reasoned lint exemption. Patch the caller's log binding in tests. Run the observability lint with focused tests when a logging path changes. Never add freeze-list entries.

Before implementation handoff run strict validation and the copied contract gate from the complete equivalent merged-spec directory described above. After main-spec sync run `uv run --locked python -m tools.contract_gate` at the actual root. Update existing behavior documentation; no unrelated features, migrations or compatibility aliases. Proposal creation does not run implementation tests.
