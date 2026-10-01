## Why

The adventurer guild's 聖潔王都 branch master (葛里安·衛登, the guild-hall host) carries no NPC persona today and answers from a provisional `guild_staff` table written before the compact card existed. The seven guild rank examiners (temporary exam opponents) likewise have no persona. The approved design (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §1, §5.2–5.3) requires every listed NPC's card and all corresponding authored dialogue to be rewritten — not sampled, not preserved, not filled only where empty. The `npc-persona-profile-registry` inventory assigns exactly these sources to the `altoria_guild` owner, so this slice can be written and reviewed in one workday in parallel with the other content slices.

## What Changes

- Author the host `NpcProfile` in `world/lore/npc_profiles/altoria_guild.py`, keyed by the host's `service_id`, each with a complete compact card grounded in the host's established identity and world facts and a `misunderstood` voice line in that host's own voice; `greeting` stays `None` because each host's table authors its greeting.
- Author seven examiner profiles (`guild_examiner_f` … `guild_examiner_s`) with complete cards and no voice lines, add an `examiner_profile_key` to `GuildRank` naming each, and extend `validate_guild_npc_identities` so a missing or unresolved key fails load naming the rank.
- Set `host_profile_key` on the guild-hall host row in `world/lore/settlements/places_altoria_middle.py`.
- Rewrite the greeting and every keyword response of the `guild_staff` table in `world/lore/dialogue/guild.py` against the new cards, keeping each table's keyword identifiers, greeting presence, and every mechanical/service semantic its settlement specs require.
- Write every greeting, response and voice line strictly in character: the branch master knows only its own world, so no line names a command, a game mechanic, or an interface element. The table stops naming `guild register`, `guild list`, `guild accept`, `guild log`, `guild show`, `guild turnin`, `guild abandon` and `guild merit`; the host explains the counter in the world's terms (sign the register, take a slip from the board, come back and report with the slip's number). The `回報` keyword stays, because reporting back is what a returning adventurer says. This overturns the `scripted-dialogue` and `guild-registration` requirements that the table teach the guild commands. The branch master speaks formally, as an office-holder at the counter.
- Replace incidental exact-wording test assertions on the old prose with behavior assertions; keep contract-pinned substrings.
- Add no data-contract test and pin no prose: NPC lines are authored content, and rewording them must never break a test. Remove the existing pins that would (the pre-split dialogue digests in `test_dialogue_assembly`, the `guild <verb>` substring checks in `test_dialogue` and `test_talk_turnin_commands`). Completeness and voice quality are established by the recorded editorial review.

No creation path writes these cards yet: `npc-persona-host-examiner-producers` initializes them on new hosts and exam opponents, `npc-persona-roster-cutover` replaces existing instances, and `npc-persona-dialogue-consumption` routes the `misunderstood` line. Until then the authored dialogue is live and the cards are inert lore.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `npc-profile-registry` (introduced by `npc-persona-profile-registry`): ADDED requirement "Guild branch master and rank examiners carry individual authored profiles and rewritten dialogue".
- `scripted-dialogue`: MODIFIED requirements "Scripted dialogue hosts answer authored talk lines" (the greeting scenario) and "Dialogue tables are immutable, keyed, and registry-backed" — the `guild_staff` table describes the counter in character and names no command.
- `guild-registration`: MODIFIED requirement "Guild service hosts teach their service commands through scripted dialogue" — the host teaches the service in the world's terms and names no command (title kept for traceability).

## Impact

- Content: `world/lore/npc_profiles/altoria_guild.py`, `world/lore/settlements/places_altoria_middle.py` (the guild-hall row gains `host_profile_key`), `world/lore/dialogue/guild.py` (the `guild_staff` table rewritten), `world/lore/guild.py` (examiner profile keys).
- Tests: no new test module. `test_dialogue` and `test_talk_turnin_commands` stop asserting `guild <verb>` substrings and compare the host's answers with its authored table instead, plus a no-command-token assertion on the `guild_staff` table; `test_dialogue_assembly` drops its pre-split content digests and keeps a prose-free four-answer shape check; `test_guild` gains a synthetic-rank rejection for an unresolved examiner profile key; the guild hall's pinned place tuple in `test_settlements` gains its `host_profile_key`; the shipped-registry immutability check moves to the `test_npc_profile_inventory` data contract and the guild-economy test support resolves its service ids by place kind (identical hunks in every content slice).
- No mechanism, schema, prompt, or UI change; live stock, prices, quest listings, and command availability are untouched.

## Batch:

depends-on: npc-persona-profile-registry

Code-conflict notes: `world/lore/settlements/places_altoria_middle.py` is also edited by `npc-persona-content-altoria-trade` (different rows). `world/lore/guild.py` gains the `examiner_profile_key` field here; `npc-persona-host-examiner-producers` later reads it without editing it. `world/lore/dialogue/guild.py` and `world/lore/npc_profiles/altoria_guild.py` are owned by this slice alone. The shared test edits (`test_dialogue_assembly`, the immutability move, the guild-economy test support) are byte-identical across the content slices, so they merge cleanly. This slice is a prerequisite of `npc-persona-host-examiner-producers` and `npc-persona-roster-cutover`; it is independent of every other content slice.
