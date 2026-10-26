# Ciaran-Fare Dialogue Editorial Review

## 1. Scope and Canonical Ownership

This document records the line-by-line editorial and lore verification for the `authored-dialogue-content-ciaran-fare` change (`ciaran_lareneth`, `ciaran_nireth`, `ciaran_valwyn`).

### Profile and Place Bindings
- `ciaran_lareneth_home` (place: `拉瑞內斯的家`, host: `拉瑞內斯‧妮特布倫`) -> `world/lore/dialogue/content/ciaran_lareneth.yaml`
- `ciaran_nireth_home` (place: `妮瑞斯的家`, host: `妮瑞斯‧米斯特瓦勒`) -> `world/lore/dialogue/content/ciaran_nireth.yaml`
- `ciaran_valwyn_home` (place: `瓦爾溫的家`, host: `瓦爾溫‧斯蒂爾瓦特爾`) -> `world/lore/dialogue/content/ciaran_valwyn.yaml`

Canonical Sources:
- `tmp/story_settings/world_info.md`:
  - Elven races section: Total population ~300 elves (roughly 100 Ciaran dark elves in Shadow Valley, central mountains western underground; brown skin, silver hair, red eyes, fire/dark affinity, blade artistry).
  - Elven society section: Elves are all-rounders (`全能者`) with no fixed professions, no caste system, no marriage, open relationships, and no shame regarding nudity/sexuality. Attitude towards other races is indifferent (`不在意`).
  - Religion and deities section: Three true ancestral deities (Dark Goddess for Ciaran). Elves never proselytise to outsiders; outsiders do not know elven religion.
  - State and politics section: Other races view elves as higher beings above royalty (`皇族之上的高級存在`) and accord them the highest courtesy.
  - Economy section: Continent common currency (1 gold = 100 silver = 10,000 copper).
- `world/lore/npc_profiles/ciaran_homes_a.py` and `ciaran_homes_b.py`:
  - `ciaran_lareneth`: Flower confectioner living by `溪畔小徑`; gentle, seasonal awareness, serves candied blossoms and tea.
  - `ciaran_nireth`: Hedge herbalist by `藥草園`; meticulous, caring, brews healing and mana potions.
  - `ciaran_valwyn`: Collector by `村北古樹下`; curious, nostalgic, braids spider silk, hoards tagged curios, wears crescent earrings.
- `world/lore/settlements/places_ciaran.py`:
  - Room locations and doorway keys: `拉瑞內斯的家` (exterior xy 245, 135 `溪畔小徑`), `妮瑞斯的家` (exterior xy 590, 300 `藥草園`), `瓦爾溫的家` (exterior xy 200, 465 `村北古樹下`). Other referenced village places: `村中廣場`, `共食棚`, `練刀場`, `銀葉坡`, `長老古樹下`, `谷底`.
- `world/lore/settlements/assortments.py`:
  - `elven_fare` (`elven_candied_blossom`).
  - `elven_remedies` (`greater_healing_potion`, `mana_potion`).
  - `elven_sundries` (`elven_spider_silk`).
- `docs/lore/settlement-locations.md` (`暗影谷村` section):
  - Elven village has no commercial stores or career titles; services are provided by individual elves who love their crafts within their homes; no trading hierarchy, boss, or apprentices.
- `skill://npc-dialogue-content`, `skill://chinese-content-writing-guideline`, `skill://writing-style-guideline`.

---

## 2. Mandatory Lore Checks

### Elves Standing, Rarity, and Village Culture
- Canon: Total population of dark elves is ~100 living in `暗影谷村` (central mountains western underground). Other races revere elves as beings above royalty, while elves treat outsiders with calm courtesy and indifference (`不在意`).
- Non-commercial Sharing: The village has no shops as institutions, no business hours, and no profit motive. Communal food is shared at `共食棚`; craft items are shared or traded from individual homes. Money (copper coins) is used as an exchange medium for visitors taking goods on the road, but prices represent non-commercial exchanges.
- Handling by Hosts:
  - `ciaran_lareneth`: Offers tea and candied blossom tasting to any passerby on a low stool by the window; packs jars for the road in return for copper coins; takes back unopened jars without penalty.
  - `ciaran_nireth`: Brews remedies from her own garden herbs; prepares potions for village wounded and occasional visitors; refuses outside raw herbs to protect purity; takes back unused intact bottles.
  - `ciaran_valwyn`: Collects odds and ends from forest and stream; braids extra spider silk for villagers and guests; trades stories and travel accounts as readily as goods; directs accessory inquiries to Gwenaera.

