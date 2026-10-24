# Design

## Context

`enter_sleep` commits one posture at zero time, `SleepEntry` is transient, `begin_sleep` reconstructs a plan on the next request and `continue_sleep` wakes only `entry.member`. `fatigue.predict_interval` wakes forced sleepers at 72000 units but treats voluntary full reserve as saturation. `mental_time._offset_seconds` has no voluntary wake boundary. These observed sources explain passive owner saturation without wake; the supplied live-save evidence is diagnostic only and must remain untouched.

The engine design's single deterministic writer and player-driven clock remain authoritative. `party-time-settlement` keeps mental scope separate from narrower resource scopes. Existing clock snapshots, practice stage and possession ownership are reused.

## Goals / Non-Goals

**Goals:** establish the durable per-body contract consumed by control/dream presentation; independently complete sleepers through real time; provide explicit single/party duration/recovery operations within a workday-sized rules change.

**Non-Goals:** contextual modal behavior, automatic owner-target continuation and dream association belong to the dependent change. No new posture enum, combat-round simulation, migration, save repair, general sleep planner or UI redesign.

## Decisions

### One body-owned accepted receipt

Persist a bounded receipt on the body's existing Evennia Attribute surface, owned by time-skip rules. Use plain validated serializable values, never object references or process-only state. The active receipt contains `sleep_id`, authenticated `owner_id`, `body_id`, `kind` (voluntary/forced), `mode` (duration/recovery/forced-threshold), `entry_tick`, accepted `target_tick` or declared recovery target with planned boundary, `limit_tick`, `settled_through_tick`, `revision`, and lifecycle state (`sleeping`, `interrupted`, `completed`). Keep the latest completion and interval operation identity/result for duplicate response handling. Retain bounded latest state, without an unbounded per-second journal.

The sleep ID identifies the accepted posture episode; interval operation IDs identify clock commits within it. The authoritative clock/operation replay seam records the latest committed interval result transactionally. Replaying a known ID returns that result; an older/stale revision rejects with current state and never advances. Concurrent commands lock the owner/body records in stable ID order, re-read posture and receipt, and compare expected revisions before mutation. Complete receipts cannot become active again. A fresh sleep request on an active receipt rejects replacement and exposes `sleep continue`.

A voluntary entry creates the receipt in the same transaction as posture/projection. Forced depletion creates a threshold receipt from its actual committed transition, without invoking voluntary safety or granting a skip. Forced targets stay at the existing threshold. Existing fixture/nonphysiological bodies receive no invented physiology. Absence of receipt on an already-voluntary persisted body fails closed with a stable diagnostic, without silently refilling, waking or migrating it. The supplied live save requires no repair in this assignment.

### Exact target modes

Duration uses the existing parser, positive whole seconds and configured cap. Its deadline is `entry_tick + accepted_seconds`; full reserve or gauges never shortens it. Default and `until-recovered` declare full HP/MP/SP plus full mental reserve using the existing regen target calculation, with maximum allowed elapsed segment recorded at entry. The initial next target boundary is the maximum of those times-to-full; forced mode uses 72000 units. Never use reserve saturation alone as voluntary completion.

An already-met recovery target reconciles to awake in the entry transaction with zero elapsed time and no claim of completed elapsed sleep. A positive duration can remain sleeping even with all gauges full. If full recovery exceeds the existing cap, the bounded segment ends awake at its accepted limit and reports incomplete full recovery; this preserves the existing maximum without infinite continuation or a false full-restoration claim.

For ordinary expected recovery, actual gauges/reserve satisfy the declared target at the planned boundary. If an accepted external effect changes recovery needs, reevaluate the next recovery boundary against the same declared full target and remaining accepted cap; never extend the cap or replace the sleep ID. Death/deletion/defeat cancels physiological completion under existing rules and grants no revival.

### Reconcile all settled sleepers without repuppeting

Integrate receipt boundary lookup with mental-time planning and clock settlement. Every applicable advance reads all living in-scope sleeper plans, including unselected owners. At a voluntary target boundary reconcile posture/projection and receipt completion in the owning transaction; emit one post-commit wake notification. No possession, puppet, commander, combat draft or binding write belongs to this reconciliation.

