## Why

The `offer_quest` intent is whitelisted in the dialogue layer but has no executable surface: every
extraction currently returns `applied=False` with no state change (npc-dialogue spec scenario "A
whitelisted but not-yet-executable intent is rejected"). The design
(`docs/superpowers/specs/2026-08-09-dialogue-quests-lore-design.md`) defines the deterministic
capability surface: an NPC holding a registered guild offer may assign that quest through dialogue
as a direct, atomic assignment — speech is the notification, no pending-offer step.

## What Changes

- Add `_apply_offer_quest` to `world/rules/npc_intents.py`:
  - Payload is exactly `{"quest_key": str}` (bounded); extra or missing fields reject.
  - Verification: the NPC carries the `GuildStaff` component with a `branch_key`;
    `get_guild_offer(quest_key, branch_key)` resolves (the offer is registered at that branch);
    the player's canonical guild rank is within the offer's quest rank band.
  - Application: `accept_quest(player, quest_key)` plus `apply_affinity_change(npc, player,
    GUILD, +1)` commit in one atomic transaction with quest-log/relations snapshots and rollback,
    mirroring `accept_guild_offer`; duplicate-quest rejection is delegated to the quest runtime.
- Remove `offer_quest` from `_FORWARD_DECLARED_KINDS` in `world/rules/npc_intents.py` (the tuple
  then holds only `reveal_lore`, owned by the sibling `lore-knowledge-codex` change).
- Keep the accepted failure mode unchanged: any verification or application failure discards only
  the intent and preserves the speech; `none` and every other intent kind are untouched.

## Capabilities

### New Capabilities
- `dialogue-offer-quest`: The deterministic capability surface for the `offer_quest` dialogue
  intent — exact payload shape, guild-offer verification, direct atomic assignment through the
  quest runtime with affinity credit, and the failure semantics (speech preserved, no state).

### Modified Capabilities
- `npc-dialogue`: The intent-whitelist requirement changes — `offer_quest` becomes executable with
  the exact payload `{"quest_key": str}`; the "whitelisted but not-yet-executable" scenario
  now covers only `reveal_lore`.

## Impact

- `world/rules/npc_intents.py`: new applier; `_FORWARD_DECLARED_KINDS` shrinks to `reveal_lore`.
- `world/rules/guild_offers.py` / `world/rules/guild.py`: offer verification and rank checks are
  reused, no API changes.
- `world/quests/runtime.py`: `accept_quest` reused unchanged.
- `world/rules/affinity.py`: `AffinitySource.GUILD` reused for the +1 credit.
- Tests: `world/rules/tests/test_npc_intents.py` and dialogue-layer tests gain offer-quest paths;
  existing guild/quest/affinity suites must stay green.
- No backward compatibility or migration work: the project is unreleased with zero users.
