# Proposal

## Why

The counter accepts requests while a separate qualification table selects the actual examiner. The current shared name obscures this authority boundary.

Approved source: `docs/superpowers/specs/2026-10-25-npc-capabilities-and-services-design.md` (aa3dbe64). Planning only, unreleased clean cutover.

## What Changes

- **BREAKING** Rename examination reception and remove the unused persistent-adventurer profession label.
- Complete the named producer/consumer/test/documentation cutover in design.md, without shims or historical save repair.
- Preserve existing deterministic gameplay ownership and every stated non-goal.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `guild-registration`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `guild-rank-exams`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `human-guild-hosts`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `profession-registries`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `webclient-service-menus`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `quest-issuer-authorization`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.

## Impact

Observed `typeclasses/components.py::GuildExaminer` uses slot `guild_examiner`. `guild_exams.py::resolve_exam_request_target` resolves a counter separately from `human_guild_hosts.qualified_host`. `GuildAdventurer.profession` defaults to adventurer and `sync_persistent_adventurers` writes it despite no gameplay consumer. The current rulebook still expands counter blueprints, so this first slice keeps that mechanism coherent until direct declarations replace it.

This is a one-engineer-day runnable slice with 3 focused implementation/test/documentation units. Exact contracts and complete caller categories are in design.md; planned checks are not planning results.

## Batch:

depends-on: none

code-conflicts: Shared components.py, profession vocabulary, guild_exams, service_actions tests and shard ownership with H/D/T/P. Serialize with authored-dialogue-refresh-lifecycle and webclient-settlement-alignment when editing guild_exams/service adapters; their mutation/publication logic is unchanged.

The complete new-new and relevant active-change matrix and amendment ownership are in `../npc-examination-reception/batch.md`. The approved source remains unchanged.
