# Design

## Context

Observed owners and nearby test targets: map_knowledge.py record_arrival; typeclasses/exits.py after_successful_movement; movement_settlement.py MovementSnapshot/settle_movement; time_skip.py advance_wait and sleep_control.py; clock snapshot/transaction; new tests/test_ground_reveal.py and existing movement/sleep tests.

## Goals / Non-Goals

Record maximum settled sight and derive permanent reveal without read writes. Keep the named slice complete and independently runnable after prerequisites; dependent behavior is owned elsewhere.

## Decisions

Add sole-writer record_ground_observation(character,cell,tick,radius) in map_knowledge.py. record_arrival uses ground_radius at actual arrival end tick, preserves first tick, advances last tick, sight=max(old,radius). PlayerCharacter owns knowledge. Under possession reuse existing authorized PlayerCharacter/commander knowledge seam and traversed cell; never create companion NPC history. Non-wilderness arrivals unchanged.

Observe exactly once at the final cell/time of a positive committed explicit skip: wait/rest, voluntary self/party sleep and forced-sleep continuation. Use actual elapsed seconds after truncation. The concrete shared owner is WorldClock.advance's atomic block, after stages/tick persistence and before transaction exit. Add keyword-only ground_observer=None, carrying the authorized PlayerCharacter plus actual observed cell; only explicit-skip callers set it. Non-SKIP use with this parameter rejects before mutation. Add that character's map_knowledge to build_advance_snapshot_registry before entering the clock transaction, then call the map-knowledge writer at the final tick inside it. This is a narrow observation input, not a general callback/plugin facility. advance_wait and continue_sleep pass the resolved observer only for actual positive intervals, never from replay/zero/refusal paths. A post-return web/text adapter hook is invalid.

continue_sleep already owns an outer atomic block and captures build_advance_snapshot_registry/_snapshot_clock_tick around clock.advance plus receipt/disposition writes. Register the same observer knowledge surface in that outer registry as well, so a receipt write failure after inner advance restores clock, physiology and knowledge caches. continue_owner_sleep delegates separately committed boundary intervals to continue_sleep; each committed interval is an actual explicit skip and observes its own end once, with no extra top-level observation or intermediate clock-stage/phase pulses. begin_all_party_sleep enters sleep at zero elapsed time and records nothing; its later positive continuation uses the same path. Add test_skip_observer_rolls_back_with_clock_failure and test_sleep_receipt_failure_restores_ground_observation in the existing clock/sleep modules. No guarantee is added for an arbitrary external atomic wrapper after these owners return.

Fault after knowledge write inside either named owner must restore database AND Attribute caches. Existing logged/no-throw knowledge-write policy stays; observation failure cannot independently break successful movement. No normal action tick, zero/replayed/refused skip, read, reconnect or teleport observation. Future camping uses this explicit-skip observation input; no camp API/UI here.

revealed_in_bounds and is_revealed are pure. First test valid exact-landmark lit district ownership; otherwise inspect visit chunks intersecting query expanded8 and union stored discs, cropped to query/frame. No persistent seen-cell bitmap/lighting record. Revealed blocked/water/footprint cells stay visible yet unwalkable. Hidden points/elven villages still need exact has_visited. Live entities remain separate.

Avoid full parse_knowledge scan for window lighting: exact membership checks over finite district landmark IDs. A corrupt selected chunk is diagnosed/preserved and only independently valid lit membership can reveal. An invalid envelope/schema establishes no trusted lit set, so reveal is empty. This resolves lit fallback without inventing a second source of truth. Update arrival-seam requirement to distinguish record_arrival from skip observation; preserve its original blocked/read/teleport/pruning scenarios and add final-skip evidence. Document reveal API/corruption/ownership.

## Dependency contracts

## Review disposition and day boundary

B5/N4 are adopted through the named clock and continue_sleep owners above, without introducing a generic rollback journal. One-day breakdown is 1.5h arrival/max-radius tests, 2h explicit clock/skip observer and dual registry tests, 1.5h bounded union/lighting/hidden tests, 1h docs/traceability and 2h integration allowance. The mapping is this section: existing map-knowledge arrival/parser and movement-settlement-atomicity requirements before new IDs exist, plus the new observation/reveal requirements after equivalent-tree sync. Focused labels are the existing world/rules/tests/test_clock.py, test_sleep_receipt.py, test_movement_settlement.py and proposed test_ground_reveal.py.

The per-requirement association and remount plan is recorded in the
`### Temporary per-requirement mapping (pre-sync)` subsection of
`## Evidence and requirement shape`; no delta requirement ID is claimed by a
test before the equivalent-tree sync, and the maintained modified requirement
keeps its current canonical ID.

Post-implementation review disposition: the reviewer's blocking finding (a
swallowed persistence failure inside the no-throw writer could leave the
surrounding transaction unusable while the advance still returned) is fixed by
isolating `_write_knowledge` in a nested savepoint and restoring the pre-write
Attribute snapshot on failure; the corpus regression faults inside that seam
and asserts the skip commits with unchanged durable and cached knowledge. The
same review's non-blocking finding (rollback evidence only covered an absent
record) is fixed by seeding existing history and asserting both the handler
value and the raw stored row in the clock and sleep rollback tests. The
multi-interval owner-continuation suggestion is dispositioned as covered by the
delegated per-interval path: `continue_owner_sleep` adds no observation code of
its own; each committed boundary interval is the already-tested `continue_sleep`
call.

