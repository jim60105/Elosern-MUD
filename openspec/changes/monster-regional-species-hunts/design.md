## Context

See proposal.md — Why. `monster-quest-objectives` shipped everything a regional species hunt needs:
`QuestObjective.region_key` / `species_key` / `countable_variant_keys` with registration-time membership
validation, `world/quests/runtime.py::_provision_hunt_targets` calling
`world/maps/monster_provisioning.py::ensure_hunt_targets` inside the acceptance transaction with a closed
refusal vocabulary, `world/quests/describe.py::_describe_species_hunt` rendering region/species/count/variants,
and the authored `rating_rationale_zh` / `background_flavor_zh` fields on `QuestDefinition`. What does not
exist is a single shipped hunt: `world/quests/catalog.py` still carries only the tier-based
`introductory_hunt`, because the quest change declared the shipped catalog tier-based until approval landed.

The content this change needs is authored and registered:

- `world/lore/monster_placement.py::_AMBIENT_PLACEMENT_DECLARATIONS` (lines 320-346) authors four regions
  and their eligible variants: `eastern_plains` (grain_pecker, flock_leader, burrow_maker, nest_guard;
  quantity 2, capacity 3), `northwest_highland_forest` (wood_stalker, trail_hunter; 1/2),
  `southwest_coast` (shore_walker, reef_warden; 1/2), `western_hills_valleys` (burrow_maker, nest_guard,
  cliff_stepper, pass_warden; 1/2). `southeast_coast` has no ambient rule at all.
- The guild-economy rulebook's `quest_rewards` list is the hand-written reward join, and
  `world/rules/quest_issuance.py::resolve_issuance` resolves a `guild:` issuer key straight out of the
  registered offer — so a catalog definition plus a reward row is a complete, acceptable commission.
- The bestiary's per-species 委託背景示例 are approved narrative, and the bestiary's own usage boundary
  sanctions carrying them in the structured field while the author supplies rank and rating rationale
  separately.

## Goals / Non-Goals

**Goals:** six published hunts matching the authored placement one-for-one; counts inside the authored
supply; authored ranks, rationales, flavors, and rank-banded rewards; a content contract that keeps a
future authored hunt from being unmeetable.

**Non-Goals:** no new objective field, validator branch, rendering change, command, or player-visible
surface; no hunt in a region without authored placement; no hunt over a variant nothing places; no
deadline; no item reward (the reward join stays copper + merit, and monster loot stays the monster side's
business); no ability mechanics or ability claim in prose.

## Decisions

**D-R1 The hunts ride the landed machinery; the change adds content and a content contract.** Coverage is
derived from the placement registry rather than invented: one hunt per (region, species) pair a covered
region places — two in `eastern_plains`, two in `western_hills_valleys`, one each in
`northwest_highland_forest` and `southwest_coast`. Six hunts, six regions' worth of species pairs, and no
hunt for `southeast_coast`, whose only species presence is the boss site the dependent change publishes.

**D-R2 Counts sit at `min(quantity, capacity)` of the region's authored ambient rule.** A rule's
per-coordinate steady state is `quantity` and its ceiling is `capacity`, so a count at their minimum is
never above the region's authored legal supply; the eastern-plains hunts therefore require 2 and the other
four require 1. Region-wide provisioning sums the per-covered-cell headroom (`capacity − living`) and the
acceptance path refuses with a named reason when even that cannot cover a species-specific shortfall, so
the authored number is a solvable target in principle and an authored-overflow is the defect this rule
prevents.

**D-R3 Ranks are authored from the arrangement, and the mid hunts are `D`.** The rank registry's own
descriptions separate the work (`world/lore/guild.py`): `F` "Simple collection and caravan escort
tasks.", `E` "Low-tier monster hunts.", `D` "Party-based dungeon runs.", `C` "Work for an adventurer
capable of acting alone." The approved calibration says a creation-budget character can only chip a
mid-tier defense of 12–20, which is exactly "a party of ordinary adventurers" — so the two mid-tier hunts
are authored `D`, not `C`, and no hunt in this batch is authored above `D`. Consequence worth recording:
the mid hunts' strongest countable variants are graded `C`, so the shipped content itself demonstrates
that a danger grade does not become a quest's rank.

**D-R4 Prose: background flavor reuses the approved bestiary example; rating rationale is newly authored
composition/terrain prose.** The bestiary's boundary forbids treating its example as a published
commission — rank, rationale, and structured objectives must be authored separately, which is precisely
what this change does. No published prose asserts a special ability effect, because none of the six has
mechanics; where a bestiary example describes an effect symptom, the published flavor states the local
conflict instead (the one species affected is published by the dependent site change).

**D-R5 The unmeetable-hunt rule lives in a registered data-contract module, not in registration code.**
Rejected alternative: make `register_quest_definition` demand that the region have an ambient rule with an
eligible ordinary variant and a count within `min(quantity, capacity)`. That would couple the definition
layer to the placement registry, force every synthetic hunt fixture in the suite to install placement rows,
and duplicate a guarantee the acceptance path already owns and reports through named refusals. Shipped
content in this repository is guarded by registered data-contract tests (the lore content module is the
precedent), so the content rule lives there and the runtime rule stays with the runtime.