Interruptible ordinary waits stop at the first real wake/depletion/interaction boundary as before. A different body's explicit sleep continuation stops at that boundary without falsely waking its selected body. An indivisible action keeps its accepted effects/full duration atomic; subdivide only physiology accounting at a pre-existing voluntary deadline, so awake remainder consumes the ordinary activity rate and sleeping remainder gains no practice. Do not retroactively turn an awake collapse inside an indivisible interval into recovery. Preserve the existing terminal-combat activity policy; no natural live-round wake or extra combat advance.

Practice eligibility is derived per actual awake/sleep interval. Preserve a sleeping body's standing booking. Reuse existing whole-hour study writer for later eligible awake time, without granting an entire mixed interval as awake practice or resetting unrelated gauges. Keep existing non-mental scopes unchanged.

### Explicit all-party operation and transports

Select the canonical ordered present effective roster anchored at the acting room, including the owner. Validate membership, living/physiology, co-location, per-body state and shared skip safety before writes. Remote effective companions remain untouched. Existing voluntary plans and forced receipts retain their target/identity. Every selected awake physiological body receives a new voluntary plan in one transaction. If one selected awake member is otherwise unable to accept voluntary sleep, reject the whole operation with its reason, rather than silently omit it.

`enter_party_sleep` (proposed rules seam) does no automatic possession release or elapsed advance. A control consumer may combine entry and verified release in an outer compensated unit. Direct `sleep all` requests can enter all bodies then return the resulting nonacting recovery/handoff outcome; the dependent consumer adds dream/automatic continuation. A retry with the same operation identity changes nothing twice.

Text grammar is `sleep [<duration>|until-recovered]`, `sleep all [<duration>|until-recovered]` and `sleep continue`; keep `睡眠` alias. Browser `explore.wait` sleep payload uses `sleep: true`, `sleep_scope: self|party`, `sleep_mode: duration|recovery`, and `seconds` only in duration mode, plus existing action/operation envelope identity. Missing mode defaults to recovery only for the existing canonical recovery request, with no deprecated route or alternative writer. Reject contradictory fields. The dependent change replaces the old combined `sleep dream` surface with accepted-view dream choices. Both command documents must describe availability while the current body sleeps.

### Atomicity and consumer boundary

Extend the existing advance snapshot registry with receipt and target surfaces, projection caches and idempotency result state. Entry snapshots every selected body's fatigue/projection/receipt surfaces. Fault after any posture, resource, clock or completion write restores all touched persisted Attributes and in-process caches. Post-commit events never claim a rolled-back transition. Existing control writers remain the sole owners of sessions, locks and cmdsets.

Expose a read-only sleep outcome with owner/body IDs, sleep ID/revision, target, actual committed prefix, completed/interrupted status and current control-independent availability. Control/dream consumers cannot manufacture elapsed results, call `_wake_voluntary` directly or replace a plan.

## Approved Design Amendments

During apply, amend `docs/superpowers/specs/2026-10-21-party-fatigue-and-sleep-design.md` header and §16 stale implementation status to distinguish the archived original implementation from these proposed corrections. Amend §4.2/§9.1 to allow the explicit all-party operation and declared duration/recovery targets, §8.4 for passive voluntary boundaries, and §11/§12 for durable receipt/snapshot ownership. Amend §8.5 narrowly for a pre-existing voluntary wake deadline inside an indivisible action, preserving atomic full effects and completion-time collapse for previously awake bodies. Retain all combat exclusions. This proposal commit itself stays entirely inside its change directory.

## Risks / Trade-offs

- Attribute/cache rollback gaps -> extend the existing registry and inject late multi-body faults, including reload assertions.
- Mixed interval accounting -> independently known duration and practice examples, preserving indivisible and terminal boundaries.
- Missing old receipt -> fail closed; pre-release policy prohibits migration/shim or live-save patching.

## Deployment and Rollback

Apply with **gpt-luna**, branch `feat/fix-body-sleep-lifecycle`, worktree `.worktrees/fix-body-sleep-lifecycle`. Deploy as a clean pre-release cutover with no data migration. Revert implementation as one coherent change if necessary; do not introduce an old/new dual writer. Run only focused checks named in tasks; full CI and complete browser evidence remain CI-owned.

## Batch Review Disposition

The single blocking batch critique identified a retained exact-field transport contract and an omitted §8.5 design amendment. The follow-up adds the original explore.wait requirement delta with explicit duration-sleep grammar, malformed-payload scenarios and adapter tasks, and names the narrow indivisible-action amendment. No implementation or verification evidence is claimed by this planning correction.
