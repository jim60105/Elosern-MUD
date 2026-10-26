# Middle-Exchange Dialogue Editorial Review

## 1. Scope and Canonical Ownership

This document records the line-by-line editorial and lore verification for the `authored-dialogue-content-middle-exchange` change (`altoria_jeweller`, `altoria_alchemist`, `altoria_merchant_master`).

### Profile and Place Bindings
- `altoria_jeweller` (place: 聖潔王都首飾坊, host: 艾蓮娜‧鴉丘, `service_id`: `altoria_jeweller`, `dialogue_key`: `altoria_jeweller`) -> `world/lore/dialogue/content/altoria_jeweller.yaml`
- `altoria_alchemist` (place: 聖潔王都鍊金坊, host: 希碧拉‧灰沼, `service_id`: `altoria_alchemist`, `dialogue_key`: `altoria_alchemist`) -> `world/lore/dialogue/content/altoria_alchemist.yaml`
- `altoria_merchant_hall` (place: 聖潔王都商會公所, host: 尤斯汀‧柯德溫, `service_id`: `altoria_merchant_master`, `dialogue_key`: `altoria_merchant_hall`) -> `world/lore/dialogue/content/altoria_merchant_master.yaml`

### Canonical Sources
- `tmp/story_settings/world_info.md`: authoritative world setting, covering:
  - Elven standing, rarity (~300 elves on the entire continent across three branches), lack of class/profession division, and respect above royalty.
  - The 光明教會 doctrine: Holy Seat in 聖潔王都, ancestral goddess of forest elves, sacred brothels/sanctuaries (聖所), and light-magic consecrated baptismal holy water (`受洗聖水`) that removes travel defilement.
  - 15–16th-century-with-magic economy, currency (1金 = 100銀 = 10000銅), and trading relationships between the human kingdom (王國) and empire/beastfolk.
- `world/lore/npc_profiles/altoria_trade.py`: persona cards, appearance, speech styles, and relationships for `altoria_jeweller`, `altoria_alchemist`, and `altoria_merchant_master`.
- `world/lore/settlements/places_altoria_middle.py`: room definitions, doorways, hosts, coordinates, and assortment bindings.
- `world/lore/settlements/assortments.py`: assortment definitions `capital_adornments` and `capital_remedies`.
- `world/lore/items/`: canonical items (`protective_ring`, `storage_pouch`, `gliding_cloak`, `silver_hairpin`, `wolf_fang_necklace`, `pilgrim_medallion`, `purified_pendant`, `fearless_brooch`, `apothecary_beads`, `passion_silk_choker`, `radiant_holy_emblem`, `healing_potion`, `greater_healing_potion`, `mana_potion`, `miners_bracing_broth`, `beastfolk_herbal_salve`, `passion_draught`, `baptismal_holy_water`).
- `world/rules/rulebook/clock.yaml` & `world/rules/dialogue_references.py`: canonical dayparts (`midnight`, `dawn`, `noon`, `dusk`).

---

## 2. Mandatory Lore Checks

### Elves Standing, Rarity, and Culture
- Canon: Total population ~300 elves across three branches (斐歐恩, 基亞蘭, 伊歐拉斯) compared to 30M humans and beastfolk. Elves are regarded as a rank above royalty (皇族之上的高級存在).
- Society & Culture: No fixed professions or class divisions; all elves are all-rounders. Physical attributes range 70–95. Elves have open relationships with no marriage system or concept of shame concerning nudity/sexuality.
- Host handling:
  - `altoria_jeweller`: References the `gliding_cloak` (`滑翔斗篷`) woven from rare elven spider silk (`精靈蛛絲`) brought by caravans across the central mountains, treating it with respectful admiration.
  - `altoria_alchemist`: Disclaims divine blessings and supernatural healing, focusing solely on mortal botanical and alchemy remedies.
  - `altoria_merchant_master`: Respects high-value cross-mountain caravan routes and does not reduce elves or their goods to mundane commodification.

### Religion (光明教會)
- Canon: Holy Seat located in 聖潔王都 (Sacred Capital Altoria). The principal deity is 光明女神 (ancestral goddess of the 斐歐恩 forest elves). Doctrine views physical union and pleasure as holy worship. Church operates 聖所 (sanctuaries) staffed by nuns and priests using light magic for contraception and blessings.
- Host handling:
  - `altoria_jeweller`: Explains that the `purified_pendant` (`淨化吊墜`) is washed in holy water, mentions `pilgrim_medallion` (`朝聖者銅符`) worn by pilgrims ascending the `聖階`, and notes that priests from the Grand Temple order `radiant_holy_emblem` (`光輝聖徽`).
  - `altoria_alchemist`: Strictly refuses to sell `baptismal_holy_water` (`受洗聖水`), explaining that divine purification belongs to the church. Points travelers up the `聖階` to the `聖所` counter in front of the Grand Temple (`大神殿前`) to cleanse wilderness defilement (`穢氣`), without claiming broad cures for poisons or curses.
  - `altoria_merchant_master`: Recognizes church jurisdiction and limits chamber authority strictly to trade, tariff review, and caravan coordination.

