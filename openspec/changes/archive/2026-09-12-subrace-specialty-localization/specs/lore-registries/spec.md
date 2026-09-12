# Delta: lore-registries — subrace specialty localization

Authored against the **post-archive** text of `openspec/specs/lore-registries/spec.md` produced
by `human-subrace-lineage-rework` (Change 1). The MODIFIED requirement below carries Change 1's
requirement body and every one of its scenarios over verbatim — the human five `specialty`
strings are Change 1's and are NOT rewritten here — and adds exactly two scenarios pinning the
three elf and seven beastfolk `specialty` values verbatim.

## ADDED Requirements

### Requirement: Subrace specialty prose is server-owned Traditional Chinese for every entry
Every `Subrace.specialty` value in `SUBRACE_REGISTRY` SHALL be Traditional Chinese (zh-TW)
player-facing prose, derived server-side from the registry and rendered verbatim to the player by
the character-creation surfaces (`commands/character_creation.py` renders
`{display_name_zh}（{common_name_zh}）——{specialty}`; the WebClient creation menu uses
`entry.specialty` as the subrace description). No `specialty` value SHALL contain an English
sentence: the field is the server-owned label text for a Chinese subrace name, exactly as the
creation panel's `sex` options are server-owned Traditional Chinese labels
(`webclient-character-creation-ui`), and no browser-side translation or English fallback exists.
This contract binds all fifteen entries — the five human bloodlines, the three elf branches, and
the seven beastfolk subspecies — and every value SHALL stay within the creation protocol's
`MAX_SPECIALTY_CODE_POINTS` (256) bound so it ships on the same path unchanged.

#### Scenario: Every specialty renders as Chinese beside its Chinese name
- **WHEN** a player building a custom character is shown a subrace line — the CLI prompt
  `{display_name_zh}（{common_name_zh}）——{specialty}` or the WebClient menu description — for
  any of the fifteen subraces
- **THEN** the whole line is Traditional Chinese with no English sentence embedded in it, since
  `specialty` is server-owned registry prose derived server-side rather than a client-translated
  or client-owned string

#### Scenario: Registry inspection finds no English prose in any of the fifteen specialties
- **WHEN** every one of the fifteen `SUBRACE_REGISTRY` entries' `specialty` values is inspected
  at test time
- **THEN** each value contains at least one CJK ideograph and zero ASCII letters (`A-Z`/`a-z`) —
  none of the fifteen approved strings contains a single ASCII letter, so the rule needs no
  parenthetical-exception mechanism, and a value such as
  `The lower class: farmers and laborers.` fails the assertion the moment it is reintroduced

#### Scenario: A localized specialty still fits the creation protocol bound
- **WHEN** every `specialty` value is measured against `MAX_SPECIALTY_CODE_POINTS`
- **THEN** each is at most 256 code points, so the WebClient creation panel ships the field
  through the existing validation path with no protocol change

## MODIFIED Requirements

### Requirement: Subrace registry covers elf branches, beastfolk subspecies, and human bloodline subraces with stat modifiers
`world/lore/races.py` SHALL define a frozen `StatModifiers` dataclass with fields `atk_phys`,
`agility`, and `defense` (each a `float` fractional delta, default `0.0`), a frozen `Subrace`
dataclass with fields `key`, `race_key`, `display_name_zh`, `common_name_zh`, `population`,
`home_anchor_key`, `affinity_elements`, `specialty`, `static_modifiers`, and `vital_overrides`, and
a module-level `SUBRACE_REGISTRY: dict[str, Subrace]` containing the three elf branches
(`fionnen`, `ciaran`, `eolas`), the seven named beastfolk subspecies (`wolfkin`, `catkin`,
`bearkin`, `rabbitkin`, `bovinekin`, `tigerkin`, `foxkin`), and the five named human bloodline
subraces (`human_royal`, `human_noble`, `human_coastal`, `human_plains`, `human_highland`), so
that every race in `RACE_REGISTRY` has at least one subrace and no player-facing subrace selection
ever needs a "none" option.

#### Scenario: Every subrace references a real race
- **WHEN** every entry in `SUBRACE_REGISTRY` is inspected
- **THEN** each entry's `race_key` exists as a key in `RACE_REGISTRY`

#### Scenario: Every race has at least one subrace
- **WHEN** each key of `RACE_REGISTRY` is inspected against `SUBRACE_REGISTRY`
- **THEN** for every race key there is at least one `SUBRACE_REGISTRY` entry whose `race_key`
  equals it, including `human`

