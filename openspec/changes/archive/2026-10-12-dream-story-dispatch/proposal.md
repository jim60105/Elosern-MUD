# Proposal

## Why

Confirmed dreams currently save private requests without a production director scheduler. The approved `docs/superpowers/specs/2026-10-11-dream-story-dispatch-design.md` requires those requests to become validated executable arrangements with real exploration encounters, while waking play continues immediately.

## What Changes

- Persist one narrative-owned work record per confirmed request/version in the confirmation transaction and notify a server-owned background pump after commit.
- Extend the shown draft with bounded experience requirements, then run StoryDirector and ScenarioDirector with separate immutable permitted contexts and checkpointed outputs.
- Revalidate authoritative sources and atomically publish the decision, thread, beat, package and request linkage without spawning future roles or accepting commissions.
- Activate independent encounters at actual exploration, publication, reconnect, startup and declared prerequisite boundaries, before final escort/outcome evaluation.
- Route truthful spoiler-safe status and actual scene/conversation updates through existing surfaces, with offline and recovery behavior and correlated operational events.
- **BREAKING** Target fresh game-database initialization only. No old-request scanner, migration, compatibility parser or historical reconciliation is included. This proposal run executes no reset.

## Capabilities

### New Capabilities

- `dream-story-dispatch`: narrow durable work ownership, queue/claim/recovery, publication identity, status and fresh-database deployment verification.
- `story-encounter-activation`: production exploration-boundary eligibility and activation ordering consuming upstream deterministic operations.

### Modified Capabilities

Exact existing main paths were confirmed against `openspec/specs/` and the CLI inventory.

- `dream-authoring`: visible bounded experience requirements and atomic confirmed-version handoff.
- `dream-session-lifecycle`: confirmation closes the dream with durable work and immediate waking.
- `dream-sleep-surface`: asynchronous handoff and ordinary waking-play status without time charge.
- `story-director-beats`: complete request fitness, separate stage contexts and atomic current-state settlement.
- `narrative-quest-compilation`: symbolic new-role/private issuance planning and linked package publication.
- `scenario-director`: beat-scoped complete extended blueprint fitness without filler.
- `webclient-dream-stage`: display and preserve the exact requirements being confirmed.
- `webclient-dialogue-session`: committed activation refresh and real conversation acceptance consumers.
- `npc-dialogue`: dispatch/planning knowledge remains private; participant knowledge uses narrative provenance.
- `observability-logging`: confirmation, stage, publication, recovery and activation correlation.

## Impact

Apply extends `world/narrative/` authoring/models/director/quest-beat ownership, server dream composition and server start/stop, existing movement/control and reconnect boundaries, permitted context/schema/prompt contracts, quest package publication, and existing presentation consumers. Clients remain injected at server composition; AI never writes state. Tests exercise real deterministic owners with synthetic model-boundary outputs and exact shard/traceability ownership. No new dependencies or UI control panel are required.

## Non-goals

No implementation during proposal creation, unsolicited continuation scheduler, autonomous NPC framework, generic agent/retry subsystem, migration, legacy reconciliation, compatibility shim, reset execution or unrelated refactor. The upstream artifacts are referenced and remain unchanged.

## Batch:

```text
depends-on: quest-scene-encounters
depends-on: escort-rendezvous
code-conflicts: quest-scene-encounters (package publication, role activation, dialogue refresh and schema/compiler consumers); ordered implementation
code-conflicts: escort-rendezvous (extended blueprint, movement/activation final evaluation, private offer consumers and shared shard manifests); ordered implementation
code-conflicts: exploration-room-actions (exploration adapters/projections and client tests/manifests); serialize shared edits, no semantic dependency
code-conflicts: exploration-presence-rail (occupant/affordance projections and dialogue client tests/manifests); serialize shared edits, no semantic dependency
code-conflicts: monster-prompt-wiring-and-logic-tests (no planned production overlap; shared contract gates and test manifests only)
```

Apply follows both upstream implementations and their executable proof, not merely their proposals. Consume `publish_scene_package`, `lookup_story_role`, `activate_scene_encounter`, `transition_story_dialogue`, `accept_escort_commission`, `release_escort_bindings`, `evaluate_escort_event`, `resolve_exclusive_outcome` and `exclusive_outcome_status` by their upstream authority/transaction contracts without re-declaring them.

## Size and implementation boundary

[INFERENCE] The full approved acceptance list is not a credible one-engineer-day implementation. A planning allocation of 16 hours after both upstream changes covers deterministic confirmation/work and recovery (4), director contracts/checkpoints/publication (4), activation/status consumers (3), and integrated fault/offline/runtime proof plus docs/gates (5), with tests developed alongside behavior. This is exactly one requested proposal with every acceptance criterion retained; the estimate authorizes no narrowed delivery.

Recommended split if one-day apply units are mandatory: first `dream-dispatch-publication` for durable work, visible requirements and two-stage atomic publication, with production enabling guarded; then dependent `dream-encounter-production-handoff` for exploration activation, status consumers and the whole runtime acceptance proof. Those additional changes are suggestions only, have not been created, and need explicit scope approval before replacing this artifact set.