**D-R6 No documentation change.** `guild list` and `guild show` render the same shape they rendered
before: same one-liner form for a species hunt, same detail sections. Only the offers rendered change, and
the docs describe the surface, not the offer list. `tests/test_command_docs.py` therefore stays green with
no edit — stated here so the absence is a decision rather than an omission.

**D-R7 Rewards are hand-written in the existing join, copper inside the rank band, merit authored by rank.**
Copper: F 40 and 50, E 150 and 180, D 900 and 1100 — each inside its rank's band (`F` 10–100, `E` 100–500,
`D` 500–5000). Merit: 20/25, 45/50, 110/120 — authored per rank, never derived, and small enough that no
single hunt carries a member across a rank-examination threshold on its own.

**D-R8 No deadlines.** The introductory hunt carries none, and a deadline adds a failure mode nobody asked
for; a player exploring the wilderness at walking pace is not the balance target this wave published.

## The authored content

| definition key | display name | rank | count | reward (copper / merit) |
|---|---|---|---|---|
| `eastern_plains_sway_whistle_sparrow` | 驅除東部平原穗鳴雀 | F | 2 | 40 / 20 |
| `eastern_plains_ridge_burrow_hare` | 驅除東部平原築埂兔 | F | 2 | 50 / 25 |
| `northwest_highland_forest_fog_mane_lynx` | 討伐西北高地森林霧鬃山貓 | D | 1 | 900 / 110 |
| `southwest_coast_tide_lamp_crab` | 清理西南海岸潮燈蟹 | E | 1 | 150 / 45 |
| `western_hills_valleys_ridge_burrow_hare` | 清理西部丘陵築埂兔 | E | 1 | 180 / 50 |
| `western_hills_valleys_rock_echo_goat` | 討伐西部丘陵岩響山羊 | D | 1 | 1100 / 120 |

Rating rationales (authored, composition and terrain only):

- sparrow: 低階群居鳥類，較強個體會自不同方向干擾驅趕者；個體不難應付，但數量分散，取巧不易。
- eastern hare: 平原鬆土讓牠們容易鑽回洞道，護巢型又會加固入口；個體不強，逐一找出田埂間的巢口才是難處。
- lynx: 中階獵食者會反覆試探隊伍邊緣，避開完整隊列；高地森林的晨霧讓接近方向難以判斷，落單的人風險明顯上升。
- crab: 低階甲殼類，但守礁型占據狹窄洞口，防禦遠高於同階個體；礁隙與潮池讓隊伍無法展開，只能逐處清理。
- western hare: 谷地的築埂兔沿灌溉渠築巢，土埂堵住分水口；渠岸狹窄又讓較強個體難以繞過，得在水道旁動手。
- goat: 中階個體，守隘型會守住岩坡入口；坡面狹窄、碎石鬆動，隊伍難以同時展開，只能沿單側接近。

Background flavors (the bestiary's approved example for that species, verbatim):

- sparrow: 收穫已近尾聲，東側田區每天清晨仍有成群穗鳴雀來訪。農戶請公會處理持續侵入的族群，以免今年最後一批穀物留不下來。
- eastern hare: 平原邊緣的鬆土帶出現新的築埂兔巢，坑洞妨礙農具與牲畜通行。農戶請公會清除這一帶的族群，讓田間作業恢復。
- lynx: 高地運輸隊連續在晨霧中失去馱獸，獵人找到的足跡始終沿道路外緣移動。部族請公會處理已開始追逐運輸隊的個體。
- crab: 港外的候船燈附近聚集了一批潮燈蟹，已有夜歸小船認錯泊岸方向。碼頭請公會清理這處聚集地，恢復燈號辨識。
- western hare: 兩戶農家原以為渠水不足是分水爭議，查找後才發現分水口旁有築埂兔巢。公會受託處理占據渠岸的族群，讓灌溉恢復。
- goat: 採石場的運料路被岩響山羊占據。工人能聽見上方敲岩聲，卻不敢再推車通過。業主請公會處理守路個體，重新開通運料線。

## Risks / Trade-offs

- Early in a world's life the region may hold fewer eligible individuals than a 2-count eastern-plains hunt
  needs → the acceptance guarantee provisions up to authored capacity and, if even that cannot cover the
  shortfall, refuses with its named reason; the board row stays visible because rank eligibility is not
  availability, and the refusal is the landed contract's own answer.
- A development database whose ambient individuals were built under the interim tier band holds slightly
  different numbers than the approved ones → the guarantee counts individuals, not their stats, so the
  hunts remain completable; change 1 documents the divergence and builds no migration.
- Six new offers change the board's contents for every rank → intended; the two F hunts are the first
  board rows a fresh member can afford in rank order, which is the point of publishing them.
- One kill can legitimately credit two records: a species hunt counts any eligible defeat in its region,
  and the ambient owner's own count includes site-owned individuals, so killing a site's individual can
  also advance a regional hunt of the same species. That is intended — both are hunts over the same
  world, each record credits each persistent identity once, and excluding another owner's individuals
  would contradict the landed definition of region-eligible targets. The implementer SHALL NOT "fix" it.

## Open Questions

None. The bound clear-outs are the dependent change's scope.
