## Why

The 5 聖潔王都 (`capital_altoria`) lower-terrace hosts (西格瑪·庫柏、蘿溫·古橡、溫弗蕾德·古林、伊莎貝爾·葦沼、托瓦德·鄧堡) carry no NPC persona today and answer from provisional dialogue tables written before the compact card existed. The approved design (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §1, §5.2–5.3) requires every listed NPC's card and all corresponding authored dialogue to be rewritten — not sampled, not preserved, not filled only where empty. The `npc-persona-profile-registry` inventory assigns exactly these sources to the `altoria_lower` owner, so this slice can be written and reviewed in one workday in parallel with the other content slices.

## What Changes

- Author 5 `NpcProfile` rows in `world/lore/npc_profiles/altoria_lower.py`, one per host, keyed by the host's `service_id`, each with a complete compact card grounded in the host's established identity and world facts and a `misunderstood` voice line in that host's own voice; `greeting` stays `None` because each host's table authors its greeting.
- Set `host_profile_key` on the 5 host rows in `world/lore/settlements/places_altoria_lower.py`.
- Rewrite the greeting and every keyword response of the 5 tables in `world/lore/dialogue/altoria_lower.py` against the new cards, keeping each table's keyword identifiers, greeting presence, and every mechanical/service semantic its settlement specs require.
- Write every greeting, response and voice line strictly in character: a host knows only its own world, so no line names a command, a game mechanic, or an interface element, and casual places speak in everyday colloquial register (only on-duty officials speak formally). This overturns `altoria-hospitality`'s requirement that the inn and tavern tables name their commands.
- Replace incidental exact-wording test assertions on the old prose with behavior assertions; keep contract-pinned substrings.
- Add a data-contract test for this slice: reference resolution, keyword-set preservation, voice-line coverage, no surviving provisional line, and within-slice voice distinctness.

No creation path writes these cards yet: `npc-persona-host-examiner-producers` initializes them on new hosts, `npc-persona-roster-cutover` replaces existing instances, and `npc-persona-dialogue-consumption` routes the `misunderstood` line. Until then the authored dialogue is live and the cards are inert lore.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `npc-profile-registry` (introduced by `npc-persona-profile-registry`): ADDED requirement "Altoria lower-terrace hosts carry individual authored profiles and rewritten dialogue".
- `altoria-hospitality`: MODIFIED requirement "Each host's dialogue teaches what its location is for" — hosts teach their location's purpose in in-world terms and name no command.

## Impact

- Content: `world/lore/npc_profiles/altoria_lower.py`, `world/lore/settlements/places_altoria_lower.py` (5 rows gain `host_profile_key`), `world/lore/dialogue/altoria_lower.py` (5 tables rewritten).
- Tests: a new data-contract module under `world/lore/tests/` (package-owned shard), its `tools/test_data_freeze.json` entry, and wording updates in existing tests that pinned provisional prose; `test_altoria_hospitality`'s command-token assertions become in-world-topic and no-command-token assertions, and `test_dialogue_assembly` stops pinning the five rewritten tables' pre-split digests.
- No mechanism, schema, prompt, or UI change; live stock, prices, quest listings, and command availability are untouched.

## Batch:

depends-on: npc-persona-profile-registry

Code-conflict notes: `world/lore/settlements/places_altoria_lower.py`, `world/lore/dialogue/altoria_lower.py`, and `world/lore/npc_profiles/altoria_lower.py` are owned by this slice alone. Every content slice appends to `tools/test_data_freeze.json` (adjacent-line rebase conflicts only). This slice is a prerequisite of `npc-persona-host-examiner-producers` and `npc-persona-roster-cutover`; it is independent of every other content slice.
