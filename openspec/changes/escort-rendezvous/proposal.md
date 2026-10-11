# Proposal

## Why

Generated escort commissions are currently refused because protected-role binding has no executable production flow. The approved `docs/superpowers/specs/2026-10-11-escort-rendezvous-design.md` supplies that flow through existing party, quest, possession and settlement owners, including moving-role reunion and exclusive alternative commissions.

## What Changes

- **BREAKING** Extend the existing ordered party ID roster with general membership and quest/role temporary reasons; migrate all readers and writers together without a second roster or compatibility adapter.
- Accept exact published protected actors atomically, preserve ordinary quota and lawful combat behavior, and release each terminal record's reasons with compensated possession handback.
- Add closed destination/rendezvous predicates evaluated from actual movement, activation, binding and living-state changes.
- Arbitrate explicit owner/package outcome groups before reward planning; persist one winner or an unaccepted physical result, invalidate alternatives and close obsolete offers.
- Extend generated package issuance/objective contracts and replace escort rejection at all four boundaries after this change's real flow is implemented and proved. Unsupported templates remain refused.
- Update existing party and quest presentation, versioned capabilities, text interactions and command documentation without a new escort UI.

## Capabilities

### New Capabilities

- `quest-exclusive-outcomes`: durable result arbitration, one settlement entitlement, alternative invalidation and unaccepted outcomes.

### Modified Capabilities

Confirmed existing main capability paths are `party-system`, `companion-possession-core`, `quest-lifecycle`, `quest-progress-tracking`, `quest-failure-conditions`, `quest-blueprint`, `quest-auto-settlement`, `quest-reward-settlement`, `quest-issuer-authorization`, `scenario-director`, `scene-builder`, `npc-schedule-runtime`, `affinity-system`, `affinity-friendly-fire`, `webclient-party-panel`, `webclient-exploration-menu`, `webclient-quest-log-panel`, `webclient-service-menus`, and `webclient-quest-drawer`. Their deltas amend membership/recruitment metadata, handback, acceptance/binding/terminal state and canonical protected-death reason, actual-role completion, publication guards, payout eligibility, issuer scope, generated validation/registration, schedule precedence, affinity departure immunity, complete roster and existing four-state quest/abandonment presentation.

`quest-scene-encounters` is an upstream proposed capability, not a current main capability. This change adds a downstream extension requirement to it for multiple distinct commissions and indexed final-result observation. It consumes `publish_scene_package`, `lookup_story_role`, `activate_scene_encounter`, and `transition_story_dialogue` from `quest-scene-encounters`; it does not re-declare those operations or edit upstream artifacts.

## Impact

Implementation affects existing `world/rules/party.py`, affinity/service gates, combat and possession owners; `world/quests/` definitions, runtime, binding, progress, deadlines, compilation, registration and settlement integration; `server/ai_director_service.py`; ScenarioDirector schema/semantic/template boundaries; map movement completion and position readers; narrative event/knowledge and upstream phase APIs; existing party/quest presenters and client validators. Tests remain beside owners with exact shard ownership and substantive traceability. No dependencies are added.

## Non-goals

No implementation in this proposal, new escort UI, autonomous NPC framework, retry subsystem, extra objective families, data migration, compatibility layer, or fresh-database reset. Dream dispatch is a later consumer and is not a prerequisite.

## Batch:

```text
depends-on: quest-scene-encounters
code-conflicts: quest-scene-encounters (quest package/schema/compiler/registration, role lifecycle, issuer scope, dialogue phases, retention integration); ordered implementation
code-conflicts: exploration-presence-rail (webclient-exploration-menu spec, shared exploration affordance consumers and dialogue/client tests; no planned layout edits)
code-conflicts: exploration-room-actions (webclient-exploration-menu spec, shared exploration capability consumers and client manifests/tests; no planned room-action edits)
code-conflicts: monster-prompt-wiring-and-logic-tests (none in production; shared test-data/contract gates only)
```

Proposal creation needs the upstream contract artifacts, not landed upstream implementation. Apply follows upstream implementation/verification. The exploration changes have no semantic dependency; serialize any shared client/manifest edits. The monster change is independent. Later dream-story-dispatch consumes this change and cannot be a reverse dependency.

## Size and implementation boundary

One engineer-day integration allocation, eight hours, reuses existing owners. Allow 1.5 hours for party metadata/readers and schedule precedence, 1 hour for acceptance/release and possession compensation, 1.5 hours for typed predicates and indexed event integration, 1.5 hours for outcome arbitration and settlement, 0.75 hours for schema/compiler/service guard cutover, 0.75 hours for existing presentation/docs, and 1 hour for focused fixtures, traceability and gates. Tests are developed with each behavior within those allocations. No subsystem rewrite, registry redesign, production dispatch or visual redesign is included. All approved acceptance behaviors remain required; allocation is a planning estimate, not permission to defer them.
