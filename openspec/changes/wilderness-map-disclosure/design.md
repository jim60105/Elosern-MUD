# Design

## Context

Observed owners and nearby test targets: web/webclient/presentation/local_map/wilderness.py _wilderness_layer; exploration.py _move_rows and mirrored exploration validator; shared move-entry projection and dialogue exit consumers; ExitCompass target model; local-map/exploration/compass tests and frozen protocol audits.

## Goals / Non-Goals

Filter eager wilderness map facts while preserving opaque directional movement. Keep the named slice complete and independently runnable after prerequisites; dependent behavior is owned elsewhere.

## Decisions

This is the B2 anti-peek remediation prerequisite, within sub-project1 rules/protocol scope. Existing eager local_map serializes every legal wilderness neighbour, terrain labels and gateway metadata; a radius0 forest night now makes some neighbours genuinely unknown. Filter before building any node/edge/label/gateway metadata using ground-reveal's is_revealed and hidden-entry actual-visit predicate. Keep the local_map version1 field schema and its bounded adjacent/remembered-boundary scope, but wilderness adjacency alone no longer grants knowledge. Only revealed legal neighbours and actually visited remembered boundaries are emitted. Current cell remains current. Revealed memory can support navigation facts without live entities. Hidden gateway names/identities require actual visit, even if district lit; otherwise omit gateway node metadata. Non-hidden settlement gateways require corresponding cell/entry reveal. No local_map record is invented for unknown destinations.

Preserve movement without disclosing targets. Add one server disclosure projection used by every serialized wilderness move-row source, including exploration and independent dialogue exits. A real legal Exit still provides opaque exit_ref, enabled state and generic compass-direction label; unknown or visit-gated destination is null, with no canonical target identity, coordinates, terrain, settlement name or gateway facts. Known targets retain canonical IDs. Never substitute current_node as a fake destination. Existing explore.move already submits only exit_ref/current_node, so actual traversal admission stays unchanged. The disclosure of directional availability/lock status is an existing control fact, not an unknown terrain record. Do not populate disabled_reason with target names or terrain facts.

Bump exploration panel schema5->6 on Python/JS and associated frozen consumers; retain exact move-row keys, with destination nullable only for directional wilderness rows whose target is withheld. Other layer destinations remain canonical non-null. For separate dialogue exit representation use the same nullable destination discriminator at its existing row schema owner, bump that owner only if it is versioned/exact and cannot already carry absence; do not leak an alternate copy. This is a payload/value adaptation of existing controls, not a layout or walking-queue feature. Keep all12-row/byte bounds. ExitCompass target resolver must accept a null target ID, derive bearing solely from server generic direction word, retain exitRef action and avoid minimap highlight when no destination exists. Local map can contain only current, so missing neighbour metadata must not disable otherwise enabled opaque directions. Cross-layer/hidden names never become anonymous fallback labels.

Tests inspect a complete eager publication, local map, exploration and dialogue exit rows, then later area map using the same unlit/unvisited synthetic forest-night case. Unknown terrain/coordinates/target IDs/names absent in every branch, yet executing opaque control reaches the canonical real cell and records arrival. Add hidden-gateway and revealed ordinary-neighbour controls. All original local-map/gateway/compass scenarios remain for disclosed destinations; changed preconditions explicitly say revealed/permitted. Retain grid/instance/interior behavior. Update existing map/synchronization protocol documentation and frozen audit fixtures. No new player command, travel HUD, paces, client queue or camping.

## Dependency contracts

- [wilderness-ground-reveal](../wilderness-ground-reveal/design.md) must land first.

## Planning and implementation boundaries

This artifact set covers sub-project1 only. Read the [blueprint](../../../docs/superpowers/specs/2026-10-30-wilderness-travel-mode-blueprint-design.md) §7.1, the [detailed sight design](../../../docs/superpowers/specs/2026-10-30-wilderness-sight-and-fog-reveal-design.md) and [engine architecture](../../../docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md) §§2/3/6.5/10. Preserve single-writer ownership and server exploration mode. No travel HUD/input queue/log/tint, camping/dream/art changes, authored geography/landmark-content changes, new roads, migrations or compatibility paths. Generated elevation and the approved sight rulebook are explicitly allowed.

Implementation will be performed by gpt-luna-level workers. Follow the named owners and exact contracts; read each prerequisite design first. Do not invent downstream stubs or leave unresolved behavior to a worker. Each change is capped at one workday including focused evidence/docs. Independent roots can run concurrently only with one owner integrating shared test-manifest/doc edits.

## Evidence and requirement shape