- [wilderness-knowledge-chunks](../wilderness-knowledge-chunks/design.md) must land first.
- [wilderness-sight-rules](../wilderness-sight-rules/design.md) must land first.

## Planning and implementation boundaries

This artifact set covers sub-project1 only. Read the [blueprint](../../../docs/superpowers/specs/2026-10-30-wilderness-travel-mode-blueprint-design.md) §7.1, the [detailed sight design](../../../docs/superpowers/specs/2026-10-30-wilderness-sight-and-fog-reveal-design.md) and [engine architecture](../../../docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md) §§2/3/6.5/10. Preserve single-writer ownership and server exploration mode. No travel HUD/input queue/log/tint, camping/dream/art changes, authored geography/landmark-content changes, new roads, migrations or compatibility paths. Generated elevation and the approved sight rulebook are explicitly allowed.

Implementation will be performed by gpt-luna-level workers. Follow the named owners and exact contracts; read each prerequisite design first. Do not invent downstream stubs or leave unresolved behavior to a worker. Each change is capped at one workday including focused evidence/docs. Independent roots can run concurrently only with one owner integrating shared test-manifest/doc edits.

## Evidence and requirement shape

Use synthetic documents, policies and parties with independent expected results. Do not pin shipped data, text, markup or counts. Appearance/wording judgments are human-reviewed against the approved detailed design, outside SHALL requirements. For each requirement implement a discoverable test named from its mechanism, covering every delta scenario and both raising/non-raising cases. Test paths are named in Context. New package-local server tests join exactly one shard in .github/evennia-shards.json; avoid new modules when an existing test file is sufficient.

Requirement IDs must come from tools.spec_traceability list on the equivalent merged spec tree, never hand-composed. Before sync associate only the nearest current canonical requirement and report the temporary mapping per docs/development/spec-test-traceability.md. Sync remounts to the generated IDs with no uncovered requirements or waiver. Modified requirements retain identity except an explicit RENAMED window title. Mechanism tests must exist before that sync.

### Temporary per-requirement mapping (pre-sync)

`tools.spec_traceability list` was run on this worktree's current spec tree. The
new capability's requirements do not exist there yet, so no annotation below
claims a delta ID; the sync remount must use the IDs the tool generates from the
merged tree.

| Delta requirement | Current annotation / evidence | Disposition |
| --- | --- | --- |
| `map-knowledge` MODIFIED: Arrival recording happens only at existing successful-arrival seams | `world.rules.tests.test_map_knowledge_integration` (`test_gate_entry_records_wilderness_node`, `test_wilderness_arrival_records_the_ground_radius_at_the_final_tick`, forbidden-path cases) carries the current canonical ID `map-knowledge::arrival-recording-happens-only-at-existing-successful-arrival-seams` | Identity is retained because the requirement is MODIFIED, not renamed; re-review every assertion at sync. |
| ADDED: Ground observations are monotonic and transactional | Writer/arrival evidence: `test_ground_reveal.GroundObservationWriterTests` carries `map-knowledge::map-knowledge-py-is-the-sole-writer-of-a-versioned-visited-node-record`; skip evidence: `test_ground_reveal.SkipObservationTests`, `test_clock.OuterOwnerSeamTests.test_skip_observer_rolls_back_with_clock_failure`, `test_sleep_receipt.SleepEntryLifecycleTests.test_sleep_receipt_failure_restores_ground_observation` (no new-capability annotation) | Nearest current canonical requirements are the sole-writer and advance-atomicity requirements. Mount the generated `wilderness-ground-reveal` ID after sync. |
| ADDED: Permanent reveal is a bounded read projection | `test_ground_reveal.GroundRevealProjectionTests` covers union/lit shortcut, chunk selection, hidden-plus-corrupt history, invalid envelope, frame cropping and read purity (no new-capability annotation) | No current canonical projection requirement exists; mount the generated `wilderness-ground-reveal` ID after sync. |

Every scenario in both delta specs has a discoverable mechanism test named for
its behaviour; the only annotations present are the existing canonical IDs
above, and no guessed or hand-composed ID appears in test source.

## Risks / Trade-offs

[Read side effects] -> Pure projections and object/Attribute/clock snapshots in integration tests. [Shared files] -> Serialize shard-manifest, schema and documentation changes even when roots are independent. [Data echo tests] -> Assert mechanics on synthetic fixtures and treat visual review separately. No new permanent lighting or walking state is allowed.

## Rollout / Rollback

Apply only after dependencies land. Development database reset is needed for the schema2 cutover; never automate deleting the user's database. No migration or dual decoder is added. Rollback is source reversal and a deliberate development reset where applicable. This proposal task does not start apply, sync or archive.
