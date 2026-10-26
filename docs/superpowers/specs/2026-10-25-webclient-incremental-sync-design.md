# WebClient Incremental Synchronization and Event-Driven Alignment

**Date:** 2026-10-25
**Status:** Approved design; complete OpenSpec proposals prepared. Implementation not started by this design workflow.
**Scope:** Per-session presentation publication, browser reduction, bounded multipart delivery, and functional verification. No implementation is included in this document commit.

## 1. Purpose and authority

Reduce repeated transmission of unchanged presentation data while retaining atomic, authoritative browser state. Keep the existing generic per-message byte ceiling. A logical publication may exceed that ceiling through bounded multipart delivery.

The architectural source of truth remains `2026-07-29-ai-mud-engine-design.md`. Presenters remain read-only, and synchronization never writes game state. This design replaces the full-snapshot fallback and revision-admission decisions described in `2026-08-02-webclient-oob-foundation-design.md` where explicitly stated below. It preserves the committed-state and declarative-menu invariants of `2026-09-02-declarative-frame-refresh-design.md`.

Existing main OpenSpec requirements remain the runtime contract until corresponding changes are proposed, implemented, and synchronized. This document records an approved target design, not a claim that the runtime has changed.

## 2. Existing behavior and failure

`web/webclient/actions/dispatcher.py` publishes affected-panel updates when an adapter declares a nonempty valid `affected_panels` collection. Missing or empty declarations, stale results, and errors can fall back to a full snapshot. A declaration selects candidate panels; it does not establish that their contents changed.

`web/webclient/presentation/coordinator.py` checks and sends a full eager snapshot as one envelope. Its aggregate canonical JSON can exceed the generic 65,536-byte limit even when individual panels satisfy their own bounds.

The browser reducer in `web/static/webclient/js/elosern/protocol/store.js` replaces named panels on updates and clears the eager panel store on snapshots. Current newer-revision admission alone does not establish that a delta's required baseline is present. Existing map assembly demonstrates deferred adoption, but only for its specialized map path.

The reducer also clones the complete presentation for subscriber notifications. Reducing network payload alone would leave that repeated copying intact.

## 3. Decisions and alternatives

### 3.1 Selected: candidate-panel content comparison

Render the candidate panels and compare their JSON-compatible values against the session's last successfully published presentation baseline. Transmit complete replacements only for changed panels. Dictionary key order does not constitute a change; list order does. Use a JSON-type-aware comparison so Python equality cannot equate booleans with numbers. Do not derive equality by sorting and serializing entire presentations.

Known affected-panel declarations limit the candidate set. When the affected scope is unknown, render all eager panels and compare them, but transmit only changes. This preserves conservative recomputation without requiring conservative retransmission.

Correct candidate coverage remains necessary. A skipped dependency can leave a panel stale until alignment; periodic alignment does not excuse an incorrect declaration. Changes to candidate selection must preserve coupled panels and current presenter dependencies.

### 3.2 Rejected: content hashes as ordinary change detection

Computing a content digest still requires visiting the candidate contents and normally adds canonical serialization plus hashing. This design has no content-addressed storage requirement that would justify those costs.

### 3.3 Rejected: world-wide mutation counters

Source-level counters can make invalidation inexpensive but require complete dependency coverage across mutations, viewer-specific presentation, and derived time-sensitive data. Introducing that infrastructure is outside this change. Presentation revisions are sequencing counters, not source mutation counters.

## 4. Components and ownership

### Presentation comparison and baseline

The coordinator owns one bounded, ephemeral baseline per transport-and-puppet presentation sequence. It contains eager panel values and common presentation metadata. It is never persisted to character attributes. Baseline values must be owned immutable snapshots or otherwise isolated from future mutation; comparing two aliases of a mutable presenter result is invalid.

The comparator accepts validated old and new panel values and returns equality. It does not access the database or decide affected scope. A publication planner constructs replacements, explicit removals, metadata, and the delivery frames before publication begins.

