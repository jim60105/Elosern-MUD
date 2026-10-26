# Upper-Faith Dialogue Editorial Review

## 1. Scope and Canonical Ownership

This document records the line-by-line editorial and lore verification for the `authored-dialogue-content-upper-faith` change (`altoria_high_priestess`, `altoria_sanctum_deacon`).

### Profile and Place Bindings
- `altoria_temple` (place: 聖潔王都光明神殿, host: 艾莉安娜‧寒水, title: 聖潔王都光明神殿主祭) -> `world/lore/dialogue/content/altoria_high_priestess.yaml`
- `altoria_sanctum` (place: 聖潔王都聖所, host: 羅海西亞‧芬威克, title: 聖潔王都聖所執事) -> `world/lore/dialogue/content/altoria_sanctum_deacon.yaml`

### Canonical Sources
- `tmp/story_settings/world_info.md` §宗教與信仰 / §精靈族 (authoritative setting: 光明女神 is the ancestral deity of the 斐歐恩 forest elves; Holy Seat / 聖座 in 聖潔王都; 聖所 staffed by 修女 and 修士 using light magic for contraception; open worship/ministry/commerce; elven standing as beings above royalty, ~300 total population, natural view of body and intimacy).
- `world/lore/npc_profiles/altoria_upper.py` (persona cards, appearance, personality, voice lines, habits, connections).
- `world/lore/settlements/places_altoria_upper.py` (room names, room descriptions, doorway aliases, assortment bindings, service IDs, dialogue keys).
- `world/lore/settlements/assortments.py` (`sanctum_wares`).
- `world/lore/items/data_intimacy_items.py` and `world/lore/items/data_named_equipment.py` (canonical item names, price tables, sellable status).
- `skill://npc-dialogue-content`, `skill://chinese-content-writing-guideline`, `skill://writing-style-guideline`.

---

## 2. Mandatory Lore Checks

### Elves Standing, Rarity, and Culture
- **Canon**: Total population ~300 elves across three branches (斐歐恩, 基亞蘭, 伊歐拉斯) compared to ~30M mortal races (21M humans, 9M beastfolk). All three nations treat elves with highest reverence, as beings above royalty (皇族之上的高級存在). Elves have open relationships with no marriage system or bodily shame.
- **Church Origin**: The church's principal deity is 光明女神, the direct ancestral deity of the 斐歐恩 (forest elves). The holy scriptures explicitly record that elven uninhibited sexual customs represent the divine nature of the goddess, who regards intimacy and physical joy as the root of life and highest grace.
- **Host Handling**:
  - `altoria_high_priestess`: Topic 01 features a race-specific variant (`kind: race_is`, `race_key: elf`, priority 10) where the High Priestess bows in deep respect, recognizing the elf traveler as kin of the goddess's direct lineage (斐歐恩之民). She affirms that worldly ranks do not apply in the temple, and elves are welcome to participate, stroll, or contemplate in the light as they wish.
  - `altoria_sanctum_deacon`: Retains open, respectful commerce without generic fantasy puritanical embarrassment or condescending explanations.

### Religion (光明教會) and the Sanctum Ministry
- **Canon**:
  - The Holy Seat (聖座) is established in 聖潔王都 (Sacred Capital Altoria).
  - Worship (禮拜), sanctuary service (聖所事工), and sacred commerce (商店) are three counters under one single roof and one faith life.
  - The church operates 聖所 (sanctuaries / sacred houses), where nuns (修女) and monks/friars (修士) dedicate their bodies to faith as worship, serving with their bodies as a path of spiritual devotion.
  - Contraception is performed via light magic (光魔法進行避孕), seen as a divine gift / providence (攝理之術).
  - No invented purity dogma, no hidden back room, no invented sacrament, no fee or blessing the sources do not declare.
- **Host Handling**:
  - `altoria_high_priestess`:
    - Explains daily services (日課) at morning and dusk without requiring baptism, identity disclosure, or fees.
    - Blessings and prayers for journey safety are performed freely without charge; holy water is directed to the deacon's counter.
    - Publicly and openly explains the sanctum ministry without evasion, comparing its open ministry to a tavern serving wine—ordinary, holy, and continent-wide knowledge.
    - Directs all merchandise, holy water purchases, and ritual vessels to Deacon Rohaisya.
  - `altoria_sanctum_deacon`:
    - Welcoming, businesslike, and attentive. Directly presents wares on shelves with fixed price tags on the counter card.
    - Explains baptismal holy water as pure water blessed by High Priestess Eliana with light magic, carrying the temple's sun emblem wax seal.
    - Explains ritual vessels (censer of desire, holy mist) as instruments of holy reverence and joy.
    - Explains sanctuary arrangements: visitors meet nuns in consultation rooms to agree upon times, rooms, and services with mutual consent; holy prayers are directed back to the main hall.

---

## 3. Retained Service Behaviours and Assortment Consistency

- **Temple Services**:
  - Worship and prayer are completely open on first visit with zero barrier or fee.
  - Formal conversion / baptism is available upon request.
  - Blessings are free of charge.
