# Design

## Context

Observed owners and nearby test targets: map_knowledge.py record_arrival; typeclasses/exits.py after_successful_movement; movement_settlement.py MovementSnapshot/settle_movement; time_skip.py advance_wait and sleep_control.py; clock snapshot/transaction; new tests/test_ground_reveal.py and existing movement/sleep tests.

## Goals / Non-Goals

Record maximum settled sight and derive permanent reveal without read writes. Keep the named slice complete and independently runnable after prerequisites; dependent behavior is owned elsewhere.

## Decisions

Add sole-writer record_ground_observation(character,cell,tick,radius) in map_knowledge.py. record_arrival uses ground_radius at actual arrival end tick, preserves first tick, advances last tick, sight=max(old,radius). PlayerCharacter owns knowledge. Under possession reuse existing authorized PlayerCharacter/commander knowledge seam and traversed cell; never create companion NPC history. Non-wilderness arrivals unchanged.

Observe exactly once at the final cell/time of a positive committed explicit skip: wait/rest, voluntary self/party sleep and forced-sleep continuation. Use actual elapsed seconds after truncation. Integrate inside the shared clock/skip atomic transaction before durable commit, registering knowledge Attribute in snapshot/compensation. advance_wait currently calls clock.advance before constructing its result, so a post-return web/text adapter hook is invalid. Add a narrow shared deterministic skip completion callback inside the owning atomic boundary or reuse an existing sleep/clock completion owner. Fault after knowledge write must restore database AND Attribute caches. Existing logged/no-throw knowledge-write policy stays; observation failure cannot independently break successful movement. No intermediate phase observations, normal action ticks, zero/replayed/refused skip, read, reconnect or teleport observations. Future camping uses this same skip owner; no camp API/UI here.

revealed_in_bounds and is_revealed are pure. First test valid exact-landmark lit district ownership; otherwise inspect visit chunks intersecting query expanded8 and union stored discs, cropped to query/frame. No persistent seen-cell bitmap/lighting record. Revealed blocked/water/footprint cells stay visible yet unwalkable. Hidden points/elven villages still need exact has_visited. Live entities remain separate.

Avoid full parse_knowledge scan for window lighting: exact membership checks over finite district landmark IDs. A corrupt selected chunk is diagnosed/preserved and only independently valid lit membership can reveal. An invalid envelope/schema establishes no trusted lit set, so reveal is empty. This resolves lit fallback without inventing a second source of truth. Update arrival-seam requirement to distinguish record_arrival from skip observation; preserve its original blocked/read/teleport/pruning scenarios and add final-skip evidence. Document reveal API/corruption/ownership.

## Dependency contracts

- [wilderness-knowledge-chunks](../wilderness-knowledge-chunks/design.md) must land first.
- [wilderness-sight-rules](../wilderness-sight-rules/design.md) must land first.

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