### Publication coordinator

The existing coordinator owns sequence identity, monotonic revisions, publication ordering, and the baseline. All publication paths use the same planning and serialization boundary, including graphical actions, text-command settlement, explicit synchronization, and asynchronous pushes. No caller bypasses that owner to maintain a second baseline.

### Bounded delivery assembly

A transport codec delivers a logical snapshot or delta intact when it fits, otherwise as bounded parts. Its job is delivery and assembly, not game-state calculation or panel rendering. General presentation assembly must coexist with the specialized map protocol without changing map lifecycle semantics.

### Browser reducer and view

The reducer validates sequence and baseline, assembles complete publications, validates logical contents, and commits once. Subscribers receive only committed states. View consumers retain unchanged panel references and cannot mutate shared committed payloads.

## 5. Logical publication contract

A publication identifies its protocol version, presentation epoch, target revision, and publication kind. A delta additionally identifies the exact base revision. Common metadata includes mode, layout version, and server time.

A delta contains complete replacements for changed eager panels and an explicit collection of removed panel names. An omitted panel is unchanged. An unavailable panel is a replacement with the existing unavailable schema, not an implicit deletion. A panel cannot be both replaced and removed in one publication. Unknown names and malformed payloads are rejected before commit.

A complete snapshot contains the authoritative eager panel set. Its adoption replaces that set, including removal of old panels omitted from the new snapshot. Snapshot adoption establishes a fresh comparison baseline without requiring the receiver to possess its predecessor revision.

Metadata changes can produce a delta with no panel replacements or removals. Update validation must permit that case. If neither panels nor metadata changed, no presentation revision is consumed and no presentation message is sent. An associated action result references the current published revision.

Use the existing bounded, unpredictable epoch identity for one transport-and-puppet sequence and the existing JS-safe integer revision counter. Allocate a new epoch on reconnect or puppet replacement. Do not hash presentation contents to calculate revision identifiers.

## 6. Normal publication flow

1. Complete the deterministic action and construct the presentation context at the existing serialized publication boundary.
2. Decide whether this publication requires full alignment. If so, follow section 8 and skip delta comparison.
3. Render the declared candidate set, including required companions. If scope is unknown, render every eager panel. Preserve current dialogue/mode coupling and action-local presentation context such as combat round data.
4. Validate candidate payloads and compare against the published baseline. Retain unchanged baseline values, replace changed values, and include explicit removals where applicable.
5. Include current common metadata. If the resulting presentation is identical, send only any required action result at the existing revision.
6. Plan and validate every delivery frame before consuming a revision or sending the first frame. Reuse prepared serialized representations within this publication where the transport permits; do not serialize just to compare equality.
7. Publish the complete logical batch in order, then the action result referencing its target revision. Advance the baseline only after all sends return successfully. The baseline records publication, not proof of client receipt.

Normal publication does not await an extra client acknowledgment round trip. Exact-base admission and recovery handle a receiver that did not adopt a preceding publication. A partial send failure invalidates the publication baseline for further deltas; the next publication must establish a complete snapshot. Already-sent partial data is never treated as a committed browser state.

## 7. Client admission and recovery

For an active epoch, accept a delta only when its base revision exactly equals the committed revision and its target revision is newer. Reject old transport generations and retired epochs before assembly or reduction. A delta cannot establish initial state.

Validate all replacements, removals, and metadata against a staged next state. Submit that state and revision atomically, then notify subscribers once. Do not advance metadata or revision while a publication is incomplete.

If a delta has an incompatible base or a publication fails validation, preserve the last committed presentation, lock mutations against that obsolete view, and request complete synchronization. Coalesce repeated recovery requests while one is outstanding. Do not introduce historical version replay, patch composition, or an unbounded revision log.

