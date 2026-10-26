# Lower Civic Authored Dialogue Review

Review and lineage ledger for `authored-dialogue-content-lower-civic`.
Covered hosts: `altoria_bathhouse_keeper` (`altoria_bathhouse`), `altoria_guard_captain` (`altoria_guardhouse`).
Review date: 2026-10-26.

## 1. Sources Consulted & Canonical Inputs

1. `tmp/story_settings/world_info.md`:
   - Elves social standing and population: ~300 elves continent-wide (forest, dark, illusion-child branches) vs. 30M humans and beastfolk. Treated as "皇族之上的高級存在" (a rank above royalty).
   - Elven sexuality and nudity: ~80% of time on sexuality, no concept of shame around sex or nakedness. Other races treat their ways with awe and "視而不見" (look away out of reverence, not moral disgust or contempt).
   - Church of Light (光明教會): Rooted in forest elf ancestral deity, holy seat in Holy Capital Altoria.
   - Public facilities: Towns feature public bathhouses; human/beastfolk culture requires privacy and shame around nakedness, creating distinctive contrast with elves.
   - Economy & currency: 1 gold = 100 silver = 10,000 copper; guild system F-S ranks; guard stations do not issue parallel bounties.
2. Canonical NPC profiles & Places:
   - `world/lore/npc_profiles/altoria_lower.py`: `altoria_bathhouse_keeper` (Isabel Reeds, 44yo human woman, keeper for 20 years, loud spoken tone, insists on "男左女右" rules, curious about elven culture without prejudice, denies medical healing claims).
   - `world/lore/npc_profiles/altoria_lower.py`: `altoria_guard_captain` (Thorwald Denburg, 45yo human man, south gate captain, orderly and formal, hates answering twice, points work-seekers to guild, uses specific street names and map).
   - `world/lore/settlements/places_altoria_lower.py`: `altoria_bathhouse` and `altoria_guardhouse` place definitions.
   - Canonical place names referenced in guard directions: `南大道`, `中央廣場`, `公會前`, `冒險者公會`, `市場街`, `聖階`, `客棧巷`, `爐火旅店`, `醉月酒館`.
3. Style skills:
   - `skill://npc-dialogue-content`
   - `skill://chinese-content-writing-guideline`
   - `skill://writing-style-guideline`

## 2. Topic Inventory and Refined Prose Intent

### `altoria_bathhouse_keeper.yaml` (`altoria_bathhouse`)

- Opening (`greeting`): Isabel emerges briskly from the steam with folded towels, welcoming guests warmly while keeping her brisk, busy attitude ("想問規矩就爽快開口，我後頭還有一大疊布巾等著摺呢！").
- `altoria_bathhouse.topic_01` (`規矩`):
  - `fallback` (`scene_id: altoria_bathhouse.topic_01_scene`, `revision: r2`): 4 lines. Actor asks a genuine spoken question about first-time bath rules. Isabel gestures to the two curtained entrances, explaining the stone wall division and clean shoe storage with concrete reasoning.
  - Variant `elf_guest` (`variant_id: elf_guest`, `priority: 20`, `when: {kind: race_is, race_key: elf}`): 5 lines. Isabel pauses in awe at seeing an elf guest. Explains how humans and beastfolk look away out of deep reverence without daring to judge, and warmly invites the guest to enjoy a quiet, uninhibited soak during less busy hours. Priority 20 ensures this combined ethnic reaction takes precedence.
  - Variant `high_exposure` (`variant_id: high_exposure`, `priority: 10`, `when: {kind: exposure, minimum: 3}`): 4 lines. Isabel acts promptly with hospitality, handing over a thick towel to protect from drafts and gate guard scrutiny, guiding them to warm private lockers.
- `altoria_bathhouse.topic_02` (`精靈`):
  - `fallback` (`scene_id: altoria_bathhouse.topic_02_scene`, `revision: r2`): 5 lines. Explains elven rarity (~300 on the continent), their natural attitude toward the body without shame, and other races' awe-inspired acceptance.
- `altoria_bathhouse.topic_03` (`泡湯`):
  - `fallback` (`scene_id: altoria_bathhouse.topic_03_scene`, `revision: r2`): 4 lines. Describes clean heated river water over round stones soothing travel exhaustion, while firmly disclaiming myths about magical healing (redirecting wound treatment to East Market alchemists).
- `altoria_bathhouse.topic_04` (`歇息`):
  - `fallback` (`scene_id: altoria_bathhouse.topic_04_scene`, `revision: r2`): 4 lines. Offers hall benches and spring water for cooling down; directs overnight travelers seeking comfortable feather beds to Winnifred at Hearthstone Inn.

### `altoria_guard_captain.yaml` (`altoria_guardhouse`)

- Opening (`greeting`): Thorwald turns sharply from inspecting the south gate, chainmail gleaming, stating duties clearly: directions and security are answered; no commissions or bounties exist here.
- `altoria_guardhouse.topic_01` (`進城`):
  - `fallback` (`scene_id: altoria_guardhouse.topic_01_scene`, `revision: r2`): 5 lines. Uses wall map and points out South Boulevard, Central Plaza, Guild Front, Market Street, and Holy Steps with firm spatial orientation.
- `altoria_guardhouse.topic_02` (`找活`):
  - `fallback` (`scene_id: altoria_guardhouse.topic_02_scene`, `revision: r2`): 5 lines. Guardhouse issues zero commissions; explains the civic principle of public defense vs. private mutual aid, directing work-seekers to guild hall boards.
- `altoria_guardhouse.topic_03` (`治安`):
  - `fallback` (`scene_id: altoria_guardhouse.topic_03_scene`, `revision: r2`): 5 lines. Explains patrolling guards in blue tabards; clarifies guard jurisdiction (defense against theft, brawls, beasts) while disclaiming private merchant price disputes.
- `altoria_guardhouse.topic_04` (`過夜`):
  - `fallback` (`scene_id: altoria_guardhouse.topic_04_scene`, `revision: r2`): 5 lines. Value of order; guardhouse only has bare wooden benches with no beds or locks; directs travelers to Hearthstone Inn and Moonlit Tavern in Inn Lane.

## 3. Retained Service Behaviours and Exclusions

- Public bathhouse does not provide healing mechanics, stat bonuses, or status removal.
- Guardhouse does not maintain a bounty board, parallel commissions, or entrance toll/pass requirements.
- Neither NPC commits the player to purchases, allegiances, or quests in actor lines.
- Zero OOC terms: no command tokens, mechanics, UI words (`指令`, `系統`, `選單`, `按鈕`), or bracketed hints.
- Service semantics remain 100% identical to baseline.

## 4. Linguistic and Style Verification

- Language: Traditional Chinese 正體中文 (zh-TW).
- Punctuation: Full-width punctuation marks throughout; single space between CJK and alphanumeric characters.
- Banned terms check: Zero occurrences of 「您」; zero sentence-final 「的，/的。」; zero calques; zero 中式武俠 terms.
- Linter execution: `sh /home/jim60105/.agents/skills/chinese-content-writing-guideline/scripts/lint.sh` produced `0 error(s)` on both YAML files.
