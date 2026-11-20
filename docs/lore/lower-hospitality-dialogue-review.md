# Authoring Review: Lower Hospitality Dialogue Slice (Refined r2)

## 1. Source References and Review Gate
- Canonical world setting: `tmp/story_settings/world_info.md`
  - Population: ~300 elves total across three branches (Fionnen, Ciaran, Eolas) vs 30M total population (humans 21M, beastfolk 9M). Elves are exceptionally rare.
  - Social standing: Consistently regarded across human kingdom and empire as "皇族之上的高級存在" (above royalty). Other races view elven free sexual mores with awe and "視而不見" (look away respectfully).
  - Religion: 光明教會 (Holy See in 聖潔王都), worships 光明女神 (ancestral deity of Fionnen forest elves). Physical union regarded as worship (崇神之禮), brothels run as sanctuaries (聖所), light magic used for contraception.
  - Economics: 1 gold = 100 silver = 10000 copper. Standard meal: 5-10 copper; standard inn lodging: ~20 copper.
- Profiles and places:
  - `world/lore/npc_profiles/altoria_lower.py` (eatery owner 西格瑪‧庫柏, tavern keeper 蘿溫‧古橡, innkeeper 溫弗蕾德‧古林).
  - `world/lore/settlements/places_altoria_lower.py` (`altoria_eatery`, `altoria_tavern`, `altoria_lodging`).
  - Assortment: `staple_meals` (`meal` 10 copper, `kingdom_rye_hardtack` 8 copper, `adventurer_field_ration` 10 copper, `imperial_candied_fruit` 15 copper, `beastfolk_smoked_jerky` 20 copper, `harbor_lobster_bisque` 25 copper, `elven_candied_blossom` 60 copper).
  - Retained services: No quests, rumors, recruitments, or stat buffs granted by prose alone. Eatery sells assortment goods and buys ingredients. Tavern provides social setting and companion talks without free perks. Innkeeper provides lodging and practice environment without free heals or fee modifications.

## 2. Topic Inventory and Intent
- `altoria_eatery_owner.yaml` (`revision: r2`, with `topic_02` later raised to `r3`):
  - `altoria_eatery.topic_01` (餐點): Daily basic hot meat soup, fresh thick-cut rye bread, travel rations.
  - `altoria_eatery.topic_02` (招牌): Southeastern harbor lobster bisque recipe from an old boatman; elven candied blossoms bought out on 南大道 as expensive luxury confections.
  - `altoria_eatery.topic_03` (乾糧): Wilderness travel advice, beastfolk smoked jerky and rye hardtack.
  - `altoria_eatery.topic_04` (收購): Buying game and wild harvest with strict freshness standards.
- `altoria_tavern_keeper.yaml` (`revision: r2`):
  - `altoria_tavern.topic_01` (傳聞): Roots in guest conversations, listening etiquette. Includes variant for companion present (`var_companion_violet` with preset `violet_altoria`).
  - `altoria_tavern.topic_02` (同伴): Pure-chain continuation (`predecessors: [altoria_tavern.topic_01]`, `disclosure: pure_chain`). Candid reflections on travel companions and mutual trust.
  - `altoria_tavern.topic_03` (委託): Directing formal guild contract inquiries to Adventurers Guild hall.
  - `altoria_tavern.topic_04` (歇腳): Recommending hearth seating or neighbor Winifred's inn.
- `altoria_innkeeper.yaml` (`revision: r2`):
  - `altoria_lodging.topic_01` (房間): Quiet upstairs room with solid latches.
  - `altoria_lodging.topic_02` (過夜): Importance of safe sleep over resting by roadsides.
  - `altoria_lodging.topic_03` (修煉): Quiet environment for mental sword practice and spell recitation.
  - `altoria_lodging.topic_04` (澡堂): Directing travelers to Isabelle's bathhouse to the east.

## 3. Style & Anti-OOC Compliance
- Strictly in-character, player-facing Traditional Chinese (zh-TW).
- Full-width punctuation throughout.
- Spaces between CJK and alphanumeric characters.
- Zero backticks, zero UI mentions, zero game command tokens (`talk`, `rest`, `buy`, etc.), zero system stat/mechanic explanations.
- Verified absence of forbidden calques (折入, 回填, 賦能, 落地, 拉齊), banned phrases, and sentence-final `的，`/`的。`.

## 4. Rewrite (2026-11-20)

Whole-slice prose rewrite to fix causal coherence, drop the flat/AI phrasing, and let the
three adult hosts speak with the world's frankness. No `topic_id`, `scene_id`, `keyword`,
`label`, condition, variant, priority, predecessor, disclosure or speaker changed. Service
behaviour unchanged: the eatery still sells its assortment and buys fresh game; the tavern
still brokers nothing (no rumour, commission or party slot sold); the lodging still offers
rooms, rest and quiet study with no free healing and no fee change.

