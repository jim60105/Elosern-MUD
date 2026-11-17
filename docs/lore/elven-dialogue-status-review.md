# Review: elven status in authored dialogue

Scope: five shipped tables whose prose made an elf describe ordinary bodily
harm, plus one line that could be read as elven goods being robbed. The canon
basis is `tmp/story_settings/world_info.md` 種族設定 › 精靈族 (physical values
70-95, HP 10000, standard body reinforcement ×100, immunity to disease),
三國關係 › 對精靈態度 (`world_info.md:207`), and 特殊設定 › 精靈與外界互動
(`world_info.md:408-413`). The three elven branches hold a rank above royalty in
all three human and beastfolk nations, and an elf child's unrestrained strength
makes the child dangerous to others.

This review supersedes the revision claims for the scenes listed below in
`fionnen-fare-homes-review.md`, `eolas-fare-homes-review.md`,
`ciaran-local-goods-review.md` and `lower-hospitality-dialogue-review.md`.

## Changed scenes

| File | Scene | Revision | Change |
| --- | --- | --- | --- |
| `fionnen_sylara.yaml` | `fionnen_sylara_home.topic_01` | `r1` → `r2` | elf hunters return with torn clothes, not wounds; an elf child breaks the branch, not herself |
| `fionnen_sylara.yaml` | `fionnen_sylara_home.topic_03` | `r1` → `r2` | her craft serves guests and animals; a scratch on an elf closes overnight, which keeps the self-healing fact already stated in her card |
| `fionnen_lumeth.yaml` | `fionnen_lumeth_home.topic_01` | `r1` → `r2` | the bees circle her and leave her alone, so the honey keeper keeps her everyday register without being stung |
| `eolas_nirnel.yaml` | `eolas_nirnel_home.topic_03` | `r1` → `r2` | only a burn she gave herself on 試煉場 needs care; falling in the forest no longer breaks an elf's bones, and the next line's low injury rate now agrees |
| `ciaran_nireth.yaml` | `ciaran_nireth_home.topic_01` | `r3` → `r4` | elven bodies are described as sound; spent mana remains the danger that crosses every race |
| `altoria_eatery_owner.yaml` | `altoria_eatery.topic_02` | `r2` → `r3` | elven blossom stock is bought out on 南大道 and never taken by force |

## Line review

`fionnen_sylara_home.topic_01`, host answer to whether the village sees many
injuries. The old line gave elf hunters wounds and elf children falls, which
contradicts a body that shrugs off ordinary cuts and a child whose strength
endangers others. The new line keeps the forest's wear on cloth and timber and
leaves the salve for visitors and animals, matching the greeting's check for
blood and the 光魔法 scene's account of who she treats.

`fionnen_sylara_home.topic_03`, the light magic scene. The old answer said elves
heal by themselves after an injury, and it stood beside a 藥草 scene that
assumed routine wounds. The new answer keeps the card's fact (a scratch closes
overnight) and removes the implication that elves carry lasting harm. The actor
question stays unchanged, and the host still refuses to claim light does more
than it does.

`fionnen_lumeth_home.topic_01`, the hive scene. A bee sting is a small event,
and it still reads as an elf being hurt by an ordinary insect. The new line
keeps the instruction about slow movement and the reason behind it, and the
guest learns how the keeper behaves around her hives.

`eolas_nirnel_home.topic_03`, the mana and healing scene. The old line named
burns from 試煉場 and bones broken in the forest. The new line keeps the burn,
which the elves' pursuit of extreme sensation permits, and removes the fall.
The following line already says the valley's people are rarely hurt, so the two
now agree, and spent mana remains the condition that reaches every race.

`ciaran_nireth_home.topic_01`, the brewing scene. The old line said bone trauma
is equally dangerous for every race, which flattens the species gap. The new
line keeps disease immunity and sound bodies, and leaves mana exhaustion as the
shared danger. The 藥草 scene's buy-back and the three remedy names are
untouched.

`altoria_eatery.topic_02`, the signature dish scene. 「給搶個精光」 can be read as
robbery, which no one in Altoria would attempt against elven goods. 「被搶購一空」
keeps the high purchase price and the demand that explains it.

## Checks

- `npc_content_lint.py` over the five files reports 0 errors; its one warning is
  the existing 拉拉 in 希拉拉's name.
- `chinese-content-writing-guideline` and `writing-style-guideline` linters
  report 0 errors on the same files.
- `DIALOGUE_SNAPSHOT` loads with 38 entries.
- `tools.contract_gate` passes.

## Proper nouns

No new proper noun enters the prose. The place rows behind 試煉場、南大道、
林間菜圃、花蕊蜜園 and 石階菜畦 already cover every name in the scenes.
