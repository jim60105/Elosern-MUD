# Middle-Tools Dialogue Editorial Review

## 1. Scope and Canonical Ownership

This document records the line-by-line editorial and lore verification for the `authored-dialogue-content-middle-tools` change (`altoria_merchant`, `altoria_blacksmith`, `altoria_tailor`).

### Profile and Place Bindings
- `altoria_general_store` (place: 阿爾托利亞雜貨店, host: 瑪爾特‧金秤) -> `world/lore/dialogue/content/altoria_merchant.yaml`
- `altoria_forge` (place: 聖潔王都鍛造鋪, host: 維爾登‧黑潭) -> `world/lore/dialogue/content/altoria_blacksmith.yaml`
- `altoria_tailor` (place: 聖潔王都裁縫坊, host: 妮絲塔‧狐溪) -> `world/lore/dialogue/content/altoria_tailor.yaml`

Canonical Sources:
- `tmp/story_settings/world_info.md` (authoritative setting: elven standing/rarity, religion, 15–16th-century-with-magic economy, currency 1金=100銀=10000銅).
- `world/lore/npc_profiles/altoria_trade.py` (persona cards, voice lines, appearance, personality, habits).
- `world/lore/settlements/places_altoria_middle.py` (room name, host details, assortment bindings).
- `world/lore/settlements/assortments.py` (`general_sundries`, `common_arms`, `common_outfits`).
- `skill://npc-dialogue-content`, `skill://chinese-content-writing-guideline`, `skill://writing-style-guideline`.

---

## 2. Mandatory Lore Checks

### Elves Standing, Rarity, and Culture
- Canon: Total population ~300 elves across three branches (斐歐恩, 基亞蘭, 伊歐拉斯) compared to 30M humans and orcs. Elves are regarded as a rank above royalty (皇族之上的高級存在).
- Society & Culture: No fixed professions or class divisions; all elves are all-rounders (全能者). Physical attributes range 70–95. Elves have open relationships with no marriage system or concept of shame concerning nudity/sexuality.
- Host handling:
  - `altoria_merchant`: Mentions rare elven spider silk (`elven_spider_silk`) brought from the central mountains by caravans as a high-value material on the top shelf, treating it with respectful caution.
  - `altoria_blacksmith`: Respects true physical craftsmanship and steel; does not lecture on rules or trivialize elven arms.
  - `altoria_tailor`: Notes that ancient vestment patterns were handed down from the elven ancestral goddess (光明女神), treated with reverence. No host implies elves are subordinate or divided into mortal working classes.

### Religion (光明教會)
- Canon: Holy Seat located in 聖潔王都 (Sacred Capital Altoria). The principal deity is 光明女神 (ancestral goddess of the 斐歐恩 forest elves). Doctrine views physical union and pleasure as holy worship. Church operates 聖所 (sanctuaries) staffed by nuns and priests using light magic for contraception.
- Host handling:
  - `altoria_merchant` topic 04 directs inquiries about baptismal holy water (`受洗聖水`) to the Grand Temple and holy sanctuaries in the upper terrace, acknowledging the nuns' holy devotion through bodily offering.
  - `altoria_tailor` topic 03 references tailoring orders from the Grand Temple for nuns' vestments (`修女聖袍`, designed for openness following the church's sacred doctrines) and saintess garments (`聖女聖袍`).

---

## 3. Retained Service Behaviours and Assortment Consistency

- Shopping Services: Retained completely unchanged.
  - `altoria_general_store`: Stocks `general_sundries` (`magic_lamp`, `healing_herb`, `rough_iron_ore`, `beast_crystal`, `evernight_shard`, `mana_core`, `dragon_scale_fragment`, `elven_spider_silk`, `spirit_dew`, `enchanted_compass`, `dungeon_flare_talisman`, `beastfolk_signal_conch`, `camp_ward_kit`, `goblin_ear`, `slime_residue`, `earth_drake_scale`, `troll_fang`). Buy-back buys materials/sundries from this assortment only. No weapons, armor, or potions sold or promised.
  - `altoria_forge`: Stocks `common_arms` (`plain_sword`, `iron_dagger`, `hunting_throwing_axe`, `hunters_longbow`, `apprentice_focus_staff`, `knight_blade`, `magic_sword`, military swords). Buy-back covers weapons only; raw ore is directed to the general store. No repairs, bespoke crafting, or bargaining.
  - `altoria_tailor`: Stocks `common_outfits` (`leather_armor`, `mage_robe`, `chainmail`, `iron_shield`, `knight_platemail`, `archmage_mending_robe`, `enticing_lace_set`, `sister_vestments`, `saintess_vestments`). Buy-back covers wearable outfits only.

---

