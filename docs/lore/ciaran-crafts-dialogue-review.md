# Ciaran Crafts Dialogue Editorial Review

## 1. Scope and Canonical Ownership

This document records the line-by-line editorial and lore verification for the `authored-dialogue-content-ciaran-crafts` change (`ciaran_hailiel`, `ciaran_vethiel`, `ciaran_gwenaera`).

### Profile and Place Bindings
- `ciaran_hailiel_home` (`place`: `海莉爾的家`, `host`: `海莉爾‧斯塔爾法爾`) -> `world/lore/dialogue/content/ciaran_hailiel.yaml`
- `ciaran_vethiel_home` (`place`: `維特希爾的家`, `host`: `維特希爾‧威爾德布瑞亞爾`) -> `world/lore/dialogue/content/ciaran_vethiel.yaml`
- `ciaran_gwenaera_home` (`place`: `格威娜拉的家`, `host`: `格威娜拉‧希爾維爾莉夫`) -> `world/lore/dialogue/content/ciaran_gwenaera.yaml`

Canonical Sources:
- `tmp/story_settings/world_info.md` (sections: `地理結構` `中央山脈`; `種族設定` `精靈族`; `宗教與信仰` `真相`; `特殊設定` `精靈與外界互動`).
- `world/lore/npc_profiles/ciaran_homes_a.py` (`ciaran_hailiel`, `ciaran_gwenaera`) and `ciaran_homes_b.py` (`ciaran_vethiel`).
- `world/lore/settlements/places_ciaran.py` (`ciaran_hailiel_home`, `ciaran_vethiel_home`, `ciaran_gwenaera_home`).
- `world/lore/settlements/assortments.py` (`elven_crafted_arms`, `elven_attire`, `elven_adornments`).
- `docs/lore/settlement-locations.md` (`暗影谷村` section and craft settlement differences).
- `skill://npc-dialogue-content`, `skill://chinese-content-writing-guideline`, `skill://writing-style-guideline`.

---

## 2. Mandatory Lore Checks

### Elves Standing, Rarity, and Absence of Commerce
- Canon: The entire continent has approximately 300 elves (roughly 100 in the Ciaran tribe of `暗影谷村`). Three human and beastfolk nations view elves as beings above royalty (`皇族之上的高級存在`) and extend the highest courtesy.
- Society and culture: Elves are all-rounders (`全能者`) with no fixed professions, no caste system, and no apprentice hierarchy. The village has no shops as commercial institutions, no opening hours, and no merchant bosses. Craftspeople make what they love in their own homes and share or trade goods with fellow villagers or rare visitors.
- Attitude toward outsiders: Elves are calm, self-contained, and unbothered (`不在意`) rather than curious or awed by outsiders. When a human visitor behaves with extreme deference or royal ceremony, Ciaran villagers remain polite and unruffled, finding excessive formality faintly puzzling.
- Body and clothing ethos: Elves possess zero concept of shame regarding nudity or the physical body. Other races look away out of awe and respect rather than moral prudery. Clothing serves to allow graceful, unimpeded physical movement and beauty.
- Host handling:
  - `ciaran_hailiel`: Operates in her home beside the drill field (`練刀場邊`). Forges blades out of passion; judges visitors by grip and footing rather than social rank.
  - `ciaran_vethiel`: Weaves atop weaving slope (`織房坡`). Bares her upper body naturally without embarrassment and speaks gently of spider-silk ritual vestments that showcase the body.
  - `ciaran_gwenaera`: Handcrafts adornments atop silver-leaf slope (`銀葉坡`). Welcomes visitors with casual liveliness, treating silver wire ornaments as personal artistic joy rather than commercial commodities.

### Religious Belief and Absence of Proselytising
- Canon: Elves never preach their faith to other races. The secret history of the three creator goddesses (`光明女神`, `暗之女神`, `知識女神`) remains known only among elves.
- Host handling: None of the three craftswomen lectures visitors on theology, ancestral deities, or Divine Arcana (`神之秘法`). The ritual robe (`elven_traditional_robe`) is described strictly as an elven ceremonial garment woven from valley spider silk.

---

## 3. Retained Service Behaviours and Assortment Consistency

