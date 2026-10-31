# Design

## Context

Observed owners and nearby test targets: area_map.py _wilderness_area; map_panels.py WILDERNESS_WINDOW/AREA_MAX_BYTES and mirrored JS protocol/panels/map_panels.js; map_parts codecs; lib/area_map_view.js and AreaMapView.vue; test_area_map.py/test_map_panel_protocol.py and existing Node/Vitest area-map tests.

## Goals / Non-Goals

Publish a filtered41-cell RLE window through existing map transport. Keep the named slice complete and independently runnable after prerequisites; dependent behavior is owned elsewhere.

## Decisions

Existing wilderness area generation exposes15x15 provider-valid node labels irrespective of visits. Replace that serializer with schema2 RLE. Bump AREA_MAP_SCHEMA_VERSION to2 on both ends, no v1 compatibility; other area graph shapes stay identical, world/local map schemas unchanged. Preserve common wilderness schema_version/available/layer/map_id/frame/current_node/title/district_name/cell_km/nodes/edges/quest_markers. Add exact window:{min_x,min_y,width:41,height:41}, rows, light_phase, ground_radius, entities, sightings. Origin=current-20, including negative boundary offsets. Rows are41 south-to-north arrays of adjacent runs with positive integer length summing41; equal adjacent runs merge. Out-of-frame positions are unknown.

Unknown is exactly {length,kind:'unknown'}. Revealed is exactly {length,kind:'terrain',terrain,passable,band,tier,road,ford}; canonical terrain class, boolean flags, band0..15/tier0..3. Unknown may carry no terrain, validity, identity or hidden alternate metadata. Revealed blocked/water/footprint terrain stays present with passable=false. Road=false unless existing canonical geography/pricing actually supports one; do not add roads. nodes holds exactly one sparse entry, in the existing exact node shape id/label/x/y/visibility/visited/gateway/action, per in-window cell that is current, carries an actual visit record, or is revealed with a legal action, gateway replacement or location metadata: an ordinary visited cell therefore always has its own node with visited=true, and a reveal-only cell has no node entry at all, so absence means remembered-but-not-visited and no terrain or unknown run ever states a visit. No unknown cell facts through node labels/gateways. Hidden/elven villages need actual visits even in lit terrain. Actions are current legal revealed neighbours only, with existing canonical gateway replacement/exit_ref; unknown neighbour movement remains available through the opaque directional controls that wilderness-map-disclosure owns outside this map.

Entities exact {id,cell:{x,y},kind,hostile,label}; stable nonsemantic observation token, kind hostile|npc|character, boolean hostile, label<=256 codepoints. Only current ground-disc entities serialize; remembered cells carry none. Sightings use the four-field approximate sight contract, never internal source keys/target coordinates. Caps:1681 nodes,2048 edges,32 quests,4096 entities,256 sightings, logical393216 bytes. Exceeding any bound logs and returns map_unavailable without truncation. Keep generic Python/JS list/depth/safety validators consistent with these limits. Reuse existing map/publication chunking, never increase generic frame size or push maps on movement.

Minimal existing-view cutover is necessary to keep current drawer working: decode RLE terrain into ephemeral display cells in lib/area_map_view.js, merge sparse metadata/edges, update AreaMapView only to consume this normalized form, and delete obsolete wilderness15 handling. This is not TravelMap/HUD/input redesign. Do not derive sight, eligibility, route or clock client-side. Test existing selection/adjacent move/gateway behavior and other-layer geometry. Anti-peek assertions inspect all serialized branches including quest-marker exceptions: accepted quest identity remains existing intentional disclosure, never an excuse to add cell details.

Use synthetic20000 visits, warmed presenter,20 timed samples, median<=50ms on development hardware with setup excluded; record runtime/hardware and independently assert selected-chunk parsing. Update existing protocol doc and frozen parity/audit fixtures. The old fifteen-cell requirement title is deliberately renamed to Wilderness area maps cover a revealed forty-one-cell neighbourhood, preserving its legal-neighbour and no-fabricated-node scenarios with new window bounds.

## Review dispositions and concrete evidence

