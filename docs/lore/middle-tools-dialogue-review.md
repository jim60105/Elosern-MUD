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
   - Actor asks about weapons. Host lists common swords, daggers, throwing axes, longbows, and apprentice staves, noting river water quenching and sturdy grip.
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
5. `altoria_tailor.topic_04` (keyword: 收購):
   - Actor asks about buy-back of old clothing. Host confirms buy-back for restitching and re-lining into fresh gear.

---

## 5. Style and Constraint Compliance Verification

- **In-Character Only**: No backticks, command names (`rest`, `buy`, `talk`), or UI mentions.
- **Punctuation & Script**: Full-width Traditional Chinese punctuation (，。、「」『』？！). Space between CJK and ASCII alphanumeric characters.
- **Prohibited Patterns**: Zero instances of 「您」, sentence-final 「的，」/「的。」, or calques (折入, 回填, 落地, 賦能).
- **Scene Shapes**: All formal scenes start with complete actor `speech` line, followed by host responses and stage narration, within 3–8 lines.
- **Revision Tracking**: All authored scenes across all three hosts declare `revision: r2`.

---

## 6. Rewrite (2026-11-20)

Wholesale prose rewrite of the three hosts under `authored-dialogue-content-middle-tools`. Every scene body, variant and greeting was replaced; all `topic_id`, `scene_id`, `keyword`, `label`, condition operands, variant priorities and speaker values are unchanged. Each rewritten scene moved `r2` → `r3`. Item display names were re-read from `content/items/` and corrected where the old prose drifted: `camp_ward_kit` is 露營魔導具 (not 營地防護石), `dragon_scale_fragment` is 龍鱗碎片 (not 地龍鱗片), `knight_platemail` is 騎士全套板甲, `archmage_mending_robe` is 大術師補綴長袍. The tailor's adult frankness is confined to the vestment cut and fit; the merchant and smith stay salt-of-the-earth traders with no body focus.

### A. altoria_general_store (瑪爾特‧金秤)

- **Opening Greeting** (r3): Ledger, charcoal marks, then the same out-or-return opener, now split by the board price for gear versus the scale for appraisal.
- `altoria_general_store.topic_01` (賣什麼, r3): Actor asks what the shop sells. Host lists 魔法燈, 附魔羅盤, 迷宮探照符 and 露營魔導具 (the camp warding kit, named by what it unfolds into), then 粗鐵礦 and 魔獸結晶 as smithing material. Actor's discount question is answered with the board-price refusal and the thirty-year brass scale. Causal bridge: the actor's second turn follows the item list directly.
- `altoria_general_store.topic_02` (材料, r3): Actor asks about buy-back and the rate. Host answers with the declared materials (哥布林耳朵, 史萊姆黏液, 巨魔尖牙, 地龍鱗片) weighed on the brass scale. The actor's follow-up "那你架上也有稀罕的材料賣嗎" bridges to the top-shelf rare goods: 魔導晶核, 龍鱗碎片 and 精靈蛛絲 from the central mountains.
- `altoria_general_store.topic_03` (行頭, r3): First-trip advice, each item earning its purpose: 魔法燈 for the dark, 附魔羅盤 for lost paths, 迷宮探照符 for the stretch ahead, 露營魔導具 for a wind-and-rain-proof tent, 通訊法螺 to find a separated companion. Actor's "第一次出城" is answered before the topic closes.
- `altoria_general_store.topic_04` (飾品藥水, r3): Actor asks about accessories and remedies; host redirects to 艾蓮娜's 首飾坊 (隔壁) and 希碧拉's 鍊金坊 (東市). The follow-up about 受洗聖水 bridges to 大神殿's 聖所 counter. The nun's bodily-offering line was dropped to keep the merchant plain.

### B. altoria_forge (維爾登‧黑潭)

- **Opening Greeting** (r3): Hammer on the anvil, the weapon-and-dominant-hand question kept laconic.
- `altoria_forge.topic_01` (兵器, r3): Actor asks for a self-defence blade. Host lists 普通劍, 鐵短刀, 狩獵擲斧, then 獵手長弓 and 見習術師法杖 for reach, with the board price on the door. Actor's quality question is answered with river-water quenching, the leather grip and the thumbnail-and-tap test. The "絕不會誤事" boast was dropped.
- `altoria_forge.topic_02` (好貨, r3): Actor asks for the best. Host names 騎士制式長劍 from the training-ground orders, then, on the actor's follow-up, the 魔導長劍 with the enchanter's infused essence described as provenance, not an offered service.
- `altoria_forge.topic_03` (賣鐵, r3): Actor asks about selling old weapons; host accepts intact weapons and refuses raw ore, sending 粗鐵礦 to 瑪爾特's 雜貨店 scales on 市場街.
- `altoria_forge.topic_04` (保養, r3): The `basic_swordplay` variant (priority 10, condition unchanged) recognises the swordsman's grip and calluses and gives cleaning, oiling, whetstone and discard advice; the fallback keeps the two whetstones and the no-repair, no-rejoin rule.

### C. altoria_tailor (妮絲塔‧狐溪)

- **Opening Greeting** (r3): Surfaces from the fabric, sizes up the guest's cut, asks where the journey leads.
- `altoria_tailor.topic_01` (衣甲, r3): Actor asks for road armour. Host presents 硬皮甲 and 鎖子甲 (every iron ring from the smith next door), then 術師長袍, 鐵盾 and 騎士全套板甲 on the actor's caster-and-squire follow-up.
- `altoria_tailor.topic_02` (旅裝, r3): Fit against chafing (肩頭勒緊, 褲襠磨腿), a well-fitted 皮甲 over three rough sets, and 大術師補綴長袍 for academy casters, each reason given.
- `altoria_tailor.topic_03` (禮服, r3): The noble variant (priority 10, condition unchanged) keeps the formal register and the temple order line; the fallback names the 修女聖袍 open front to the navel with the 聖徽細鏈 waist, and the 聖女聖袍 sheer silk, plus the discreet custom lace fitting. The 光明女神 ritual attribution was dropped in favour of the registry's own "聖女親手繡成" wording.
- `altoria_tailor.topic_04` (收購, r3): Actor asks about old armour and clothes; host takes back what she sold, undoes the old seams and re-tans them, with the wash-before-you-bring rule.

### Final revision ledger

| Host | Greeting | topic_01 | topic_02 | topic_03 | topic_04 |
| --- | --- | --- | --- | --- | --- |
| altoria_merchant | r3 | r3 | r3 | r3 | r3 |
| altoria_blacksmith | r3 | r4 | r4 | r3 | r3 (variant + fallback) |
| altoria_tailor | r3 | r3 | r3 | r3 (variant + fallback) | r3 |

Lint: `npc_content_lint.py` 0 errors for all three files (0 warnings for the merchant and smith; the tailor's `北大道` is a `--places` prompt, grounded in the tailor's own room description `content/maps/interiors/altoria_tailor.yaml`). `chinese-content-writing-guideline/lint.sh` 0 errors for all three (warnings are YAML keys and ordinary dialogue question marks).