#### Scenario: Every elf branch has a home village anchor
- **WHEN** `SUBRACE_REGISTRY["fionnen"]`, `["ciaran"]`, and `["eolas"]` are inspected
- **THEN** each has a non-`None` `home_anchor_key` that resolves to an entry in `ANCHOR_REGISTRY`
  whose `kind` is `AnchorKind.ELVEN_VILLAGE`

#### Scenario: Beastfolk subspecies have no fabricated population figures
- **WHEN** the seven beastfolk subspecies entries are inspected
- **THEN** each has `population=None`, since `world_info.md` gives no per-subspecies count

#### Scenario: Elf branches carry no stat-distribution skew
- **WHEN** `SUBRACE_REGISTRY["fionnen"]`, `["ciaran"]`, and `["eolas"]` are inspected
- **THEN** each has `static_modifiers == StatModifiers()` (all fields `0.0`) and
  `vital_overrides is None`, since `world_info.md` documents no per-branch stat skew for elves

#### Scenario: Beastfolk subspecies carry the documented stat-distribution skew
- **WHEN** `SUBRACE_REGISTRY["catkin"]`, `["bearkin"]`, `["rabbitkin"]`, `["bovinekin"]`,
  `["tigerkin"]`, and `["foxkin"]` are inspected
- **THEN** each has all three `static_modifiers` fields matching `world_info.md`'s 「亞種數值傾向」
  block exactly (e.g. `catkin.static_modifiers == StatModifiers(atk_phys=-0.10, agility=0.40,
  defense=-0.30)`), and `wolfkin.static_modifiers == StatModifiers()` (balanced, all zero)

#### Scenario: Human bloodline subraces carry zero-sum stat-distribution skew
- **WHEN** every one of the five human `SUBRACE_REGISTRY` entries' `static_modifiers` is inspected
- **THEN** `abs(atk_phys + agility + defense) <= 1e-12` for every entry, so a bloodline subrace skews
  the three physical axes without shifting aggregate physical power, and the same values are
  justified per-lineage in `world_info.md`'s human 「數值傾向」 block

#### Scenario: Human subrace keys name geographic and hereditary lineages
- **WHEN** `SUBRACE_REGISTRY` is inspected
- **THEN** the human keys are exactly `human_royal`, `human_noble`, `human_coastal`,
  `human_plains`, and `human_highland`; no legacy wealth-ladder key (`human_wealthy`,
  `human_commoner`, `human_laborer`) appears as a subrace key anywhere, and no human subrace is
  named after an occupation — 農民 is an occupation practised within `human_plains`, not a subrace

#### Scenario: Human subrace naming is synonymous across key and Chinese fields
- **WHEN** the five human `SUBRACE_REGISTRY` entries are inspected
- **THEN** `display_name_zh`/`common_name_zh` are exactly 王族/王室血脈, 貴族/貴族血脈,
  濱海民/濱海血脈, 平原民/平原血脈, and 山地民/山地血脈 for `human_royal`, `human_noble`,
  `human_coastal`, `human_plains`, and `human_highland` respectively, and for the three
  geographic lineages the key, `display_name_zh`, and `common_name_zh` are the same word in the
  three forms (coastal/plains/highland ↔ 濱海/平原/山地 ↔ 濱海血脈/平原血脈/山地血脈), the
  `common_name_zh` being `display_name_zh` plus the 血脈 suffix

#### Scenario: Human bloodline stat modifiers keep the documented lineage values
- **WHEN** the five human `SUBRACE_REGISTRY` entries' `static_modifiers` and `vital_overrides`
  are inspected