An action result claiming a presentation revision newer than the committed state cannot complete the action as synchronized. With ordered delivery, a valid publication precedes its result; an unapplied claimed revision initiates recovery rather than silently releasing the normal mutation lock. Older action results must not roll back a newer committed presentation. Preserve existing request deduplication and uncertain-result behavior after disconnect.

A valid complete snapshot for the live sequence can repair a baseline mismatch. A stale snapshot must never replace a newer committed revision. Epoch replacement follows the existing transport/puppet rules and clears sequence-local comparison and assembly state.

## 8. Event-driven complete alignment

Complete alignment is driven by semantic events, not elapsed wall-clock time or every N actions. It freshly renders canonical eager presentation data and directly replaces that publication's delta. Never resend an old baseline as an alignment snapshot, and never send both a delta and an alignment snapshot for the same settlement.

Required baseline-establishment or recovery cases remain login/initial synchronization, reconnect, puppet change, and synchronization recovery.

The approved additional alignment checkpoints are:

- Successful movement across an area boundary, or entry into, exit from, or replacement of a dungeon/instance context.
- Combat termination, including terminal opening resolution and successful escape or other terminal outcomes.
- Completed rest, sleep, or explicit player-driven time-skip actions.

Ordinary movement inside the same area, combat entry, and nonterminal combat rounds use incremental publication. A rejected action does not qualify merely because its requested action type names a checkpoint. Sleep checkpoints occur at completed settlement, not merely when opening a sleep-choice interface.

Boundary detection must use authoritative existing map/instance identity and committed source/destination context. Do not use display labels, room-object identity alone, or merely a changed coordinate as a proxy for an area transition. This matters for wilderness rooms whose objects can be reused across positions. If a movement path cannot establish a comparable area/instance identity, choose complete alignment conservatively for that transition.

Checkpoints must work through graphical and text-command paths. Multiple qualifying events within one serialized settlement require only one final alignment publication. Asynchronous later changes remain separate ordered publications.

## 9. Multipart delivery and bounds

Keep the generic per-envelope 65,536-byte limit and existing explicitly scoped allowances. Do not raise or remove that limit to solve aggregate snapshots. Multipart applies to both snapshots and deltas, including a single oversized panel; splitting only between panels is insufficient.

Each transfer identifies its epoch, target revision, publication kind, transfer identity, ordered part index, part count, and declared total length. The base revision of a delta must remain consistent across all its parts. Encoding must obey existing per-string, list, object, and frame limits; a giant JSON string in a part is invalid even if the frame byte limit is met.

Receiver assembly is invisible to consumers. Validate headers, lengths, part consistency, and ordering; after complete assembly, decode and validate the logical publication and resulting panel state. Logical aggregate validation must not reapply the single-envelope byte ceiling to the assembled document. Existing logical schema and panel bounds remain enforced; transport fragmentation does not authorize oversized panel content.

Use these finite general-publication assembly bounds as shared server/client protocol constants:

| Resource | Limit |
|---|---|
| Logical publication size, measured as encoded UTF-8 JSON before fragmentation | 16 MiB (16,777,216 bytes) |
| Raw bytes per part | 24 KiB (24,576 bytes) |
| Base64 representation per part | At most 16 strings, each encoding at most 1,536 raw bytes into at most 2,048 characters |
| Part count | At most 683, with exact count and final-part size derived from declared total bytes |
| Live general-publication assembly | One per active transport |
| Assembly lifetime | 30 seconds from the first accepted part, never extended by later traffic |

The 16 MiB ceiling is an explicit resource policy, not a measured workload claim or a per-envelope increase. The selected part representation leaves header room within the generic frame bound and obeys the existing string limit. Count buffered general-publication data separately from the already bounded specialized map assembly; both owners must release their buffers on disconnect. A sender that cannot represent a valid publication within these finite limits reports a presentation failure rather than silently truncating data. Ordinary change detection never hashes contents or consults assembly deadlines.