- **Sanctum Shop Services & Assortment**:
  - Bound assortment: `sanctum_wares`.
  - Allowed item kinds: `TOY`, `POTION`, accessory equipment.
  - Exact assortment item keys and display names quoted in dialogue:
    - `nymph_buds_clamp` (花蒂銀夾)
    - `warm_honey_orb` (暖蜜魔導珠)
    - `hyperesthesia_charm` (尖銳觸感之飾)
    - `warmth_rune_egg` (恆溫魔法卵)
    - `tremor_crystal` (恆振晶)
    - `aphrodisiac_bath_salts` (催情浴鹽)
    - `kiss_of_goddess_mist` (女神之吻聖霧)
    - `censer_of_desire` (情欲香爐)
    - `embracing_vine` (纏枝魔藤)
    - `spark_candy` (微電跳蛋糖)
    - `slime_lube_gel` (史萊姆潤滑凝膠)
    - `hot_kiss_potion` (熱吻藥水)
    - `baptismal_holy_water` (受洗聖水)
  - Buy-back covers items belonging to the sanctum's own stock (`柜上有的東西，用舊了洗滌潔淨帶回櫃上，我也按成色折算收回`). No unstocked goods, raw ores, or weapons are purchased or promised.

---

## 4. Per-Topic Intent and Scene Structure Review

### A. altoria_high_priestess (艾莉安娜‧寒水)
1. **Opening Greeting**:
   - Closed lectionary, morning light through high arched windows. Solemn and serene greeting with 「願平安與你同在，旅人」, stating openly that worship, sanctuary, and shop are three open doors under one light.
2. `altoria_temple.topic_01` (keyword: 禮拜, label: 禮拜):
   - **Variant `elf_kin_worship`** (`kind: race_is`, `race_key: elf`, priority 10):
     - Actor asks about daily lections and whether visitors of different backgrounds share the same ritual.
     - Host bows in deep reverent respect to the elven visitor, citing the ancient lineage of the goddess given to the Fionnen, and affirms that elves may sit, stroll, or contemplate in peace.
   - **Fallback `altoria_temple.topic_01_scene`** (unconditional):
     - Actor asks about rules, schedule, and whether prior registration or lineage verification is required.
     - Host descends the lection steps, explaining that morning bell and dusk lections are open to all without registration, and one may stay for the sermon, speak privately, or request baptism.
3. `altoria_temple.topic_02` (keyword: 祝禱, label: 祝禱):
   - Actor asks about travel blessing fees and donations.
   - Host shakes her head, stating that the light's blessing takes no coin from travelers. She explains that lingering miasma can be washed away with baptismal holy water kept at the sanctum counter, preserving the separation between free grace and material vessels.
4. `altoria_temple.topic_03` (keyword: 聖所, label: 聖所):
   - Actor asks about the sanctum hall and how the devotional services are conducted.
   - Host turns toward the open colonnade, explaining calmly that the church views bodily intimacy and joy as divine worship. She notes that light magic is used for bodily conditioning and contraception, and confirms the open, continent-wide nature of the ministry.
5. `altoria_temple.topic_04` (keyword: 商店, label: 商店):
   - Actor asks about the goods counter in the church.
   - Host introduces Deacon Rohaisya Fenwick who manages holy water, ritual vessels, and spiritual instruments, directing purchases to the deacon and welcoming travelers back for prayer.

### B. altoria_sanctum_deacon (羅海西亞‧芬威克)
1. **Opening Greeting**:
   - Flips the ledger page with a warm greeting. Asks if items are for personal use or companions, pointing out the clear price tags on the counter board, and offering guidance on sanctuary services.
2. `altoria_sanctum.topic_01` (keyword: 賣什麼, label: 賣什麼):
   - Actor asks about the wares and categories available at the counter.
   - Host categorizes the assortment into wearable charms, intimate crystals, mood bath salts, mists, censers, lubricants, potions, and baptismal holy water, noting fixed board pricing and careful packaging.
3. `altoria_sanctum.topic_02` (keyword: 聖水, label: 聖水):
   - Actor asks about how baptismal holy water is used on travel and its cleansing effects.
   - Host shows the sealed glass vial with the temple's sun wax seal, explaining its light-magic blessing by the High Priestess, instructions on the label, and distinguishing free prayers in the main hall from purchasing bottled holy water.
4. `altoria_sanctum.topic_03` (keyword: 禮器, label: 禮器):
   - Actor asks about ritual censers and mist ornaments.
   - Host explains that desire censers and goddess mist serve both church liturgical practice and personal home devotion, with prices fixed on the board and clean buy-back available for used vessels.
5. `altoria_sanctum.topic_04` (keyword: 聖所事務, label: 聖所事務):
   - Actor asks about arranging sanctuary ministry services.
   - Host points down the quiet corridor, explaining that visitors meet welcoming nuns in private consultation rooms to agree on timing, rooms, and services by mutual consent, highlighting light-magic conditioning and contraception.

---

## 5. Style and Constraint Compliance Verification

- **In-Character Only**: No backticks, command tokens (`buy`, `pray`, `talk`), stats, mechanics, or UI hints.
- **Punctuation & Script**: Full-width Traditional Chinese punctuation throughout. Single space between CJK and ASCII alphanumeric characters.
- **Prohibited Patterns**: Zero instances of 「您」, sentence-final 「的，」/「的。」, calques (折入, 回填, 落地, 賦能), or banned wuxia terms (過招, 招式, 祕技, 拜師, 功夫, 掌門, 江湖, 客官).
- **Scene Shapes**: Every scene starts with a complete actor speech line, followed by narration and host responses, within 3–8 lines. No player commitments, vows, payments, or identity assertions.
- **Revision Tracking**: All authored scenes declare `revision: r2`.
- **Validation**:
  - `npc_content_lint.py`: Exit 0 with 0 errors.
  - `chinese-content lint.sh`: 0 errors.
  - `DIALOGUE_SNAPSHOT`: Exactly 25 profiles discovered.
- **Playback Harness Note**: In accordance with the change specifications, manual browser playback harness was not run due to broken local browser harness login; offline test modules, static codec checks, and contract gates verified the complete dataset.
