# Proposal

## Why

A text session must discover the same provider services and refusal reasons as the browser. Explicit targets prevent a selected NPC from becoming an unrelated room provider.

Approved source: `docs/superpowers/specs/2026-10-25-npc-capabilities-and-services-design.md` (aa3dbe64). Planning only, unreleased clean cutover.

## What Changes

- **BREAKING** Expose shared service discovery/reasons through NPC inspection and targeted existing text commands.
- Complete the named producer/consumer/test/documentation cutover in design.md, without shims or historical save repair.
- Preserve existing deterministic gameplay ownership and every stated non-goal.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `game-command-docs`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `guild-quest-board`: distinguish explicit selected-provider commands from implicit room discovery.
- `shop-economy`: distinguish targeted stock/trade commands from implicit unambiguous merchant discovery.

## Impact

commands/guild.py::_GuildCommandBase currently resolves one room staff; commands/church.py::CmdChurchJoin similarly resolves one ChurchHost. The existing look/interaction conventions and docs/game/{commands,command-reference}.md are protected by tests/test_command_docs.py. P provides immutable contextual descriptors and T provides exact target validation.

This is a one-engineer-day runnable slice with 4 focused implementation/test/documentation units. Exact contracts and complete caller categories are in design.md; planned checks are not planning results.

## Batch:

depends-on: npc-contextual-service-projection

code-conflicts: X follows P; U follows X so church command routing is real when advertised. Shares command docs/manifest and church/guild/commerce parser fixtures with R/T. No semantic dependency on unrelated authored prose or publication receiver internals.

The complete new-new and relevant active-change matrix and amendment ownership are in `../npc-examination-reception/batch.md`. The approved source remains unchanged.