## 4. Per-Topic Intent and Scene Structure Review

### A. altoria_general_store (瑪爾特‧金秤)
Adopted verbatim from the refined model draft `/var/home/jim60105/repos/MUD/tmp/altoria_general_store_refined.yaml`.
1. **Opening Greeting**: Setting small talk in-character. Asks if actor is leaving the city or returning; points to shelves and offers fair appraisal.
2. `altoria_general_store.topic_01` (keyword: 賣什麼):
   - Actor asks about available exploration goods. Host lists lanterns, compasses, flares, camp warding kits, and raw ores/crystals for smithing, stating fixed board prices without haggling.
3. `altoria_general_store.topic_02` (keyword: 材料):
   - Actor inquires about monster materials buy-back. Host confirms weighing goblin ears, slime residue, troll fangs, and drake scales on brass scales, and highlights rare mana cores and elven spider silk.
4. `altoria_general_store.topic_03` (keyword: 行頭):
   - Actor asks what a beginner should prepare. Host gives practical advice on lanterns, compasses, flare talismans, camp ward stones, and signal conches, explaining the purpose of each item.
5. `altoria_general_store.topic_04` (keyword: 飾品藥水):
   - Actor asks about accessories and potions. Host points to neighboring jeweller (艾蓮娜) and alchemist (希碧拉), and directs baptismal holy water inquiries to the Grand Temple's holy sanctuary.

### B. altoria_forge (維爾登‧黑潭)
Aligned to the refined standard with complete turns, grounded explanations, and laconic blacksmith attitude.
1. **Opening Greeting**: Short, blunt. Asks what weapon the actor wields and dominant hand amidst striking anvil sparks.
2. `altoria_forge.topic_01` (keyword: 兵器):
   - Actor asks about weapons. Host lists common swords, daggers, throwing axes, longbows, and apprentice staves, noting the plain water quenching and sturdy grip.
3. `altoria_forge.topic_02` (keyword: 好貨):
   - Actor asks for premium equipment. Host highlights the knight's service blade made for the training grounds and the element-infused magic sword.
4. `altoria_forge.topic_03` (keyword: 賣鐵):
   - Actor asks about selling old weapons. Host accepts intact weapons matching assortment, refusing raw unworked ore and redirecting to the general store's scales.
5. `altoria_forge.topic_04` (keyword: 保養):
   - Variant `swordsman_advice` (`SkillOwned`: `basic_swordplay` >= 1, priority 10): Host recognizes swordsman grip and posture, offering advice on cleaning, oiling, whetstones, and discarding cracked blades.
   - Fallback `altoria_forge.topic_04_fallback_scene`: Laconic instructions on whetstones, oiling, and replacing cracked blades.

### C. altoria_tailor (妮絲塔‧狐溪)
Aligned to the refined standard with enthusiastic conversational tone, attentive fitting details, and proud craft heritage.
1. **Opening Greeting**: Welcoming, chatty. Remarks on actor's clothing cut and asks about travel plans.
2. `altoria_tailor.topic_01` (keyword: 衣甲):
   - Actor asks about protective clothing. Host presents leather armor, chainmail, mage robes, and knight platemail, detailing movement comfort and protection.
3. `altoria_tailor.topic_02` (keyword: 旅裝):
   - Actor asks about long travel apparel. Host emphasizes proper fit to prevent chafing on the road and highlights robes for academy magic scholars.
4. `altoria_tailor.topic_03` (keyword: 禮服):
   - Variant `noble_formalwear` (`SocialIdentityIs`: `noble`, priority 10): Host acknowledges noble patron and discusses banqueting attire and Grand Temple holy vestments.
   - Fallback `altoria_tailor.topic_03_fallback_scene`: Host discusses orders from north avenue nobles, church nuns' open holy robes, saintess vestments, and confidential custom lace intimate wear fitting.
5. `altoria_tailor.topic_04` (keyword: 收衣):
   - Actor asks about buy-back of old clothing. Host confirms buy-back for restitching and re-lining into fresh gear.

---

## 5. Style and Constraint Compliance Verification

- **In-Character Only**: No backticks, command names (`rest`, `buy`, `talk`), or UI mentions.
- **Punctuation & Script**: Full-width Traditional Chinese punctuation (，。、「」『』？！). Space between CJK and ASCII alphanumeric characters.
- **Prohibited Patterns**: Zero instances of 「您」, sentence-final 「的，」/「的。」, or calques (折入, 回填, 落地, 賦能).
- **Scene Shapes**: All formal scenes start with complete actor `speech` line, followed by host responses and stage narration, within 3–8 lines.
- **Revision Tracking**: All authored scenes across all three hosts declare `revision: r2`.