All three hosts maintain their canonical place assortment bindings without alteration.
- `ciaran_hailiel_home`: Stocks `elven_crafted_arms` (`shadow_blade`, `shadow_blade_echo`).
  - Hailiel collects iron sand directly from the valley floor and refuses external scrap iron or unworked ore.
  - Buy-back accepts only retired blades of her own forging, refusing weapons made by others.
- `ciaran_vethiel_home`: Stocks `elven_attire` (`dark_elf_kimono`, `dark_elf_ninja_garb`, `elven_traditional_robe`, `elven_forest_veil`).
  - Vethiel starches and dyes her own threads, weaving cloth from dawn to evening stars.
  - Buy-back accepts only garments woven on her own loom to unpick thread for re-spinning, refusing outside clothing.
- `ciaran_gwenaera_home`: Stocks `elven_adornments` (`prism_charm`, `crescent_earring`).
  - Gwenaera twists silver wire, gathers shells from creeks, and polishes crystal sand.
  - Buy-back accepts only her own finished ornaments to reclaim silver and gems, refusing outside metals.
- Absolute exclusion of service delivery in prose: No line of dialogue delivers a free repair, a custom forging commission, tuition, or a price discount.

---

## 4. Per-Topic Intent and Scene Structure Review

### A. ciaran_hailiel_home (`海莉爾‧斯塔爾法爾`)
1. **Opening Greeting**: Hailiel cools a freshly quenched blade in water amidst the glow of her low hearth, observing the visitor's hands and stance beside the drill field.
2. `ciaran_hailiel_home.topic_01` (`keyword`: `鍛刀`, `label`: `鍛刀`):
   - Variant `human_guest` (`race_is`: `human`, `priority`: 10): A human visitor addresses the craftswoman with royal court deference. Hailiel calmly invites the visitor to stand straight without bowing, explaining that in the valley, bladecraft is judged by hand steadiness rather than court ceremony.
   - Fallback `ciaran_hailiel_home.topic_01_scene` (`revision`: `r2`): Actor inquires about the forging of shadow blades. Host explains multi-day folding and hammering of fierce valley iron sand into shadowsteel, inviting the guest to test grip and balance.
3. `ciaran_hailiel_home.topic_02` (`keyword`: `影刀`, `label`: `影刀`):
   - Fallback `ciaran_hailiel_home.topic_02_scene` (`revision`: `r2`): Actor asks about the shorter blade beside the anvil. Host explains that `shadow_blade_echo` (`暗影鋼刀‧影`) is paired with the main blade, quenched in first frost spring water, displaying faint shadow trailing only in swift motion.
4. `ciaran_hailiel_home.topic_03` (`keyword`: `鐵料`, `label`: `鐵料`):
   - Fallback `ciaran_hailiel_home.topic_03_scene` (`revision`: `r2`): Actor asks whether host buys outside raw ores. Host explains she exclusively shovels and pans iron sand from the valley floor, buying back only intact blades of her own make.
5. `ciaran_hailiel_home.topic_04` (`keyword`: `用刀`, `label`: `用刀`):
   - Fallback `ciaran_hailiel_home.topic_04_scene` (`revision`: `r2`): Actor asks about wielding techniques observed from the drill field. Host references neighbor Teliel (`泰莉爾‧菲溫德`), highlighting practical movement coordination between twin blades and warning that unfitted blades hinder their wielder.

### B. ciaran_vethiel_home (`維特希爾‧威爾德布瑞亞爾`)
1. **Opening Greeting**: Vethiel pauses her wooden loom shuttle, turns from the warp threads with dyed purple silk around her fingers, and asks what color the traveler favors.
2. `ciaran_vethiel_home.topic_01` (`keyword`: `織衣`, `label`: `織衣`):
   - Fallback `ciaran_vethiel_home.topic_01_scene` (`revision`: `r2`): Actor asks about garments produced on the loom. Host lists short robes, battle dress, ritual spider-silk robes, and morning dew veils, encouraging the visitor to touch the weaves.
3. `ciaran_vethiel_home.topic_02` (`keyword`: `戰衣`, `label`: `戰衣`):
   - Fallback `ciaran_vethiel_home.topic_02_scene` (`revision`: `r2`): Actor inquires about the ink-black battle garment (`精靈戰鬥服飾`). Host explains its close-fitting cut, joint ease, and minimal coverage designed for unhindered agility in forest hunts.