- **THEN** `human_royal` is `StatModifiers(atk_phys=-0.05, agility=-0.05, defense=0.10)` with
  `vital_overrides["mp"] == (120, 220)`; `human_noble` is `StatModifiers(atk_phys=0.10,
  agility=0.05, defense=-0.15)`; `human_coastal` is `StatModifiers(atk_phys=0.05, agility=0.10,
  defense=-0.15)`; `human_plains` is `StatModifiers()` (the human zero baseline, so the largest
  human group's demographics and mechanics agree); and `human_highland` is
  `StatModifiers(atk_phys=0.10, agility=-0.15, defense=0.05)` — every value unchanged by the
  rename, each carrying the lineage rationale in `world_info.md`'s human 「數值傾向」 block
  (王都王室重統御學識; 領地貴族自幼習劍術馬術; 港市海岸船上作業練就輕捷; 東部平原農耕與工坊
  並重; 西部丘陵谷地礦坑與工坊重勞動)

#### Scenario: Human specialty prose states the lineage and its bent
- **WHEN** the five human `SUBRACE_REGISTRY` entries' `specialty` fields are inspected
- **THEN** they are exactly, verbatim:
  王族 → 「王都王室的血脈。自幼受統御與學識的教養，長於謀略而非武藝，魔力底蘊高於同族。」;
  貴族 → 「領地貴族的血脈。自幼習劍術與馬術，攻守取捨偏向進取。」;
  濱海民 → 「世居港市與海岸的血脈。船上作業與碼頭往來練就輕捷身手，慣穿輕裝。」;
  平原民 → 「世居平原與城鎮的血脈。農耕與工坊並重，各項資質最為均衡。」;
  山地民 → 「世居丘陵與谷地的血脈。礦坑與工坊的重勞動造就體魄與耐久，不以靈巧取勝。」

#### Scenario: Elf branch specialty prose names home, affinity, and art
- **WHEN** the three elf `SUBRACE_REGISTRY` entries' `specialty` fields are inspected
- **THEN** they are exactly, verbatim:
  斐歐恩族 → 「翠綠森林村的森林精靈。親和光屬性魔法，弓術與光法並修，從容而精準。」;
  基亞蘭族 → 「暗影谷村的黑暗精靈。親和火與暗屬性魔法，刀術造詣尤深，攻勢凌厲。」;
  伊歐拉斯族 → 「幽月谷村的幻童精靈。外表永駐童年，親和所有屬性魔法，並擅長神之秘法。」 —
  each naming the branch's own village, affinity, and signature art from `world_info.md`'s 三分支
  block, with no occupational determinism

#### Scenario: Beastfolk specialty prose names a physique, its habit, and its tradeoff
- **WHEN** the seven beastfolk `SUBRACE_REGISTRY` entries' `specialty` fields are inspected
- **THEN** they are exactly, verbatim:
  狼人 → 「群居狩獵的狼人，體格均衡而耐力出眾，慣於配合同伴作戰，無突出短板亦無驚人天賦。」;
  貓人 → 「身形輕盈、舉步無聲的貓人，敏捷遠出同族之上，代價是肌骨纖薄，難以吃下正面重創。」;
  熊人 → 「骨架厚重、力大無窮的熊人，慣用重型武器，卻因轉身遲鈍而追不上靈活的對手。」;
  兔人 → 「奔躍如風的兔人，為獸人之中最快的亞種，擅長遊走遠射，卻經不起近身的一擊。」;
  牛人 → 「身軀如山、皮糙肉厚的牛人，防禦最厚而善於陣地戰，只因其行動緩慢而難以追擊機動的敵人。」;
  虎人 → 「爆發力驚人、攻速兼備的虎人，出擊凌厲而防禦為全亞種最弱，講求一擊制敵而非持久消耗。」;
  狐人 → 「體格在獸人之中不突出的狐人，以體力換來同族最深厚的魔力底蘊，是最接近施法者的亞種。」 —
  each naming a physique and its habit plus the tradeoff its `static_modifiers` encode, matching
  `world_info.md`'s 「亞種數值傾向」 block, never an occupation as identity

#### Scenario: Every beastfolk subspecies' static_modifiers sum to zero
- **WHEN** every one of the seven beastfolk `SUBRACE_REGISTRY` entries' `static_modifiers` is
  inspected
- **THEN** `abs(atk_phys + agility + defense) <= 1e-12` for every entry, with no exemption for
  `foxkin` — its physical-axis modifiers alone already sum to zero (`-0.05 + 0.15 + -0.10 ==
  0.0`); its separate MP vital-band override (below) is a different, independently-checked
  mechanism and is not required to make this sum work; the tolerance accounts only for binary
  `float` representation of the documented decimal percentages

#### Scenario: Foxkin overrides its MP vital band above the species baseline
- **WHEN** `SUBRACE_REGISTRY["foxkin"]` is inspected
- **THEN** `vital_overrides` is not `None` and `vital_overrides["mp"] == (50, 70)`, which is a
  higher band than `RACE_REGISTRY["beastfolk"].vital_baseline.mp` ((30, 50)) — confirming a
  subrace can override a vital bound, not only a static one

#### Scenario: Every other subrace leaves vital_overrides unset
- **WHEN** every `SUBRACE_REGISTRY` entry other than `"foxkin"` and any human bloodline subrace that
  documents a `vital_overrides` band is inspected
- **THEN** `vital_overrides is None` for that entry, meaning it uses `RaceProfile.vital_baseline`
  unmodified
