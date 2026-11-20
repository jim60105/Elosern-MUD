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
- **Church Origin**: The church's principal deity is 光明女神, the direct ancestral deity of the 斐歐恩 (forest elves). The holy scriptures record that elven uninhibited sexual customs represent the divine nature of the goddess, who regards intimacy and physical joy as the root of life and highest grace.
- **Host Handling**:
  - `altoria_high_priestess`: Topic 01 features an elven guest variant (`kind: race_is`, `race_key: elf`, priority 10) where the High Priestess bows in polite, composed respect, recognizing the elf traveler as kin of the goddess's direct lineage (斐歐恩族的始祖神祇). She affirms that the temple's tradition comes from that heritage, and elven travelers may sit for the lection, walk through the hall, or contemplate in the light as they wish.
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
    - Composed, polite, modern formal zh-TW with complete sentences.
    - Explains daily services (日課) at morning and dusk without requiring baptism, identity disclosure, or fees.
    - Blessings and prayers for journey safety are performed freely without charge; holy water is directed to the deacon's counter.
    - Publicly and plainly explains the sanctum ministry without evasion, comparing its open ministry to a tavern serving wine—ordinary, holy, and continent-wide knowledge.
    - Directs all merchandise, holy water purchases, and ritual vessels to Deacon Rohaisya.
  - `altoria_sanctum_deacon`:
    - Welcoming, businesslike, and chatty with natural spoken zh-TW particles (喔／啦／吧／嘛). Directly presents wares on shelves with fixed price tags on the counter card.
    - Explains baptismal holy water as pure water blessed by High Priestess Eliana with light magic, with usage instructions on the label.
    - Explains ritual vessels (censer of desire, holy mist) as instruments for relaxation and liturgy.
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
  - Buy-back covers items belonging to the sanctum's own stock (`要是從前在我這兒買的器物，用舊了洗乾淨拿回來，我也按成色折算收回喔`). No unstocked goods, raw ores, or weapons are purchased or promised.

---

## 4. Per-Topic Intent and Scene Structure Review

### A. altoria_high_priestess (艾莉安娜‧寒水)
1. **Opening Greeting**:
   - Closed lectionary, morning light through high windows. Calm and courteous greeting with 「願平安與你同在，旅人」, stating plainly that worship, sanctuary, and shop are three open counters under one roof.
2. `altoria_temple.topic_01` (keyword: 禮拜, label: 禮拜):
   - **Variant `elf_kin_worship`** (`kind: race_is`, `race_key: elf`, priority 10):
     - Actor asks about daily lections and whether elven visitors have special rules.
     - Host bows in polite respect, noting that the Light Goddess is the ancestral deity of the Fionnen elves and temple traditions stem from that heritage. She invites the elf to sit, walk, or contemplate freely, with two complete actor turns.
   - **Fallback `altoria_temple.topic_01_scene`** (unconditional):
     - Actor asks about schedule and registration for lections.
     - Host steps down to the pews, explaining morning bell and sunset lections require no registration or baptism, with two complete conversational beats.
3. `altoria_temple.topic_02` (keyword: 祝禱, label: 祝禱):
   - Actor asks about prayer fees for journey safety and cleansing miasma.
   - Host explains that prayers are completely free of charge at the lectern, while bottled holy water for travel is kept at the deacon's shop counter.
4. `altoria_temple.topic_03` (keyword: 聖所, label: 聖所):
   - Actor asks if the sanctuary is beside the hall and about its ministry.
   - Host explains the sanctuary directly under the same roof, confirming bodily service as worship and light magic for contraception, and points the actor down the hallway to the duty nuns.
5. `altoria_temple.topic_04` (keyword: 商店, label: 商店):
   - Actor asks about the goods counter in the church and buying holy water.
   - Host introduces Deacon Rohaisya Fenwick who handles holy water, ritual vessels, and goods with board prices, and invites travelers back for prayer.

### B. altoria_sanctum_deacon (羅海西亞‧芬威克)
1. **Opening Greeting**:
   - Flips the ledger page with a light smile and informal zh-TW particles. Asks if items are for personal use or gifts, pointing to price tags on the board.
2. `altoria_sanctum.topic_01` (keyword: 賣什麼, label: 賣什麼):
   - Actor asks about available wares and pricing.
   - Host categorizes the wares on both shelves, lists exact assortment items, and explains fixed board prices across two conversational turns.
3. `altoria_sanctum.topic_02` (keyword: 聖水, label: 聖水):
   - Actor asks how baptismal holy water is used and kept during travel.
   - Host shows the bottle, explains how to wipe wrists and forehead, notes that prayers in the hall are free, while bottled water is paid at the counter.
4. `altoria_sanctum.topic_03` (keyword: 禮器, label: 禮器):
   - Actor asks about ritual censers and mist vessels and recycling old items.
   - Host explains their use in ceremony and at home, confirms clean buy-back for cash, and keeps dialogue lively and practical.
5. `altoria_sanctum.topic_04` (keyword: 聖所事務, label: 聖所事務):
   - Actor asks how sanctuary service arrangements are made.
   - Host explains that duty nuns meet guests through the corridor to agree on rooms, times, and services by mutual consent, highlighting light-magic care and contraception.

---

## 5. Style and Constraint Compliance Verification