The existing map schemas, scoped world-map allowance, and map-specific bounds remain authoritative for their own path. General publication assembly must have unambiguous routing distinct from map-body parts. Protocol constants and exact wire schemas are implementation-plan deliverables subject to these bounds, not permission to remove resource limits.

On missing parts, timeout, contradictory headers, decode failure, or resource overflow, discard the incomplete transfer and request complete synchronization. A failed recovery leaves presentation unavailable with mutations locked; do not automatically repeat an identical failing recovery indefinitely. A newer complete snapshot supersedes obsolete assemblies. A later delta cannot skip an incomplete predecessor and still commit. Disconnect and epoch retirement clear assembly buffers. Assembly expiry is transport recovery machinery, not a periodic alignment timer.

## 10. Browser work and local UI state

Retain unchanged committed panel references across delta commits. Replace the unconditional whole-state serialize/parse cloning in ordinary notification paths with explicit immutable ownership and changed-panel adoption. Public consumers must not obtain mutable aliases that can corrupt the reducer or server baseline. Preserve the observable snapshot isolation contract wherever consumers currently rely on it.

A complete alignment replaces authoritative data without remounting the entire application. It must not independently reset focus, open menus, local forms, or animations. Existing semantic rules still apply when mode, identity, panel availability, or service contents genuinely change; for example, existing mode-change teardown is preserved. The design does not retain local selections that have become invalid.

On-demand `area_map` and `world_map` retain their existing lifecycle. Alignment covers the existing eager snapshot set and does not force-load unopened maps. Preserve existing same-epoch map retention and epoch-reset behavior.

## 11. Functional verification

Retain deterministic tests and an actual changed-path smoke run during implementation. Cover these consumer-visible behaviors:

- A candidate that renders identical content is omitted; changed content is transmitted and replaces the correct panel without losing untouched panels.
- Equality respects JSON types, dictionary key-order independence, list order, and isolated baseline ownership.
- Unknown affected scope recomputes all eager panels but publishes only actual changes.
- Explicit removal, unavailable replacement, metadata-only updates, and completely unchanged action completion have distinct correct behavior.
- Exact-base rejection preserves the prior committed state; complete recovery restores every eager panel, including a panel whose invalidation was deliberately omitted before a checkpoint.
- Every approved checkpoint sends freshly rendered complete data instead of a delta, across graphical and text paths. Ordinary same-area movement and nonterminal combat remain incremental.
- Both normal updates and complete alignments expose one atomic committed state. Mode/dialogue and action-result revisions stay consistent.
- A logical publication above the generic frame limit succeeds through bounded parts. Missing, obsolete, contradictory, expired, or oversized transfers cannot expose a partial state or consume unbounded resources.
- Old generations, epochs, snapshots, action results, and assemblies cannot overwrite a newer committed presentation.
- Unchanged shared payloads cannot be mutated through subscribers; valid local focus/menu state survives alignment while existing semantic teardown remains intact.
- On-demand maps retain their existing delivery and retention contracts.

Run focused Python, Node, component, and affected browser scenarios under repository rules. Update relevant main-spec traceability through the normal OpenSpec implementation/archive lifecycle. Exercise a real browser action sequence for incremental updates, checkpoint alignment, oversized delivery, and forced baseline recovery. This is functional verification, not a performance benchmark.

**Explicit user decision:** Omit performance measurements, latency comparisons, benchmark gates, and browser long-task profiling. Low-cost design remains a requirement, but no measured latency or no-stutter claim is made. Functional browser verification remains in scope.

## 12. Scope and delivery

No persistent game-state schema, player command syntax, generative authority, or backward-compatibility layer is introduced. No JSON Patch engine, world-wide dirty-counter infrastructure, content-hash version scheme, historical delta replay, periodic alignment timer, or unrelated UI redesign is included.

Implementation must migrate every affected publisher, server/client validator, reducer consumer, protocol fixture, and relevant specification together. Keep protocol ownership explicit and modules focused; do not add a second presentation store or parallel publication owner. Preserve operational logging boundaries and update affected tests and documentation with the implementation.