### Religion and Truth
- Canon: Elves know the truth of the three goddesses (Light, Dark, Knowledge), but never preach or proselytise to outsiders. The scenes contain zero preaching, zero doctrinal instruction, and zero reference to church hierarchy.

### Demeanour and Tone
- Villagers speak in their own homes: natural, relaxed spoken Traditional Chinese (zh-TW) with fitting particles (`喔`／`啦`／`吧`／`呢`), free from essay prose or pseudo-classical 文言 cadence.

---

## 3. Retained Service Behaviours and Assortment Consistency

All service functionality is preserved without change:
- `ciaran_lareneth_home`: Stocks `elven_fare` (`elven_candied_blossom` / `精靈蜜漬花蕊`). Offers a taste on a leaf as hospitality, which grants no inventory items or stat modifiers. Sells jars for copper coins and buys back unopened jars.
- `ciaran_nireth_home`: Stocks `elven_remedies` (`greater_healing_potion` / `強效治療藥水`, `mana_potion` / `魔力藥水`). Clearly distinguishes red-cord healing potions for severe trauma from blue-cord mana potions for replenishing cast fatigue. Refuses outside raw herbs; buys back intact unopened potion bottles.
- `ciaran_valwyn_home`: Stocks `elven_sundries` (`elven_spider_silk` / `精靈蛛絲`). Sells braided silk bundles for copper coins and buys back intact unused bundles. Crescent earrings are personal display items, redirecting visitors to Gwenaera at `銀葉坡`.

---

## 4. Per-Topic Intent and Scene Structure Review

### A. ciaran_lareneth_home (`拉瑞內斯‧妮特布倫`)
1. **Opening Greeting**: Setting hospitality. Lareneth stirs honey in her stone home by `溪畔小徑` and offers a candied blossom on a thick leaf to taste before conversing.
2. `ciaran_lareneth_home.topic_01` (keyword: `花饌`, label: `花饌`):
   - Actor asks how the flower confections are prepared. Host explains late-spring gathering of dew-covered blossom cores steeped in mountain wild honey for three months; actor asks about travel suitability; host confirms long shelf life and exchange for copper coins.
3. `ciaran_lareneth_home.topic_02` (keyword: `山產`, label: `山產`):
   - Actor asks about seasonal valley produce. Host describes seasonal rhythms (spring blossoms, summer honey, autumn fruit, rain-season mushrooms); actor asks about buy-back for unused jars; host confirms full return for unopened jars.
4. `ciaran_lareneth_home.topic_03` (keyword: `茶點`, label: `茶點`):
   - Actor asks about tea treats on the low window stool. Host explains village custom of leaving treats for trail rest and thirst quenching; actor asks about travel packing; host describes wrapping jars with thick leaves and hemp cord.
5. `ciaran_lareneth_home.topic_04` (keyword: `口味`, label: `口味`):
   - Actor asks about Ciaran culinary preferences compared to big cities. Host explains light, natural sweetness over salt, avoiding excessive honey to keep the flower aroma pure; highlights `elven_candied_blossom`.

### B. ciaran_nireth_home (`妮瑞斯‧米斯特瓦勒`)
1. **Opening Greeting**: Meticulous inspection. Nireth damps the herb stove by `藥草園`和 checks the visitor's posture and shoulders for wounds before welcoming inquiries.
2. `ciaran_nireth_home.topic_01` (keyword: `調藥`, label: `調藥`):
   - Actor asks about the brewing hearth. Host describes daily morning harvesting and ancestral low-heat simmering, noting that physical trauma and depleted mana affect all races; confirms availability of `greater_healing_potion` and `mana_potion`.
