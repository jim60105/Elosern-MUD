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

## Risks / Trade-offs

[Read side effects] -> Pure projections and object/Attribute/clock snapshots in integration tests. [Shared files] -> Serialize shard-manifest, schema and documentation changes even when roots are independent. [Data echo tests] -> Assert mechanics on synthetic fixtures and treat visual review separately. No new permanent lighting or walking state is allowed.

## Rollout / Rollback

Apply only after dependencies land. Development database reset is needed for the schema2 cutover; never automate deleting the user's database. No migration or dual decoder is added. Rollback is source reversal and a deliberate development reset where applicable. This proposal task does not start apply, sync or archive.
