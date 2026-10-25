# Proposal

## Why

NPC identity is currently assembled independently on exploration, dialogue and party surfaces. Plain authored names remove this redundant presentation state while player titles remain owned by their existing system.

Approved source: `docs/superpowers/specs/2026-10-25-npc-capabilities-and-services-design.md` (aa3dbe64). Planning only, unreleased clean cutover.

## What Changes

- **BREAKING** Remove composed NPC names, title reads and title-only presentation contracts across text, game and GM.
- Complete the named producer/consumer/test/documentation cutover in design.md, without shims or historical save repair.
- Preserve existing deterministic gameplay ownership and every stated non-goal.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `npc-identity-titles`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `npc-persona-editor`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `webclient-npc-persona-editor`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `gm-runtime-state`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.

## Impact

npc_identity.npc_display_name/npc_title_value feed typeclasses/npcs.py, exploration/dialogue/party/skill_use presenters, party_scope matching, command item messages, progression unlocks and GM npcs readers. npc.persona.read emits npc_title and the editor composable stores npcTitle. H has already removed the last title-based host cleanup reader.

This is a one-engineer-day runnable slice with 4 focused implementation/test/documentation units. Exact contracts and complete caller categories are in design.md; planned checks are not planning results.

## Batch:

depends-on: npc-service-host-identity

code-conflicts: Follows H so removing npc_title_value does not leave a convergence reader. Shares dialogue.py with generated-packages, AppClient/editor fixtures with reading-client and GM readers with G. Serialize shared files; preserve source-aware dialogue IDs and publication semantics. N deletes remaining authoring after this completed slice.

The complete new-new and relevant active-change matrix and amendment ownership are in `../npc-examination-reception/batch.md`. The approved source remains unchanged.