4. `ciaran_vethiel_home.topic_03` (`keyword`: `禮袍`, `label`: `禮袍`):
   - Fallback `ciaran_vethiel_home.topic_03_scene` (`revision`: `r2`): Actor asks about the gossamer-thin white robe (`精靈傳統服飾`) and forest veil (`精靈森林輕紗`). Host notes the robe is woven from spider silk gathered by Valwyn for village rituals, explaining that elves take pride in bodily beauty while outside travelers often blush.
5. `ciaran_vethiel_home.topic_04` (`keyword`: `舊衣`, `label`: `舊衣`):
   - Fallback `ciaran_vethiel_home.topic_04_scene` (`revision`: `r2`): Actor asks about buy-back of worn garments. Host confirms taking back her own woven robes to unpick intact threads for re-spinning, refusing outside clothing.

### C. ciaran_gwenaera_home (`格威娜拉‧希爾維爾莉夫`)
1. **Opening Greeting**: Gwenaera sits behind her work table atop silver-leaf slope twisting silver wire, enthusiastically presenting two newly finished silver floral coils for the guest to evaluate.
2. `ciaran_gwenaera_home.topic_01` (`keyword`: `綴飾`, `label`: `綴飾`):
   - Fallback `ciaran_gwenaera_home.topic_01_scene` (`revision`: `r2`): Actor asks about the craftswoman's ornaments. Host explains hand-twisting silver wire, gathering shells from creeks, and grinding crystal sand, hanging finished pieces along the window cord for villagers and travelers.
3. `ciaran_gwenaera_home.topic_02` (`keyword`: `晶符`, `label`: `晶符`):
   - Fallback `ciaran_gwenaera_home.topic_02_scene` (`revision`: `r2`): Actor inquires about the prismatic crystal pendant (`三稜晶符`). Host explains it refracts incident light into three distinct bands using ancestral grinding methods, clarifying that it carries aesthetic beauty rather than mystical magic.
4. `ciaran_gwenaera_home.topic_03` (`keyword`: `耳環`, `label`: `耳環`):
   - Fallback `ciaran_gwenaera_home.topic_03_scene` (`revision`: `r2`): Actor asks about the crescent earrings (`月牙耳環`). Host notes this is her most practiced craft, mentioning that silk-gatherer Valwyn wears earrings from the same batch, and describes airing them under silver leaves to catch their luster.
5. `ciaran_gwenaera_home.topic_04` (`keyword`: `舊飾`, `label`: `舊飾`):
   - Fallback `ciaran_gwenaera_home.topic_04_scene` (`revision`: `r2`): Actor asks what to do if silver wires snap or ornaments are no longer needed. Host describes mending her own work and taking back charms to recycle silver, while refusing outside jewelry.

---

## 5. Style and Constraint Compliance Verification

- **In-Character Only**: Zero mentions of commands, backticks, syntax tokens, attribute numbers, or UI elements.
- **Traditional Chinese Formatting**: Full-width punctuation throughout. Single space separating CJK characters from alphanumeric strings.
- **Prohibited Terminology and Grammar**:
  - Zero instances of `「您」`.
  - Zero instances of sentence-final `「的，」` or `「的。」`.
  - Zero instances of banned wuxia terms (`過招`, `劍招`, `招式`, `祕技`, `拜師`, `功夫`, `掌門`, `江湖`, `客官`).
  - Zero instances of calques (`折入`, `回填`, `賦能`, `落地`, `拉齊`, `深潛`).
  - Zero instances of reduplications (`疊字`) flagged by lint.
- **Scene Shapes**: All 13 authored scenes (12 fallbacks + 1 variant) start with a complete actor speech line, hold between 6 and 7 lines, and declare `revision: r2`.
- **Variants and Conditions**: Exactly one variant (`variant_id`: `human_guest`, `priority`: 10, `race_is`: `human`) under `ciaran_hailiel_home.topic_01`, accompanied by an unconditional fallback.

### Proper Noun to Canonical Registry Mapping

