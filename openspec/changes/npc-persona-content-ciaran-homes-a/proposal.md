## Why

The 4 暗影谷村 (`village_ciaran`) first four homes hosts (艾莉妮斯·達恩斯特瑞德爾、格威娜拉·希爾維爾莉夫、海莉爾·斯塔爾法爾、拉瑞內斯·妮特布倫) carry no NPC persona today and answer from provisional dialogue tables written before the compact card existed. The approved design (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §1, §5.2–5.3) requires every listed NPC's card and all corresponding authored dialogue to be rewritten — not sampled, not preserved, not filled only where empty. The `npc-persona-profile-registry` inventory assigns exactly these sources to the `ciaran_homes_a` owner, so this slice can be written and reviewed in one workday in parallel with the other content slices.

## What Changes

- Author 4 `NpcProfile` rows in `world/lore/npc_profiles/ciaran_homes_a.py`, one per host, keyed by the host's `service_id`, each with a complete compact card grounded in the host's established identity and world facts and a `misunderstood` voice line in that host's own voice; `greeting` stays `None` because each host's table authors its greeting.
- Set `host_profile_key` on the 4 host rows in `world/lore/settlements/places_ciaran.py`.
- Rewrite the greeting and every keyword response of the 4 tables in `world/lore/dialogue/ciaran.py` against the new cards, keeping each table's keyword identifiers, greeting presence, and every mechanical/service semantic its settlement specs require.
- Replace incidental exact-wording test assertions on the old prose with behavior assertions; keep contract-pinned substrings.
- Add a data-contract test for this slice: reference resolution, keyword-set preservation, voice-line coverage, no surviving provisional line, and within-slice voice distinctness.

No creation path writes these cards yet: `npc-persona-host-examiner-producers` initializes them on new hosts, `npc-persona-roster-cutover` replaces existing instances, and `npc-persona-dialogue-consumption` routes the `misunderstood` line. Until then the authored dialogue is live and the cards are inert lore.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `npc-profile-registry` (introduced by `npc-persona-profile-registry`): ADDED requirement "Village Ciaran first-home hosts carry individual authored profiles and rewritten dialogue".

## Impact

- Content: `world/lore/npc_profiles/ciaran_homes_a.py`, `world/lore/settlements/places_ciaran.py` (4 rows gain `host_profile_key`), `world/lore/dialogue/ciaran.py` (4 tables rewritten).
- Tests: a new data-contract module under `world/lore/tests/` (package-owned shard), its `tools/test_data_freeze.json` entry, and wording updates in existing tests that pinned provisional prose.
- No mechanism, schema, prompt, or UI change; live stock, prices, quest listings, and command availability are untouched.

## Batch:

depends-on: npc-persona-profile-registry

Code-conflict notes: `world/lore/settlements/places_ciaran.py` and `world/lore/dialogue/ciaran.py` are also edited by `npc-persona-content-ciaran-homes-b` (disjoint rows: this slice owns the 艾莉妮斯, 格威娜拉, 海莉爾 and 拉瑞內斯 rows); rebase conflicts are adjacent-hunk only. `world/lore/npc_profiles/ciaran_homes_a.py` is owned by this slice alone. Every content slice appends to `tools/test_data_freeze.json` (adjacent-line rebase conflicts only). This slice is a prerequisite of `npc-persona-host-examiner-producers` and `npc-persona-roster-cutover`; it is independent of every other content slice.
