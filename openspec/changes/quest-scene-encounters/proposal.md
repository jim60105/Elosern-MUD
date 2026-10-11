# Proposal

## Why

The approved quest-scene encounter design lets players meet generated named characters before accepting a commission and retain their identities and memories afterward. The current compiler requires an existing issuer and the builder spawns occupants only in accepted instance stages, so publication, encounter activation, and dialogue need explicit deterministic contracts.

## What Changes

- Publish immutable validated scene packages with reusable roles, typed relationships, provenance-bearing initial knowledge, independent encounters, and complete phase dialogue.
- **BREAKING** Replace the blanket permanent-occupant restriction with validated package ownership and retention; share existing construction and compiler paths.
- Activate encounters transactionally without a fabricated accepted quest, reusing exact role identities and refusing missing or dead actors.
- Provision scoped runtime QuestIssuer components through rules-owned helpers and keep strict registration authorization.
- Resolve authored and generated dialogue through one resolver, using existing conversation topics and freshness contracts offline.
- Retain named actors across quest terminal states and transfer them before destructive instance reclamation.

## Capabilities

### New Capabilities

- `persistent-story-roles`: immutable scene packages, reusable exact role bindings, relationships, initial knowledge, and terminal-state retention.
- `quest-scene-encounters`: independent pre-acceptance encounter activation with durable identities and rollback.
- `story-phase-dialogue`: finite validated phases, deterministic selection, permitted knowledge, and revisioned transitions.

### Modified Capabilities

- `scene-builder`: deterministic shared construction and validated permanent-room occupants.
- `scenario-director`: shared bounded package proposal and deterministic compile/publication validation with symbolic issuer planning.
- `quest-issuer-authorization`: explicit validated runtime provisioning while retaining component-exclusive authority and existing key grammar.
- `scripted-dialogue`: shared authored/generated resolver and validated topic effects.
- `npc-dialogue`: current phase context, offline phase responses, and stale-phase settlement rejection.
- `webclient-dialogue-session`: existing window refresh and obsolete choice invalidation.
- `instance-reclamation`: retained-role transfers before ordinary owned-entity cleanup.

## Impact

Extend `world/quests/compile/`, `generated_quest_store.py`, `scene_builder.py`, quest lifecycle/binding consumers, rules-owned component/dialogue/intent helpers, narrative knowledge/context APIs, maps reclamation, and existing text/presentation consumers. Keep lore registries immutable. Add deterministic synthetic consumer and rollback tests alongside their owners and update shard manifests and traceability claims during implementation.

## Scope and delivery

One engineer-day integration change, reusing implemented compiler, prototype, characterization, component, narrative, and versioned presentation infrastructure. Implement deterministic contracts before proposal-schema changes and presentation cutover. No new UI, agent framework, live-model requirement, retry engine, migration, compatibility layer, or deployment boundary.

Source of truth is `docs/superpowers/specs/2026-10-11-quest-scene-encounters-design.md`, including sections 2 and 10. Escort mechanics and production dream/exploration dispatch belong to subsequent designs. ESCORT publication stays guarded until its protected-role flow lands. This change exposes exact actor, commission, and phase APIs without requiring sibling artifacts.

## Dependency and conflict matrix

| Active change | Dependency | Potential code conflict | Ordering |
| --- | --- | --- | --- |
| monster-prompt-wiring-and-logic-tests | None | Prompt registry or art-subject integration only if implementation changes shared registration; avoid those edits | No required order; coordinate any shared registration edits |
| exploration-presence-rail | None | DialogueChoices extraction and app-client dialogue tests | Preserve current conversation component contracts; serialize shared test/component edits |
| exploration-room-actions | None | Shared app-client or exploration-menu tests if affected by dialogue integration | No required order; avoid room-action UI edits |

The active monster proposal has no completed artifact set at planning time, so its eventual scope must be checked before shared-file edits. Designs 2 and 3 consume this change sequentially; neither is an upstream dependency.

## Batch:

```text
depends-on: none
code-conflicts: exploration-presence-rail (DialogueChoices.vue, app-client dialogue tests); exploration-room-actions (shared app-client/exploration-menu tests); monster-prompt-wiring-and-logic-tests (conditional prompt registration/art-subject integration)
```
