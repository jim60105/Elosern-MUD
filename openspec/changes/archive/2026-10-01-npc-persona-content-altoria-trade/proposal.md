## Why

The 6 聖潔王都 (`capital_altoria`) middle-terrace trade hosts (瑪爾特·金秤、維爾登·黑潭、妮絲塔·狐溪、艾蓮娜·鴉丘、希碧拉·灰沼、尤斯汀·柯德溫) carry no NPC persona today and answer from provisional dialogue tables written before the compact card existed. The approved design (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §1, §5.2–5.3) requires every listed NPC's card and all corresponding authored dialogue to be rewritten — not sampled, not preserved, not filled only where empty. The `npc-persona-profile-registry` inventory assigns exactly these sources to the `altoria_trade` owner, so this slice can be written and reviewed in one workday in parallel with the other content slices.

## What Changes

- Author 6 `NpcProfile` rows in `world/lore/npc_profiles/altoria_trade.py`, one per host, keyed by the host's `service_id`, each with a complete compact card grounded in the host's established identity and world facts and a `misunderstood` voice line in that host's own voice; `greeting` stays `None` because each host's table authors its greeting.
- Set `host_profile_key` on the 6 host rows in `world/lore/settlements/places_altoria_middle.py`.
- Rewrite the greeting and every keyword response of the 6 tables in `world/lore/dialogue/altoria_middle.py` against the new cards, keeping each table's keyword identifiers, greeting presence, and every mechanical/service semantic its settlement specs require.
- Write every greeting, response and voice line strictly in character: a host knows only its own world, so no line names a command, a game mechanic, or an interface element, and the shops speak in everyday colloquial register (only the merchant guild master, receiving callers in his office, speaks formally). The tables stop naming `shop stock`, `buy`, `sell`, `前往` and `guild request`; goods guidance stays in the world's terms (the shelf, the counter, the price board).
- Replace incidental exact-wording test assertions on the old prose with behavior assertions; keep contract-pinned substrings.
- Add no data-contract test and pin no prose: NPC lines are authored content, and rewording them must never break a test. Remove the existing pins that would (the pre-split dialogue digests in `test_dialogue_assembly`, the merchant hall's 「牆上無單」 and `` `前往` `` checks in `test_altoria_learning_exchange`). Completeness and voice quality are established by the recorded editorial review.

No creation path writes these cards yet: `npc-persona-host-examiner-producers` initializes them on new hosts, `npc-persona-roster-cutover` replaces existing instances, and `npc-persona-dialogue-consumption` routes the `misunderstood` line. Until then the authored dialogue is live and the cards are inert lore.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `npc-profile-registry` (introduced by `npc-persona-profile-registry`): ADDED requirement "Altoria middle-terrace trade hosts carry individual authored profiles and rewritten dialogue".

## Impact

- Content: `world/lore/npc_profiles/altoria_trade.py`, `world/lore/settlements/places_altoria_middle.py` (6 rows gain `host_profile_key`), `world/lore/dialogue/altoria_middle.py` (6 tables rewritten).
- Tests: no new test module. `test_dialogue_assembly` drops its pre-split content digests; `test_altoria_learning_exchange` drops the merchant hall's exact-word pins for a no-command-token assertion on that table; the pinned place tuples of the general store, forge and tailor in `test_settlements` gain their `host_profile_key`; the shipped-registry immutability check moves from `test_npc_profiles` to the `test_npc_profile_inventory` data contract now that the registry is populated (the same move every content slice makes; identical hunks); `test_dialogue_assembly` keeps a prose-free four-answer shape check; the two host-less place fixtures cloned from the general store row (`test_service_host_roster`, `test_service_host_identity`) clear its new `host_profile_key`; and the guild-economy test support resolves its guild and merchant service ids by place kind, since a shipped service id is now also a shipped profile key.
- No mechanism, schema, prompt, or UI change; live stock, prices, quest listings, and command availability are untouched.

## Batch:

depends-on: npc-persona-profile-registry

Code-conflict notes: `world/lore/settlements/places_altoria_middle.py` is also edited by `npc-persona-content-altoria-guild` (only the guild-hall row); the two slices touch different rows, so a rebase conflict, if any, is mechanical. `world/lore/dialogue/altoria_middle.py` and `world/lore/npc_profiles/altoria_trade.py` are owned by this slice alone. The shared test edits (`test_dialogue_assembly`, the immutability move) are byte-identical across the content slices, so they merge cleanly. This slice is a prerequisite of `npc-persona-host-examiner-producers` and `npc-persona-roster-cutover`; it is independent of every other content slice.
