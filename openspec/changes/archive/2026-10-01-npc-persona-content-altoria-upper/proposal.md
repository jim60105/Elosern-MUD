## Why

The 5 聖潔王都 (`capital_altoria`) upper-terrace hosts (艾莉安娜·寒水、羅海西亞·芬威克、古利安·鷹守、伊沃·高丘、奧德溫·薩契) carry no NPC persona today and answer from provisional dialogue tables written before the compact card existed. The approved design (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §1, §5.2–5.3) requires every listed NPC's card and all corresponding authored dialogue to be rewritten — not sampled, not preserved, not filled only where empty. The `npc-persona-profile-registry` inventory assigns exactly these sources to the `altoria_upper` owner, so this slice can be written and reviewed in one workday in parallel with the other content slices.

## What Changes

- Author 5 `NpcProfile` rows in `world/lore/npc_profiles/altoria_upper.py`, one per host, keyed by the host's `service_id`, each with a complete compact card grounded in the host's established identity and world facts and a `misunderstood` voice line in that host's own voice; `greeting` stays `None` because each host's table authors its greeting.
- Set `host_profile_key` on the 5 host rows in `world/lore/settlements/places_altoria_upper.py`.
- Rewrite the greeting and every keyword response of the 5 tables in `world/lore/dialogue/altoria_upper.py` against the new cards, keeping each table's keyword identifiers, greeting presence, and every mechanical/service semantic its settlement specs require.
- Write every greeting, response and voice line strictly in character: a host knows only its own world, so no line names a command, a game mechanic, or an interface element. The tables stop naming `shop stock`, `buy`, `sell`, `rest`, `practice`, `guild exam`, `engage`, `combat forfeit`, `combat actions`, `lore` and the builder-only `地圖`; the drill instructor and the dean describe practice, rank exams and the codex of knowledge in the world's terms. The priestess, the noble-quarter captain and the dean speak formally (an officiant, an on-duty officer, a dean receiving callers); the deacon behind the shop counter and the drill instructor on the yard speak colloquially.
- Replace incidental exact-wording test assertions on the old prose with behavior assertions; keep contract-pinned substrings.
- Add no data-contract test and pin no prose: NPC lines are authored content, and rewording them must never break a test. Remove the existing pins that would (the pre-split dialogue digests in `test_dialogue_assembly`; the drill instructor's `rest`/`practice`/`guild exam` and 「沒有陪練」 checks in `test_altoria_crown_watch`; the dean's 「沒有『拜師』這道門」 and `rest`/`practice`/`guild exam`/`lore` checks in `test_altoria_learning_exchange`; the requirement in `test_altoria_sanctum` that the deacon's table quote a trade command). Completeness and voice quality are established by the recorded editorial review.

No creation path writes these cards yet: `npc-persona-host-examiner-producers` initializes them on new hosts, `npc-persona-roster-cutover` replaces existing instances, and `npc-persona-dialogue-consumption` routes the `misunderstood` line. Until then the authored dialogue is live and the cards are inert lore.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `npc-profile-registry` (introduced by `npc-persona-profile-registry`): ADDED requirement "Altoria upper-terrace hosts carry individual authored profiles and rewritten dialogue".

## Impact

- Content: `world/lore/npc_profiles/altoria_upper.py`, `world/lore/settlements/places_altoria_upper.py` (5 rows gain `host_profile_key`), `world/lore/dialogue/altoria_upper.py` (5 tables rewritten).
- Tests: no new test module. The crown-watch, learning-exchange and sanctum suites drop their exact-word pins on these tables for no-command-token assertions (the academy's rank and element substance checks, which read the lore registries, stay); `test_dialogue_assembly` drops its pre-split content digests and keeps a prose-free four-answer shape check; no owned place tuple is pinned in `test_settlements`; the shipped-registry immutability check moves to the `test_npc_profile_inventory` data contract and the guild-economy test support resolves its service ids by place kind (identical hunks in every content slice).
- No mechanism, schema, prompt, or UI change; live stock, prices, quest listings, and command availability are untouched.

## Batch:

depends-on: npc-persona-profile-registry

Code-conflict notes: `world/lore/settlements/places_altoria_upper.py`, `world/lore/dialogue/altoria_upper.py`, and `world/lore/npc_profiles/altoria_upper.py` are owned by this slice alone. The shared test edits are byte-identical across the content slices, and this slice's edit to `test_altoria_learning_exchange` (the dean's assertions) is separated by an unchanged line from `npc-persona-content-altoria-trade`'s edit (the hall's), so both merge cleanly. This slice is a prerequisite of `npc-persona-host-examiner-producers` and `npc-persona-roster-cutover`; it is independent of every other content slice.