### altoria_eatery (西格瑪‧庫柏, 52)

- `topic_01` 餐點 r2→r4 — intent: the daily meat stew with fresh rye bread, then the travel
  rations. Bridge: the actor asks what is hot now, the host names the stew, the actor turns
  the topic with "which keeps on the road", and the host answers 王國黑麥硬麵包 and
  冒險者攜行口糧.
- `topic_02` 招牌 r3→r4 — intent: the 東南港灣龍蝦濃湯 recipe and 精靈蜜漬花蕊 bought out by
  demand on 南大道, with 帝國蜜漬果乾 as the everyday sweet. Bridge: the actor asks about the
  signature dishes, the host names the bisque, the actor asks "any sweets", and the host
  answers with the blossom then the candied fruit. The elven goods are scarce and bought out,
  never described as stolen.
- `topic_03` 乾糧 r2→r3 — intent: 王國黑麥硬麵包 and 獸王國燻獸肉乾 for a multi-day trip, with
  a warning against relying on hunting. Bridge: the actor asks which rations keep, the host
  names them and warns about rain, and the actor closes with appreciation.
- `topic_04` 收購 r2→r3 — intent: strict buy-back of fresh game. Bridge: the actor asks whether
  the shop buys, the host states the freshness standards, the actor asks fresh-butchered or
  cleaned, and the host answers.

### altoria_tavern (蘿溫‧古橡, 36)

- `topic_01` 傳聞 r2→r3 (fallback), r2→r4 (`var_companion_violet`) — intent: rumours live in the
  guests' own talk and the keeper sells none; the variant makes clear the guest is not alone
  and the keeper notices the noble companion. Bridge: the actor asks for rumours, the host
  points to the tables ("only sell drink, not news"), the actor asks how to open a
  conversation, and the host gives the etiquette. The variant keeps its condition and
  priority and names no companion identity.
- `topic_02` 同伴 r2→r3 — intent: trust against casual pairing, with the adult note that
  sleeping together does not equal trusting each other in a dungeon. Bridge: the actor asks
  how to judge a companion, and the host answers from ten years behind the bar.
- `topic_03` 委託 r2→r3 — intent: formal jobs belong to the guild hall. Bridge: the actor asks
  for commissions, the host redirects, the actor asks about returning to recruit, and the host
  confirms the pattern.
- `topic_04` 歇腳 r2→r3 — intent: hearth bench for warmth, 爐火旅店 next door for sleep. Bridge:
  the actor asks where to sleep, and the host offers the bench then 溫弗蕾德's inn.

### altoria_lodging (溫弗蕾德‧古林, 59)

- `topic_01` 房間 r2→r4 — intent: quiet upstairs rooms with solid latches. Bridge: the actor
  asks what the rooms are like, the host describes them, and the actor closes with relief.
- `topic_02` 過夜 r2→r3 — intent: safe sleep against wilderness camping. Bridge: the actor asks
  the difference, the host contrasts the two, and the actor takes the lesson.
- `topic_03` 修煉 r2→r3 — intent: quiet study and practice, with lamp-oil offered. Bridge: the
  actor asks whether the room suits, the host says yes, the actor states the intent, and the
  host adds the care.
- `topic_04` 澡堂 r2→r3 — intent: 伊莎貝爾's bathhouse to the east. Bridge: the actor asks where
  to bathe, and the host directs down 客棧巷.

Proper nouns all resolve to registry rows: 南大道, 客棧巷, 爐火旅店, 醉月酒館, 公共浴場,
冒險者公會, 王國西部丘陵, 東南港灣, 翠綠森林, and the 王都飯食 item display names
(王國黑麥硬麵包, 冒險者攜行口糧, 帝國蜜漬果乾, 獸王國燻獸肉乾, 東南港灣龍蝦濃湯,
精靈蜜漬花蕊). 爐火旅店 and 醉月酒館 resolve to their `doorway_key` rows in
`content/maps/interiors/`; the `--places` warnings for those two names are the lint's
heuristic missing the doorway key, not an invented name.

Compression pass (2026-11-20): fixed four subject-jump/comma-join defects where the reader
had to supply 於是 or 所以 — the eatery's 掀開鍋蓋 narration (split at the steam, added 便),
the tavern greeting (bells ring after the cloth toss, added 便 and 她), the tavern variant's
目光→手背 narration (added 接著), and the innkeeper's window/noise line (added 也就). These
three scenes moved to r4; the tavern fallback and every other scene stayed unchanged.