3. `ciaran_nireth_home.topic_02` (keyword: `重傷`, label: `重傷`):
   - Actor asks about remedies for severe beast or blade wounds. Host points to red-corded `greater_healing_potion` for deep trauma, warning against wasting it on minor scratches; confirms coin exchange for emergency defense.
4. `ciaran_nireth_home.topic_03` (keyword: `魔力`, label: `魔力`):
   - Actor asks about garden care and preparation for brewing pure mana potions. Host describes harvesting fresh shoots of mana grass at early dawn and simmering on low residual hearth heat, noting that healthy garden tending provides steady supplies for those in need.
5. `ciaran_nireth_home.topic_04` (keyword: `藥草`, label: `藥草`):
   - Actor asks about selling outside wild herbs. Host strictly refuses unknown outside herbs to preserve medicinal reliability; confirms buy-back for intact, unopened remedy jars.

### C. ciaran_valwyn_home (`瓦爾溫‧斯蒂爾瓦特爾`)
1. **Opening Greeting**: Enthusiastic curio collector. Valwyn threads sea shells on leather cord under `村北古樹下`, warmly greeting the traveler and offering to share histories of her hoarded curios.
2. `ciaran_valwyn_home.topic_01` (keyword: `蒐羅`, label: `蒐羅`):
   - Actor asks about the hanging feathers, seeds, and shells. Host shares stories of stream and path finds (including a large feather from 300 years ago) and dated tags, explaining that personal keepsakes are for display only.
3. `ciaran_valwyn_home.topic_02` (keyword: `蛛絲`, label: `蛛絲`):
   - Actor asks about `elven_spider_silk`. Host explains deep-forest spider silk braided into durable cords resisting storms; confirms exchanging braided bundles for copper coins.
4. `ciaran_valwyn_home.topic_03` (keyword: `耳環`, label: `耳環`):
   - **Variant `familiar_visitor`** (`affinity_at_least`: `familiar`, priority 10):
     - Host recognises a familiar visitor who has seen the earrings before: `「哎，是你呀！這對月牙耳環你之前見過吧……」`.
     - **Possession Safety**: The actor line is neutral with no references to the speaker's race, sex, guild, or gear, and never uses possession-breaking terms. The condition evaluates the owner's affinity; the host's recognition addresses the familiar visitor without assuming physical traits of the acting body.
     - Directs the visitor to Gwenaera at `銀葉坡`.
   - **Fallback `ciaran_valwyn_home.topic_03_scene`**:
     - Treats the visitor as a first-time guest admiring the earrings. Explains they were traded from Gwenaera for shells and kept for many years; directs the guest to visit Gwenaera's home at `銀葉坡`.
5. `ciaran_valwyn_home.topic_04` (keyword: `以物易物`, label: `以物易物`):
   - Actor asks about bartering goods and tales. Host shares enthusiasm for exchanging wild travel stories for curio origins; confirms buy-back of intact, undamaged spider silk bundles for copper coins.

---

## 5. Style and Constraint Compliance Verification

- **In-Character Only**: No command tokens (`rest`, `buy`, `talk`), no UI mechanics, and no bracketed hints.
- **Punctuation & Script**: Traditional Chinese (zh-TW) in dialogue scenes, full-width punctuation in all Chinese sentences.
- **Prohibited Patterns**:
  - Zero instances of the prohibited second-person pronoun in dialogue scenes.
  - Zero sentence-final particles before punctuation in dialogue scenes.
  - Zero English calques.
  - Zero wuxia vocabulary tokens.
  - Zero forbidden rhetorical devices (contrastive constructions, tricolons, em-dashes, mid-sentence colons).
- **Scene Shapes**: All formal scenes start with complete actor speech lines, followed by host responses and stage narration, within 3–8 lines.
- **Revision Tracking**: All authored scenes across all three hosts declare `revision: r2`.
- **Browser Playback Limit**: Browser manual playback was not run locally in this headless container environment; verification was conducted via the full test suite, parser schema validation, registry resolution, and language linters.