The user subsequently selected the OpenSpec proposal workflow for implementation planning. The complete proposal set and scheduling contract are recorded below. Honor the repository's specification-driven implementation gates. Design approval and documentation edits do not authorize code implementation.

## 13. Complete OpenSpec proposal inventory

Each change lives under `openspec/changes/<change>/` and contains its proposal, technical design, delta specifications, and implementation tasks. These artifacts were prepared for **gpt-luna-level implementation workers**: shared interfaces, caller ownership, prerequisites, and functional verification are specified before apply. Performance measurements remain excluded.

The shared wire contract, source-design traceability, detailed dependency/conflict matrix, and independent-review disposition are in [the delta-contract design](../../../openspec/changes/webclient-delta-contract/design.md). Use each change's CLI status and artifact paths at apply time; this inventory does not assert that any implementation is complete.

| ID | Change | Implementation scope | Frontend surface | Direct prerequisites |
|---|---|---|---|---|
| D | [webclient-delta-contract](../../../openspec/changes/webclient-delta-contract/proposal.md) | Exact-base delta envelopes, explicit removals, metadata-only updates, staged atomic admission, and producer/fixture migration | Browser protocol JS plus Vue fixture/story updates; no visual change | None |
| B | [webclient-publication-baseline](../../../openspec/changes/webclient-publication-baseline/proposal.md) | Isolated JSON-aware candidate comparison, unchanged completion, one publication owner, always-Deferred receipts, and complete publisher cutover | None; server publication logic | D |
| P | [webclient-publication-settlements](../../../openspec/changes/webclient-publication-settlements/proposal.md) | Causal synchronous commit groups, overlapping text/graphical ingress, and all-watcher callback ordering | None; server grouping logic | B |
| C | [webclient-publication-codec](../../../openspec/changes/webclient-publication-codec/proposal.md) | Bounded server multipart encoding, shared constants, and complete preflight before sending | Browser protocol constants/exports only; sender stays server-side | B |
| A | [webclient-publication-assembly](../../../openspec/changes/webclient-publication-assembly/proposal.md) | Atomic browser assembly, transport routing, bounded buffers, supersession, and lifecycle teardown | Browser protocol/transport logic only; assembly is invisible to users | C |
| R | [webclient-sync-recovery](../../../openspec/changes/webclient-sync-recovery/proposal.md) | Coalesced full recovery, action-result revision safety, mutation locking, and bounded recovery failure | Browser state logic plus the existing view failure/lock surface; no new visual design | A |
| M | [webclient-movement-alignment](../../../openspec/changes/webclient-movement-alignment/proposal.md) | Authoritative area/instance identity and committed movement checkpoints through graphical/text paths | None; server movement identity/checkpoint logic | P |
| S | [webclient-settlement-alignment](../../../openspec/changes/webclient-settlement-alignment/proposal.md) | Terminal combat and completed rest/sleep/explicit-skip checkpoints with causal grouping | None; server settlement logic | M |
| I | [webclient-immutable-adoption](../../../openspec/changes/webclient-immutable-adoption/proposal.md) | Immutable committed reads, unchanged reference retention, detached snapshot isolation, consumer migration, and local UI preservation | Frontend UI behavior (component consumers, focus/menu/form/animation preservation); no visual redesign | R |
| F | [webclient-sync-functional-smoke](../../../openspec/changes/webclient-sync-functional-smoke/proposal.md) | Real socket/browser scenarios for incremental updates, checkpoints, oversized delivery, and forced recovery | Browser test code only; no shipped UI | S and I |

### Frontend and visual scope