### 15–16th-Century-with-Magic Economy
- Currency is 1金 = 100銀 = 10000銅.
- Trade caravans travel from the kingdom's capital through `東門` (East Gate) along the official trade roads.
- Crafting and goods distribution: Craft guilds, merchants' guild hall (商會公所), and open markets function with written manifests, tariff reviews, and chalk boards. Prices are displayed on counter wooden placards or boards rather than recited.

---

## 3. Retained Service Behaviours and Assortment Consistency

- **altoria_jeweller (艾蓮娜‧鴉丘)**:
  - Assortment `capital_adornments`: stocks `silver_hairpin`, `wolf_fang_necklace`, `pilgrim_medallion`, `protective_ring`, `storage_pouch`, `gliding_cloak`, `purified_pendant`, `fearless_brooch`, `apothecary_beads`, `passion_silk_choker`, `radiant_holy_emblem`.
  - Service semantics: Buys back adornments covered by its assortment; asks provenance on odd or unusual heirlooms (`apothecary_beads`, `passion_silk_choker`).
  - Carried-item variant: `altoria_jeweller.topic_02` has a variant `inspect_protective_ring` with `kind: carries`, `item_key: protective_ring`, priority 10. The guest holds up the ring without asserting purchase history, and the host discusses its claw setting without buying, selling, or consuming the item.
  - Unconditional fallback: Discusses claw setting techniques for `purified_pendant`, `fearless_brooch`, and `radiant_holy_emblem` for visitors not carrying the item.

- **altoria_alchemist (希碧拉‧灰沼)**:
  - Assortment `capital_remedies`: stocks `healing_potion`, `greater_healing_potion`, `mana_potion`, `miners_bracing_broth`, `beastfolk_herbal_salve`, `passion_draught`.
  - Service semantics: Never oversells an effect, explains exact physical recovery (clearing dizziness and replenishing spent magic rather than referencing stat words like 魔力池), keeps red-label potent brews behind the counter with usage inquiries. Strictly refuses to stock or sell `baptismal_holy_water`, directing travelers up the `聖階` to the `聖所` counter at `大神殿前`.

- **altoria_merchant_master (尤斯汀‧柯德溫)**:
  - Attendant host with no assortment (`assortment_keys=()`).
  - Service semantics: Logs and coordinates caravans, reviews tariff regulations, arbitrates guild disputes; issues no escort contracts, posts no job listings, and guarantees no private cargo. Directs work-seekers to the Adventurers' Guild hall (`公會前`).
  - Guest address: The guest addresses the host as 你 in natural traveler register, while the host politely addresses the guest as 閣下.
  - Time-period variant: `altoria_merchant_hall.topic_01` has a variant `morning_caravan_dispatch` with `kind: time_period`, `start_daypart: dawn`, `end_daypart: noon`, priority 10. Describes the morning departure verification rush through `東門` without restricting business hours or locking the topic.
  - Unconditional fallback: Describes quarterly caravan scheduling and neutrality for any other time of day.

---

## 4. Per-Topic Intent and Scene Structure Review

### A. altoria_jeweller (艾蓮娜‧鴉丘)
1. **Opening Greeting**: Setting small talk in-character. Pauses polishing with her deerhide cloth, notes guest's collar/fingers, invites guest to inspect items in daylight or place old keepsakes on the velvet mat.
2. `altoria_jeweller.topic_01` (keyword: 飾品):
   - Actor asks about wearable accessories. Host presents silver hairpins, wolf fang necklaces, pilgrim medallions, and the rare protective ring, advising moderation in adornment.
3. `altoria_jeweller.topic_02` (keyword: 鑲工):
   - Variant `inspect_protective_ring` (`carries`: `protective_ring`, priority 10): Guest holds up their carried protective ring to ask about its craft without claiming where it was acquired. Host examines the ring on a velvet mat, praising the alloy claw setting that balances crystal stability and mana flow.
   - Fallback `altoria_jeweller.topic_02_fallback_scene`: Host explains claw setting principles using purified pendants (holy water silver), fearless brooches (chilled iron), and radiant holy emblems (smooth stone carving).