| Proper Noun | Type | Canonical Registry Source |
|---|---|---|
| 暗影谷村 | Settlement | `world/lore/settlements/places_ciaran.py` (`village_ciaran`) |
| 中央山脈 | Region | `tmp/story_settings/world_info.md` §地理結構 |
| 海莉爾‧斯塔爾法爾 | NPC Host | `world/lore/npc_profiles/ciaran_homes_a.py` (`ciaran_hailiel`) |
| 海莉爾的家 | Place | `world/lore/settlements/places_ciaran.py` (`ciaran_hailiel_home`) |
| 練刀場 | Exterior / Landmark | `world/lore/settlements/places_ciaran.py` |
| 暗影鋼 | Material lore | `world/lore/npc_profiles/ciaran_homes_a.py` |
| 暗影鋼刀 | Item (`shadow_blade`) | `world/lore/settlements/assortments.py`, `world/lore/items/data_named_equipment.py` |
| 暗影鋼刀‧影 | Item (`shadow_blade_echo`) | `world/lore/settlements/assortments.py`, `world/lore/items/data_named_equipment.py` |
| 泰莉爾‧菲溫德 | NPC Neighbor | `world/lore/npc_profiles/ciaran_homes_a.py` (`ciaran_teliel`), `places_ciaran.py` |
| 維特希爾‧威爾德布瑞亞爾 | NPC Host | `world/lore/npc_profiles/ciaran_homes_b.py` (`ciaran_vethiel`) |
| 維特希爾的家 | Place | `world/lore/settlements/places_ciaran.py` (`ciaran_vethiel_home`) |
| 織房坡 | Exterior / Landmark | `world/lore/settlements/places_ciaran.py` |
| 精靈短袍傳統服飾 | Item (`dark_elf_kimono`) | `world/lore/settlements/assortments.py`, `world/lore/items/data_named_equipment.py` |
| 精靈戰鬥服飾 | Item (`dark_elf_ninja_garb`) | `world/lore/settlements/assortments.py`, `world/lore/items/data_named_equipment.py` |
| 精靈傳統服飾 | Item (`elven_traditional_robe`) | `world/lore/settlements/assortments.py`, `world/lore/items/data_named_equipment.py` |
| 精靈森林輕紗 | Item (`elven_forest_veil`) | `world/lore/settlements/assortments.py`, `world/lore/items/data_regional_equipment.py` |
| 瓦爾溫‧斯蒂爾瓦特爾 | NPC Neighbor | `world/lore/npc_profiles/ciaran_homes_b.py` (`ciaran_valwyn`), `places_ciaran.py` |
| 蛛絲 / 精靈蛛絲 | Material (`elven_spider_silk`) | `world/lore/settlements/assortments.py`, `world/lore/items/data_armor_accessories_materials.py` |
| 格威娜拉‧希爾維爾莉夫 | NPC Host | `world/lore/npc_profiles/ciaran_homes_a.py` (`ciaran_gwenaera`) |
| 格威娜拉的家 | Place | `world/lore/settlements/places_ciaran.py` (`ciaran_gwenaera_home`) |
| 銀葉坡 | Exterior / Landmark | `world/lore/settlements/places_ciaran.py` |
| 三稜晶符 | Item (`prism_charm`) | `world/lore/settlements/assortments.py`, `world/lore/items/data_armor_accessories_materials.py` |
| 月牙耳環 | Item (`crescent_earring`) | `world/lore/settlements/assortments.py`, `world/lore/items/data_named_equipment.py` |
| 谷底 | Geographic Landmark | `world/lore/npc_profiles/ciaran_homes_a.py`, `places_ciaran.py` |

---

## 6. Offline Verification and Browser Playback Note

- **Browser Playback Constraint**: Browser manual playback was not executed in this worktree session because the headless CI environment lacks an active graphical display session.
- **Offline Equivalent Verification**:
  - Validated that `DIALOGUE_SNAPSHOT` loads exactly 25 entries without error.
  - Executed `npc_content_lint.py --places --strict` across all three YAML files with 0 errors and 0 warnings.
  - Executed Traditional Chinese language linter with 0 errors across all owned files.
  - Verified condition references and presence of all 12 stable topic IDs via `world.rules.dialogue_references`.
  - Focused automated test suites in `world.lore` and `world.rules` executed green.