N3 is adopted through the positive sparse-node emission rule above: because a node entry is required for every actually visited in-window cell and never for a reveal-only one, an ordinary visited cell and an identically rendered reveal-only cell stay distinguishable without adding a visited field to terrain runs. Add test_visited_cell_has_its_own_node_and_reveal_only_cell_has_none to test_area_map.py, plus an existing Node/Vitest area-map test asserting the decoded view keeps the visited cell's visit styling and dims the reveal-only cell; both use a synthetic window with two identical-terrain cells. The1681 node cap and the existing all-branch anti-peek assertions are unchanged.

Implementation dispositions (apply, 2026-10-31):

- Plan critique: gateway grid nodes are only published for steps from the current cell; the post-implementation critique found a gate on an unrevealed adjacent cell (radius-0 woodland night) still published its room and far side, so the step now also requires its cell to be revealed and both validators require a gateway node to stand on a revealed cell one step from the current cell; a wild node must stand on its own revealed cell. Terrain class order is sea > settlement footprint > ridge > river water > sight terrain row, with a distinct `area_map_terrain_unclassified` log for an unmapped row. Entity ids are a keyed blake2b digest under a domain-separated `SECRET_KEY` derivation and fail closed without a secret. `read_snapshot` treats a stored `None` as no record, and the terrain cache compares the terrain definition and sight policy by identity. The gate room replacing a footprint cell never hides a visited wild node (a footprint cell is never walkable). Only the observer is excluded from entities; present companions serialize as ordinary entities. The 50 ms timing assertion is opt-in (`MUD_AREA_MAP_BENCHMARK=1`) while the selected-chunk read assertion runs by default.
- Not adopted as suggested: the critique proposed publishing a hidden anchor's footprint with the underlying passability. The approved contract keeps every footprint `passable=false` (traversal refuses it and travel planning relies on it), so a hidden footprint keeps only its underlying terrain class; shipped hidden entries are point shapes and contribute no footprint.
- Performance: `world/rules/map_knowledge.py` gained `KnowledgeSnapshot`/`read_snapshot` (one envelope validation and cached selected chunks per request); `has_visited`, `visits_in_bounds` and `revealed_in_bounds` delegate to it with unchanged answers and diagnostics, pinned by a differential test against an independent plain union. Distant sightings light districts by exact landmark membership instead of parsing the whole record. Measured warmed median: 23 ms over 20 samples with 20,000 synthetic visits (Intel Core i7-13700, Linux 7.2, Python 3.13.14, SQLite test database).
- Client: the wilderness stops become 全區 (41), 周邊 (15) and 近處 (5) and the view opens on 周邊; the shared glyph-in-cell assertion is pinned up to 周邊 because the 41-cell overview intentionally draws the here-seal larger than a cell.

