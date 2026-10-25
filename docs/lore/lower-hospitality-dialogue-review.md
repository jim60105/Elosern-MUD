# Authoring Review: Lower Hospitality Dialogue Slice

## 1. Source References and Review Gate
- Canonical world setting: `tmp/story_settings/world_info.md`
  - Population: ~300 elves vs 30M total (humans 21M, beastfolk 9M). Elves are extremely rare.
  - Three elven branches: Fionnen (翠綠森林村, light magic, archery), Ciaran (暗影谷村, fire/dark magic, blades), Eolas (幽月谷村, all elements, divine arcana).
  - Standing: Treated by human kingdom and empire as "皇族之上的高級存在" (above royalty). Other races view elven free sexual mores with awe and "視而不見" (look away respectfully). Young elves without restraint are hazardous around other races.
  - Religion: 光明教會 (Holy See in 聖潔王都), worships 光明女神 (ancestral goddess of Fionnen elves). Physical union regarded as worship (崇神之禮), brothels run as sanctuaries (聖所), light magic used for contraception.
  - Economics: 1 gold = 100 silver = 10000 copper. Standard meal: 5-10 copper; standard inn lodging: ~20 copper.
- Profiles and places:
  - `world/lore/npc_profiles/altoria_lower.py` (eatery owner 西格瑪‧庫柏, tavern keeper 蘿溫‧古橡, innkeeper 溫弗蕾德‧古林).
  - `world/lore/settlements/places_altoria_lower.py` (`altoria_eatery`, `altoria_tavern`, `altoria_lodging`).
  - Assortment: `staple_meals` (`meal` 10 copper, `kingdom_rye_hardtack` 8 copper, `adventurer_field_ration` 10 copper, `imperial_candied_fruit` 15 copper, `beastfolk_smoked_jerky` 20 copper, `harbor_lobster_bisque` 25 copper, `elven_candied_blossom` 60 copper).
  - Retained services: No quests, rumors, recruitments, or stat buffs granted by prose alone. Eatery sells assortment goods and buys ingredients. Tavern provides social setting and companion talks without free perks. Innkeeper provides lodging and practice environment without free heals or extra fees.

## 2. Topic Inventory and Intent
- `altoria_eatery_owner.yaml`:
  - `altoria_eatery.topic_01` (餐點): Daily basic hot soup and bread, field rations.
  - `altoria_eatery.topic_02` (招牌): Lobster bisque from southeastern harbor recipe; mentions rare candied blossoms from elves.
  - `altoria_eatery.topic_03` (乾糧): Wilderness travel advice, jerky and hardtack.
  - `altoria_eatery.topic_04` (收食): Buying game and wild harvest with strict freshness standards.
- `altoria_tavern_keeper.yaml`:
  - `altoria_tavern.topic_01` (傳聞): Roots in guest conversations, listening etiquette. Includes variant for companion present (`violet_altoria`).
  - `altoria_tavern.topic_02` (同伴): Pure-chain continuation (`predecessors: [altoria_tavern.topic_01]`, `disclosure: pure_chain`). Candid thoughts on travel companions and mutual trust.
  - `altoria_tavern.topic_03` (委託): Directing formal guild contract inquiries to Adventurers Guild hall.
  - `altoria_tavern.topic_04` (歇腳): Recommending hearth seating or neighbor Winifred's inn.
- `altoria_innkeeper.yaml`:
  - `altoria_lodging.topic_01` (房間): Quiet upstairs room with solid latches.
  - `altoria_lodging.topic_02` (過夜): Importance of safe sleep over resting by roadsides.
  - `altoria_lodging.topic_03` (修煉): Quiet environment for mental sword practice and spell recitation.
  - `altoria_lodging.topic_04` (澡堂): Directing travelers to Isabelle's bathhouse to the east.

## 3. Style & Anti-OOC Compliance
- Strictly in-character, player-facing Traditional Chinese (zh-TW).
- Full-width punctuation throughout.
- Spaces between CJK and alphanumeric characters.
- Zero backticks, zero UI mentions, zero game command tokens (`talk`, `rest`, `buy`, etc.), zero system stat/mechanic explanations.
- Verified absence of forbidden calques (折入, 回填, 賦能, 落地, 拉齊) and banned phrases.