4. `altoria_jeweller.topic_03` (keyword: 奇物):
   - Actor inquires about rare magical curios. Host introduces imperial spatial storage pouches and gliding cloaks woven with central mountain elven spider silk.
5. `altoria_jeweller.topic_04` (keyword: 收飾):
   - Actor asks about selling old jewellery. Host confirms buy-back for items matching the shop's assortment, noting that heirloom items like apothecary beads or passion silk chokers require provenance inquiries.

### B. altoria_alchemist (希碧拉‧灰沼)
1. **Opening Greeting**: Setting small talk in-character. Peers out from behind bottle shelves with green-stained fingertips, asking whether the visitor has an injury or needs exploration remedies.
2. `altoria_alchemist.topic_01` (keyword: 藥劑):
   - Actor asks about bottled remedies. Host contrasts common healing potions for scrapes with greater healing potions for severe wounds, and explains mana potions for exhausted spellcasters in experiential terms (clearing dizziness and replenishing spent magic).
3. `altoria_alchemist.topic_02` (keyword: 外敷):
   - Actor asks about portable topical remedies. Host presents beastfolk herbal salve for contusions and swelling, and spicy miner's bracing broth for dispelling chill in deep pits.
4. `altoria_alchemist.topic_03` (keyword: 特殊):
   - Actor asks about potent specialized concoctions. Host inquires into the intended use and consent for passion draughts. Guest follows through by asking whether the draught works on guarded or strong-willed targets, and the host confirms it is completely useless on unwilling targets, forbidding guests from touching the red-label shelf.
5. `altoria_alchemist.topic_04` (keyword: 聖水):
   - Actor asks about negative-status-cleansing holy water. Host firmly denies selling baptismal holy water, gestures toward the upper terrace, and explains that holy water washes off travel defilement under church care. Directs the actor up the `聖階` to the `聖所` counter at `大神殿前`.

### C. altoria_merchant_hall (尤斯汀‧柯德溫)
1. **Opening Greeting**: Formal in-character welcome. Rises from the tariff table, greets with 閣下, and clearly states up front that the merchants' guild hall issues no escort commissions.
2. `altoria_merchant_hall.topic_01` (keyword: 商隊):
   - Variant `morning_caravan_dispatch` (`time_period`: `dawn` to `noon`, priority 10): Host notes the morning bustle of caravans preparing to exit `東門`, logging manifests without offering passenger escorts or cargo guarantees.
   - Fallback `altoria_merchant_hall.topic_01_fallback_scene`: Host explains quarterly chalk schedule management on the wall map, reiterating neutrality and refusal to broker private escorts.
3. `altoria_merchant_hall.topic_02` (keyword: 商路):
   - Actor asks about trade road divisions and gates. Host explains `東門` and `東市` trade distribution (grain, glass, foreign coins), workshop iron through `市場街`, and alchemy herbs through `東門`, referring route security inquiries to city guards.
4. `altoria_merchant_hall.topic_03` (keyword: 委託):
   - Actor asks about caravan protection jobs. Host explains why the hall lacks escort commission boards. Actor asks the host 「你會推薦何處？」 in natural traveler register, and host redirects to the Adventurers' Guild hall at `公會前`.
5. `altoria_merchant_hall.topic_04` (keyword: 會務):
   - Actor asks about the hall's civic duties. Host details arbitrating guild disputes, evaluating tariff codes, and quarterly accounting, inviting guest to inspect the open tariff ledger on the window table.

---

## 5. Style and Constraint Compliance Verification

- **In-Character Only**: No backticks, command names, UI controls, or meta-mechanic hints (e.g. no stat terms like 魔力池).
- **Punctuation & Script**: Full-width Traditional Chinese punctuation (，。、「」『』？！). Single space between CJK and ASCII alphanumeric characters. Zero instances of 「您」. No sentence-final 「的，」 or 「的。」. No mid-sentence colons. No reduplication.
- **Scene Shapes**: All 14 authored scenes (12 fallbacks + 2 variants) have 4–5 beats (within the 3–8 line limit), begin with a complete actor `speech` line, include narrative actions, and attribute host speech accurately.
- **Revision Tracking**: All scenes declare `revision: r2`.
- **Validation**:
  - `DIALOGUE_SNAPSHOT` length: 25.
  - `npc_content_lint.py`: 0 errors, 0 warnings across all 3 files.
  - `lint.sh` (zh-TW guideline): 0 errors across all 3 files.
  - Execution limit note: Browser manual playback harness login is unavailable; offline tests and logic verification pass.
