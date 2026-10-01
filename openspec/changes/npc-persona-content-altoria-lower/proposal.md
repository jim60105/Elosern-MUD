## Why

The 5 聖潔王都 (`capital_altoria`) lower-terrace hosts (西格瑪·庫柏、蘿溫·古橡、溫弗蕾德·古林、伊莎貝爾·葦沼、托瓦德·鄧堡) carry no NPC persona today and answer from provisional dialogue tables written before the compact card existed. The approved design (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §1, §5.2–5.3) requires every listed NPC's card and all corresponding authored dialogue to be rewritten — not sampled, not preserved, not filled only where empty. The foundation inventory assigns exactly these sources to the `altoria_lower` owner, so this slice can be written and reviewed in one workday in parallel with the other content slices.

## What Changes

- Author 5 `NpcProfile` rows in `world/lore/npc_profiles/altoria_lower.py`, one per host, keyed by the host's `service_id`, each with a complete compact card grounded in the host's established identity and world facts and a `misunderstood` voice line in that host's own voice; `greeting` stays `None` because each host's table authors its greeting.
- Set `host_profile_key` on the 5 host rows in `world/lore/settlements/places_altoria_lower.py`.
- Rewrite the greeting and every keyword response of the 5 tables in `world/lore/dialogue/altoria_lower.py` against the new cards, keeping each table's keyword identifiers, greeting presence, and every mechanical/service semantic its settlement specs require.
- Replace incidental exact-wording test assertions on the old prose with behavior assertions; keep contract-pinned substrings.
- Add a data-contract test for this slice: reference resolution, keyword-set preservation, voice-line coverage, no surviving provisional line, and within-slice voice distinctness.

No creation path writes these cards yet: `npc-persona-host-examiner-producers` initializes them on new hosts, `npc-persona-roster-cutover` replaces existing instances, and `npc-persona-dialogue-consumption` routes the `misunderstood` line. Until then the authored dialogue is live and the cards are inert lore.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `npc-profile-registry` (introduced by `npc-persona-card-foundation`): ADDED requirement "Altoria lower-terrace hosts carry individual authored profiles and rewritten dialogue".

## Impact

- Content: `world/lore/npc_profiles/altoria_lower.py`, `world/lore/settlements/places_altoria_lower.py` (5 rows gain `host_profile_key`), `world/lore/dialogue/altoria_lower.py` (5 tables rewritten).
- Tests: a new data-contract module under `world/lore/tests/` (package-owned shard), its `tools/test_data_freeze.json` entry, and wording updates in existing tests that pinned provisional prose.
- No mechanism, schema, prompt, or UI change; live stock, prices, quest listings, and command availability are untouched.

## Batch:

depends-on: npc-persona-card-foundation

Code-conflict notes: `world/lore/settlements/places_altoria_lower.py`, `world/lore/dialogue/altoria_lower.py`, and `world/lore/npc_profiles/altoria_lower.py` are owned by this slice alone. Every content slice appends to `tools/test_data_freeze.json` (adjacent-line rebase conflicts only). This slice is a prerequisite of `npc-persona-host-examiner-producers` and `npc-persona-roster-cutover`; it is independent of every other content slice.