Use synthetic documents, policies and parties with independent expected results. Do not pin shipped data, text, markup or counts. Appearance/wording judgments are human-reviewed against the approved detailed design, outside SHALL requirements. For each requirement implement a discoverable test named from its mechanism, covering every delta scenario and both raising/non-raising cases. Test paths are named in Context. New package-local server tests join exactly one shard in .github/evennia-shards.json; avoid new modules when an existing test file is sufficient.

Requirement IDs must come from tools.spec_traceability list on the equivalent merged spec tree, never hand-composed. Before sync associate only the nearest current canonical requirement and report the temporary mapping per docs/development/spec-test-traceability.md. Sync remounts to the generated IDs with no uncovered requirements or waiver. Modified requirements retain identity except an explicit RENAMED window title. Mechanism tests must exist before that sync.

### Current canonical association and planned remount

`tools.spec_traceability list` on the main tree at `master` `aab865ac` reports no
`wilderness-map-disclosure::` requirements, because the capability exists only
as a delta; the archive-time sync generates that capability's IDs. Until then
the mechanism tests carry the nearest modified requirement only:

| Delta requirement | Current canonical association | Tests |
| --- | --- | --- |
| All wilderness map publishers enforce reveal boundaries | `webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel`; `webclient-exploration-menu::exploration-move-rows-advertise-canonical-destinations` | `world.rules.tests.test_ground_reveal.WildernessDisclosurePolicyTests`; `test_local_map.test_wilderness.LocalMapWildernessDisclosureTests`; `test_exploration_panel.test_wilderness_and_npc_titles.WildernessExplorationPresenterTests` |
| Opaque directional controls remain executable | `webclient-exploration-menu::explore-move-traverses-a-re-resolved-exit-through-the-shared-movement-path`; `webclient-exit-compass::each-exploration-exit-resolves-to-exactly-one-angled-or-portal-target` | `test_wilderness_and_npc_titles.WildernessExplorationPresenterTests.test_a_withheld_direction_executes_through_the_production_move_seam`; `web/webclient-app/tests/action/compass_model.test.js` |
| local_map is a read-only version-1 panel | `webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel` (retained) | `test_local_map.test_wilderness`, `test_local_map.test_schema` |
| Visibility states | `webclient-local-map::visibility-states-are-current-visible-unvisited-visible-visited-and-remembered` (retained) | `test_local_map.test_wilderness` |
| Place names only where informative | `webclient-local-map::the-map-surfaces-state-a-place-name-only-where-it-adds-information` (retained) | `test_local_map.test_wilderness`, `test_local_map.test_grid_gateways` |
| Wilderness minimap nodes are actionable | `webclient-local-map::wilderness-minimap-nodes-are-actionable` (retained) | `test_local_map.test_wilderness` |
| Minimap gate nodes match traversal | `webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions` (retained) | `test_local_map.test_gateway_resolution`, `test_local_map.test_per_gate_footprint`, `test_local_map.test_wilderness` |
| Exploration panel schema 6 | `webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-4-presentation-panel` (retained) | `test_exploration_panel.test_schema`, `web/static/webclient/js/tests/protocol_exploration_a.test.js` |
| Aimed highlight, compass degradation, dialogue exits list | `webclient-exit-compass::the-aimed-destination-lights-on-the-minimap-and-motion-respects-the-motion-level`; `webclient-exit-compass::the-compass-degrades-honestly`; `webclient-exit-compass::the-dialogue-screen-s-exits-list-stays-independent-of-the-exploration-root` (retained) | `web/webclient-app/tests/action/compass_model.test.js`, `web/static/webclient/js/tests/exploration_menu.test.js` |

No coverage waiver is claimed and no delta requirement ID is hand-attached;
those annotations are remounted by the sync that follows archive, once
`tools.spec_traceability list` reports the new identifiers.

### Scope note: on-demand area output

This change owns the shared disclosure policy and the eager publications named
in Impact: the `local_map` wilderness layer, the exploration `move` rows and the
dialogue exit rows that reuse them. The on-demand `area_map` wilderness window
keeps its current contract here; `wilderness-area-map-reveal` (blueprint change
9) owns its unknown-run rewrite and consumes `WildernessDisclosure.reveals`
directly, so the same predicate governs it without a second decision. Task 1.4's
inspection therefore covers every publication this change owns.

## Risks / Trade-offs

[Read side effects] -> Pure projections and object/Attribute/clock snapshots in integration tests. [Shared files] -> Serialize shard-manifest, schema and documentation changes even when roots are independent. [Data echo tests] -> Assert mechanics on synthetic fixtures and treat visual review separately. No new permanent lighting or walking state is allowed.

## Rollout / Rollback

Apply only after dependencies land. Development database reset is needed for the schema2 cutover; never automate deleting the user's database. No migration or dual decoder is added. Rollback is source reversal and a deliberate development reset where applicable. This proposal task does not start apply, sync or archive.