Requirement mapping (current canonical IDs from `tools.spec_traceability list`; planned IDs from the same tool's `parse_requirements` over an equivalent merged tree with this delta applied):

| Delta requirement | Temporary canonical association | Planned ID after sync | Mechanism tests |
| --- | --- | --- | --- |
| RENAMED/MODIFIED Wilderness area maps cover a revealed forty-one-cell neighbourhood | `webclient-area-map::wilderness-area-maps-cover-a-fifteen-cell-neighbourhood` | `webclient-area-map::wilderness-area-maps-cover-a-revealed-forty-one-cell-neighbourhood` | `test_area_map.WildernessAreaTests.test_window_is_centred_run_length_encoded_and_flags_visits`, `test_only_legal_revealed_immediate_steps_are_actionable`, `test_gateway_step_replaces_its_cell_with_the_gate_room` |
| MODIFIED Map panels use exact layer and precision discriminators | `webclient-map-panel-protocol::map-panels-use-exact-layer-and-precision-discriminators` (identity retained) | unchanged | `test_map_panel_protocol.MapSchemaParityTests.*`, Node `protocol_area_map.test.js` (rows, caps, edge window) |
| ADDED Wilderness runs disclose only revealed terrain | `webclient-area-map::wilderness-area-maps-cover-a-fifteen-cell-neighbourhood`; hidden identity also `wilderness-map-disclosure::all-wilderness-map-publishers-enforce-reveal-boundaries` | `wilderness-area-map-reveal::wilderness-runs-disclose-only-revealed-terrain` | `test_anti_peek_across_every_payload_branch`, `test_visited_cell_has_its_own_node_and_reveal_only_cell_has_none`, `test_hidden_entry_identity_requires_an_actual_visit`, parity rows cases, Vitest "keeps a visited cell's visit styling and dims an identical reveal-only cell" |
| ADDED Existing maps consume bounded atomic reveal payloads | `webclient-area-map::map-view-requests-publish-the-requested-area-without-changing-gameplay`; delivery `webclient-map-panel-protocol::map-delivery-replaces-only-complete-epoch-safe-logical-panels` | `wilderness-area-map-reveal::existing-maps-consume-bounded-atomic-reveal-payloads` | `test_the_window_reads_only_its_own_chunks_and_writes_nothing` (parts round trip), `test_oversized_collections_become_unavailable_without_truncation`, opt-in `test_warmed_window_with_twenty_thousand_visits_is_within_fifty_ms`, Node part-adoption tests over the schema-2 fixture, Vitest wilderness travel descriptor test |

No coverage waiver is used; the archive step remounts the annotations to the planned IDs.

## Dependency contracts

- [wilderness-ground-reveal](../wilderness-ground-reveal/design.md) must land first.
- [wilderness-population-view](../wilderness-population-view/design.md) must land first.
- [wilderness-map-disclosure](../wilderness-map-disclosure/design.md) must land first for the opaque directional controls this map defers to for unknown neighbours.

## Planning and implementation boundaries

This artifact set covers sub-project1 only. Read the [blueprint](../../../docs/superpowers/specs/2026-10-30-wilderness-travel-mode-blueprint-design.md) §7.1, the [detailed sight design](../../../docs/superpowers/specs/2026-10-30-wilderness-sight-and-fog-reveal-design.md) and [engine architecture](../../../docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md) §§2/3/6.5/10. Preserve single-writer ownership and server exploration mode. No travel HUD/input queue/log/tint, camping/dream/art changes, authored geography/landmark-content changes, new roads, migrations or compatibility paths. Generated elevation and the approved sight rulebook are explicitly allowed.

Implementation will be performed by gpt-luna-level workers. Follow the named owners and exact contracts; read each prerequisite design first. Do not invent downstream stubs or leave unresolved behavior to a worker. Each change is capped at one workday including focused evidence/docs. Independent roots can run concurrently only with one owner integrating shared test-manifest/doc edits.

## Evidence and requirement shape

Use synthetic documents, policies and parties with independent expected results. Do not pin shipped data, text, markup or counts. Appearance/wording judgments are human-reviewed against the approved detailed design, outside SHALL requirements. For each requirement implement a discoverable test named from its mechanism, covering every delta scenario and both raising/non-raising cases. Test paths are named in Context. New package-local server tests join exactly one shard in .github/evennia-shards.json; avoid new modules when an existing test file is sufficient.

Requirement IDs must come from tools.spec_traceability list on the equivalent merged spec tree, never hand-composed. Before sync associate only the nearest current canonical requirement and report the temporary mapping per docs/development/spec-test-traceability.md. Sync remounts to the generated IDs with no uncovered requirements or waiver. Modified requirements retain identity except an explicit RENAMED window title. Mechanism tests must exist before that sync.

## Risks / Trade-offs

[Read side effects] -> Pure projections and object/Attribute/clock snapshots in integration tests. [Shared files] -> Serialize shard-manifest, schema and documentation changes even when roots are independent. [Data echo tests] -> Assert mechanics on synthetic fixtures and treat visual review separately. No new permanent lighting or walking state is allowed.

## Rollout / Rollback

Apply only after dependencies land. Development database reset is needed for the schema2 cutover; never automate deleting the user's database. No migration or dual decoder is added. Rollback is source reversal and a deliberate development reset where applicable. This proposal task does not start apply, sync or archive.
