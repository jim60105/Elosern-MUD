# Elven residents content review

Line-by-line editorial and lore verification for `elven-resident-npcs-content`:
45 chat-only adult female residents (15 per village), organized as 15 households
of three (a mother and two daughters) sharing one surname and one home.

## Sources read

- `tmp/story_settings/world_info.md` — 種族設定›精靈族（全族女性、無固定職業／
  婚姻／正式教育、壽命 800–1200）、生活方式›性文化（對裸露、性器官、性行為完全
  沒有羞恥概念、任何地點任何時間都可能進行性行為）、社會與文化›婚姻／倫理觀。
- `docs/lore/overview.md` — 精靈族、性別與生殖、性愛與身體、精靈村落。
- `docs/lore/settlement-locations.md` — 三村（幽月谷村、暗影谷村、翠綠森林村）與
  聚落差異。
- `skill://npc-dialogue-content` + `skill://map-data-authoring`。

## Structure and identity

- 45 residents, 15 per village, five households of three per village. Each
  household shares one surname and one home interior room; three residents'
  `Resident.home_room` point at the same room (verified by
  `world.rules.tests.test_resident_sync` cohabitation and by the load check).
- Public nodes: eolas `valley_floor`, ciaran `village_plaza`, fionnen
  `light_court`; every home interior declares an `exterior` onto its village's
  public node, and the shared `resident` schedule template binds
  `market_square`→public and `residence`→home.
- `race=elf`, `subrace` per village, `sex=female`. Stats are literal in-band
  elf baselines (hp/mp/sp 10000, physical 70–95, magic 100–200). No learning or
  body-enhancement multiplier is baked into a stored value.

## Names

Given names are globally unique and drawn from the world's elven naming corpus
(the same source the existing hosts use); no given name or surname reuses an
existing host's name, and a surname never crosses villages. Within one village,
three bearers of a surname are mother and daughters who cohabit. Names were
checked part-by-part against the 21 host display names.

## Adult register, ages unstated

Every card and line treats each resident as an adult woman. No prose states a
year count or an apparent age; the Eolas (幻童) residents are written as adult
elves only. The `age`/`apparent_age` integers live in the profile and are never
echoed in dialogue or cards. Eolas residents share the branch's uniform
apparent age with the six existing Eolas hosts; Ciaran and Fionnen residents
carry varied adult apparent ages.

## Register and body frankness

The frankness lives in host speech and narration, grounded in the world
source's 性文化: the bathhouse, the open relationships, and each host's own
desire are stated plainly in her own words. Actor lines carry only questions and
never grant consent, initiate an act, or commit. Family members cohabit
platonically; sexual frankness concerns the village's open relationships or the
speaker's own body, never a family member. No line mentions an age, a command,
a mechanic, a UI element, 武俠 vocabulary, or a nonexistent place/item/title.

## Proper nouns

Every proper noun resolves to a registry row: the three settlements and their
nodes (`content/maps/settlements/*.yaml`), the shared spaces (溫泉浴場、蛛絲林、
岩屋坡、溪源、石階菜畦、藥草園、練刀場、村北古樹下、織房坡、溪池浴場、靶道、
花蕊蜜園、瞭望枝、林間菜圃、木作空地), and the neighbouring hosts named only
by their authored display names. No invented place, item, price or title.

## Deliverables covered

- 45 dialogue tables (`world/lore/dialogue/content/<village>_resident_*.yaml`),
  each with a non-empty greeting, 5–6 topics, and one affinity-locked optional
  scene with an in-character refusal; every formal scene begins with a complete
  actor utterance.
- 45 `NpcProfile`s under `world/lore/npc_profiles/<village>_residents.py`, 45
  `Resident` rows under `world/lore/residents/<village>.py`, 45 inventory
  `resident` rows and 45 `dialogue_table` rows, 45 editorial-ledger `resident`
  rows and 45 `dialogue_table` rows.
- 15 family home interiors + 15 editor layouts, regenerated
  `content/map-reference-context.json`.

## Verification

- `npc_content_lint.py` (dialogues and profiles): 0 errors; warnings are
  name-derived reduplication (拉拉/姊姊/妹妹) plus a few descriptive
  reduplication prompts.
- Registry load: 45 residents, 86 profiles, 83 dialogue rows, no unresolved
  references.
- Focused Evennia tests: `test_npc_profile_inventory`,
  `test_npc_editorial_review`, `test_npc_profile_slice_content`,
  `test_dialogue_assembly`, `test_resident_sync`, `test_dialogue_sources`,
  `test_authored_dialogue_runtime` — all pass (49 tests).
- `check_map_sources.py` — game-ready; `map_reference_context` current.