- **In-Character Only**: No backticks, command tokens (`buy`, `pray`, `talk`), stats, mechanics, or UI hints.
- **Punctuation & Script**: Full-width Traditional Chinese punctuation throughout. Single space between CJK and ASCII alphanumeric characters.
- **Prohibited Patterns**: Zero instances of 「您」, sentence-final 「的，」/「的。」, calques (折入, 回填, 落地, 賦能), or banned wuxia terms.
- **Scene Shapes**: Every scene starts with a natural spoken actor question, includes natural second actor turns, followed by narration and host responses, within 3–8 lines.
- **Revision Tracking**: All authored scenes declare `revision: r2`.
- **Validation**:
  - `npc_content_lint.py`: Exit 0 with 0 errors.
  - `chinese-content lint.sh`: 0 errors.
  - `DIALOGUE_SNAPSHOT`: Exactly 25 profiles discovered.
- **Playback Harness Note**: In accordance with the change specifications, manual browser playback harness was not run due to broken local browser harness login; offline test modules, static codec checks, and contract gates verified the complete dataset.

---

## Rewrite (2026-11-20)

This section records the prose rewrite of both hosts under `authored-dialogue-content-upper-faith`. Every `topic_id`, `scene_id`, `keyword`, `label`, variant `when` condition, variant priority, and service/assortment semantics was preserved byte-for-byte; only the prose was replaced. No `refusal` scenes exist in either file. All authored scenes moved from `revision: r2` to `revision: r3`.

### A. altoria_high_priestess (艾莉安娜‧寒水)

**Greeting rewrite**: The new greeting closes the lectionary in the morning light and names all four counters under one roof, signalling that the host will answer plainly on any of them.

1. `altoria_temple.topic_01` (keyword: 禮拜, label: 禮拜):
   - Variant `elf_kin_worship` (`kind: race_is`, `race_key: elf`, priority 10), `revision: r3`:
     - Intent: an elven guest asks about lection times and house rules, and the host welcomes them as returning to the goddess's own kin.
     - Causal bridge: the host bows and answers the schedule point directly (晨鐘之後、日落之前), then the follow-up 「聽起來，我在這裡能完全自在」 is motivated as the guest's reaction and is answered with an open invitation to sit, walk, or talk. No racial over-explanation; the lineage is stated plainly.
   - Fallback `altoria_temple.topic_01_scene`, `revision: r3`:
     - Intent: a traveller asks the lection schedule and whether registration is required, and the host removes every barrier.
     - Causal bridge: the host steps to the pews and answers directly (no registration, no name, morning bell to sunset); the second turn 「我還沒受洗入教，也能坐下來聽嗎」 is the guest's own follow-up and is answered by confirming open seating and pointing to the formal initiation as an optional next step.
2. `altoria_temple.topic_02` (keyword: 祝禱, label: 祝禱), fallback `revision: r3`:
   - Intent: a traveller asks the price of a journey-safety blessing, and the host declares prayer free while directing bottled water to the shop counter.
   - Causal bridge: the host answers the fee question first (祝禱不收分文), then the guest's miasma concern turns the topic to 受洗聖水, which the host answers and uses to bridge to the deacon's counter and topic_04.
3. `altoria_temple.topic_03` (keyword: 聖所, label: 聖所), fallback `revision: r3`:
   - Intent: a traveller asks whether the sanctuary sits beside the hall and is part of the ministry, and the host states the frank canon without evasion.
   - Causal bridge: the host answers placement and ministry plainly, comparing bodily service to a tavern pouring wine, then states light-magic contraception and points down the corridor; the guest's synthesis 「禮拜與聖所是同一份信仰」 is the closing confirmation, answered by naming the three counters of one faith.
4. `altoria_temple.topic_04` (keyword: 商店, label: 商店), fallback `revision: r3`:
   - Intent: a traveller asks what the in-hall goods counter sells, and the host introduces Deacon Rohaisya as its keeper.
   - Causal bridge: the host names the deacon and her stock, then the guest's 「想買聖水，直接找她拿就行嗎」 is answered with board pricing and usage guidance, closing with an invitation back to the hall for prayer.

### B. altoria_sanctum_deacon (羅海西亞‧芬威克)

**Greeting rewrite**: The new greeting flips a ledger page and asks whether the purchase is self-use or a gift, listing 聖水, 禮器 and 貼身用 goods with board pricing, and offers to arrange sanctuary service directly.

1. `altoria_sanctum.topic_01` (keyword: 賣什麼, label: 賣什麼), fallback `revision: r3`:
   - Intent: a shopper asks what the counter sells and how the shelves are grouped, and the host enumerates the full assortment.
   - Causal bridge: the host splits the wares into wearable, concealed, and usable categories and ranks 受洗聖水 on the top shelf; the guest's price/discount follow-up is answered with fixed 不二價 board pricing and an invitation to ask.
2. `altoria_sanctum.topic_02` (keyword: 聖水, label: 聖水), fallback `revision: r3`:
   - Intent: a traveller asks how to use and keep the blessed water on the road, and the host shows the bottle and its label.
   - Causal bridge: the host answers cleansing by wiping wrist and forehead, then the guest's storage question is answered by the tight cork; the host closes by splitting free hall prayer from paid bottled water.
3. `altoria_sanctum.topic_03` (keyword: 禮器, label: 禮器), fallback `revision: r3`:
   - Intent: a shopper asks how censer and mist are paired in use, and the host explains home and ceremonial use plus the buy-back policy.
   - Causal bridge: the host answers usage first, then states the clean buy-back; the guest's 「連用過的也能拿回來換」 is answered with cash refund for intact goods.
4. `altoria_sanctum.topic_04` (keyword: 聖所事務, label: 聖所事務), fallback `revision: r3`:
   - Intent: a visitor asks how to arrange sanctuary service, and the host hands them to the duty nuns with the consent rule.
   - Causal bridge: the host points to the corridor and states that rooms, times and services are agreed by mutual consent, adds light-magic care and contraception, and splits prayer (main hall) from goods (the counter); the guest's 「兩邊各管一邊」 is answered with 各司其職.