No proposal adds, restyles, or relayouts UI; the frontend split is about where code changes land, not about visual design. Four changes are server-only logic: B, P, M, and S. D, C, A, and R touch browser JavaScript (protocol, transport, state, and the existing failure/lock projection) without changing rendering. I is the only change whose acceptance criteria are about frontend UI behavior: it preserves focus, open menus, unsaved forms, playback, and animations across alignment while migrating Vue consumers to committed reads, and it explicitly forbids menu redesign. F only adds browser tests. Any future visual work would need a separate design.

### Panel inventory ownership

B owns the publisher/candidate integration inventory. D owns update-envelope producer and fixture migration. I owns committed-data consumer and mutation auditing. The proposals do **not** separately promise a comprehensive audit of every panel's game-data dependencies. Do not interpret publisher coverage as proof that every affected-panel declaration is complete.

At apply time, use the actual current registered panels and caller implementations. If another feature has changed a panel, reconcile that feature's registered schema, candidate dependencies, and consumers at the relevant owner above; do not restore an obsolete inventory from these proposals. This document update does not inspect, modify, or schedule the other feature.

## 14. Parallel implementation batches

### Scheduling policy

The prerequisite graph permits two logical lanes after B: P/M/S and C/A/R/I. Shared files prevent unrestricted concurrent editing. In particular, P and C both change coordinator publication infrastructure; R also changes narrow ingress/dispatcher failure paths that overlap movement and settlement integration. The conservative batches below add scheduling barriers without changing the proposals' semantic prerequisite graph.

Finish and integrate each batch before starting the next. A parallel row means separate apply workers and worktrees, not shared working-directory edits. Do not run apply now merely because the schedule exists.

| Batch | Concurrent apply workers | Start condition | Conflict rationale |
|---|---|---|---|
| 1 | D | Existing feature integration constraints have been checked | Establish the shared protocol and migrate fixtures first |
| 2 | B | D integrated | Publication API and every publisher must agree before downstream changes |
| 3 | P | B integrated | Own causal-group infrastructure without C editing the coordinator concurrently |
| 4 | C | P integrated | Add server codec against the integrated publication/grouping API |
| 5 | **A + M** | C and P integrated | A owns browser assembly/routing; M owns server movement identity and checkpoint integration |
| 6 | R | A and M integrated | Serialize ingress/dispatcher recovery edits after M and before S |
| 7 | **S + I** | R and M integrated | S owns server combat/time settlement; I owns browser immutable adoption and consumers |
| 8 | F | S and I integrated | Verify the integrated end-to-end behavior after both lanes complete |

Maximum concurrency in this schedule is two implementation workers. A serial fallback is D, B, P, C, A, R, M, S, I, F when current edits or integration constraints make a parallel batch unsafe.

### Apply and integration ownership

For each change `<change>`, assign its apply worker the exact branch `feat/<change>` and worktree `.worktrees/<change>`. The worker reads the shared contract and its own proposal/design/specs/tasks, and implements only its assigned change. Completed prerequisites must be available in its starting baseline.

Within a parallel batch, one integration owner serializes shared-file changes, especially `.github/evennia-shards.json`, `.github/browser-shards.json`, traceability registrations, synchronization documentation, and any shared helper or fixture discovered during implementation. Coordinate ownership before edits; defer a shared-file operation to integration or serialize the affected slice rather than letting workers independently rewrite it. Every completed change must still contain its required test ownership registrations and documentation before handoff/archive.

Workers must not run builds, lints, tests, or formatters against half-finished shared edits. Run each change's prescribed focused functional verification after its owned edits are complete, and run the repository contract gate before handoff/archive. Integration must preserve the exact-base, causal-group, receipt, assembly, and immutable-consumer contracts. Passing checks in one isolated worktree does not establish that the other lane is integrated.

Before launching a parallel row, check the current owned-file sets and active changes again. Newly overlapping files require serialized ownership; the batch table is not permission to overwrite another feature. Existing source-conflict details are recorded in the shared delta-contract design. No performance measurement, profiling, benchmark gate, or runtime compatibility shim is introduced by this schedule.
