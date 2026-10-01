## Why

The adventurer guild's 聖潔王都 branch master (葛里安·衛登, the guild-hall host) carries no NPC persona today and answers from a provisional `guild_staff` table written before the compact card existed. The seven guild rank examiners (temporary exam opponents) likewise have no persona. The approved design (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §1, §5.2–5.3) requires every listed NPC's card and all corresponding authored dialogue to be rewritten — not sampled, not preserved, not filled only where empty. The foundation inventory assigns exactly these sources to the `altoria_guild` owner, so this slice can be written and reviewed in one workday in parallel with the other content slices.

## What Changes

- Author the host `NpcProfile` in `world/lore/npc_profiles/altoria_guild.py`, keyed by the host's `service_id`, each with a complete compact card grounded in the host's established identity and world facts and a `misunderstood` voice line in that host's own voice; `greeting` stays `None` because each host's table authors its greeting.
- Author seven examiner profiles (`guild_examiner_f` … `guild_examiner_s`) with complete cards and no voice lines, add a required `examiner_profile_key` to `GuildRank` naming each, and extend `validate_guild_npc_identities` so an unresolved key fails load naming the rank.
- Set `host_profile_key` on the guild-hall host row in `world/lore/settlements/places_altoria_middle.py`.
- Rewrite the greeting and every keyword response of the `guild_staff` table in `world/lore/dialogue/guild.py` against the new cards, keeping each table's keyword identifiers, greeting presence, and every mechanical/service semantic its settlement specs require.
- Replace incidental exact-wording test assertions on the old prose with behavior assertions; keep contract-pinned substrings.
- Add a data-contract test for this slice: reference resolution, keyword-set preservation, voice-line coverage, no surviving provisional line, and within-slice voice distinctness.

No creation path writes these cards yet: `npc-persona-host-examiner-producers` initializes them on new hosts and exam opponents, `npc-persona-roster-cutover` replaces existing instances, and `npc-persona-dialogue-consumption` routes the `misunderstood` line. Until then the authored dialogue is live and the cards are inert lore.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `npc-profile-registry` (introduced by `npc-persona-card-foundation`): ADDED requirement "Guild branch master and rank examiners carry individual authored profiles and rewritten dialogue".

## Impact

- Content: `world/lore/npc_profiles/altoria_guild.py`, `world/lore/settlements/places_altoria_middle.py` (the guild-hall row gains `host_profile_key`), `world/lore/dialogue/guild.py` (the `guild_staff` table rewritten), `world/lore/guild.py` (examiner profile keys).
- Tests: a new data-contract module under `world/lore/tests/` (package-owned shard), its `tools/test_data_freeze.json` entry, and wording updates in existing tests that pinned provisional prose.
- No mechanism, schema, prompt, or UI change; live stock, prices, quest listings, and command availability are untouched.

## Batch:

depends-on: npc-persona-card-foundation

Code-conflict notes: `world/lore/settlements/places_altoria_middle.py` is also edited by `npc-persona-content-altoria-trade` (different rows). `world/lore/guild.py` gains the `examiner_profile_key` field here; `npc-persona-host-examiner-producers` later reads it without editing it. `world/lore/dialogue/guild.py` and `world/lore/npc_profiles/altoria_guild.py` are owned by this slice alone. Every content slice appends to `tools/test_data_freeze.json` (adjacent-line rebase conflicts only). This slice is a prerequisite of `npc-persona-host-examiner-producers` and `npc-persona-roster-cutover`; it is independent of every other content slice.
