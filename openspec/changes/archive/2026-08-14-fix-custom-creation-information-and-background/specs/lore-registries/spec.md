## RENAMED Requirements

- FROM: `### Requirement: Subrace registry covers elf branches and beastfolk subspecies with stat modifiers`
- TO: `### Requirement: Subrace registry covers elf branches, beastfolk subspecies, and human social classes with stat modifiers`

## MODIFIED Requirements

### Requirement: Subrace registry covers elf branches, beastfolk subspecies, and human social classes with stat modifiers
`world/lore/races.py` SHALL define a frozen `StatModifiers` dataclass with fields `atk_phys`,
`agility`, and `defense` (each a `float` fractional delta, default `0.0`), a frozen `Subrace`
dataclass with fields `key`, `race_key`, `display_name_zh`, `common_name_zh`, `population`,
`home_anchor_key`, `affinity_elements`, `specialty`, `static_modifiers`, and `vital_overrides`, and
a module-level `SUBRACE_REGISTRY: dict[str, Subrace]` containing the three elf branches
(`fionnen`, `ciaran`, `eolas`), the seven named beastfolk subspecies (`wolfkin`, `catkin`,
`bearkin`, `rabbitkin`, `bovinekin`, `tigerkin`, `foxkin`), and the five named human social
classes (`human_royal`, `human_noble`, `human_wealthy`, `human_commoner`, `human_laborer`), so
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

#### Scenario: Human social classes carry zero-sum stat-distribution skew
- **WHEN** every one of the five human `SUBRACE_REGISTRY` entries' `static_modifiers` is inspected
- **THEN** `abs(atk_phys + agility + defense) <= 1e-12` for every entry, so a social class skews the
  three physical axes without shifting aggregate physical power, and each entry's
  `display_name_zh`/`common_name_zh`/`specialty` follows the social ladder in
  `world_info.md` (皇族與大貴族 / 中小貴族 / 富裕平民 / 普通平民 / 底層平民)

#### Scenario: Every beastfolk subspecies' static_modifiers sum to zero
- **WHEN** every one of the seven beastfolk `SUBRACE_REGISTRY` entries' `static_modifiers` is
  inspected
- **THEN** `abs(atk_phys + agility + defense) <= 1e-12` for every entry, with no exemption for `foxkin` —
  its physical-axis modifiers alone already sum to zero (`-0.05 + 0.15 + -0.10 == 0.0`); its
  separate MP vital-band override (below) is a different, independently-checked mechanism and is
  not required to make this sum work; the tolerance accounts only for binary `float`
  representation of the documented decimal percentages

#### Scenario: Foxkin overrides its MP vital band above the species baseline
- **WHEN** `SUBRACE_REGISTRY["foxkin"]` is inspected
- **THEN** `vital_overrides` is not `None` and `vital_overrides["mp"] == (50, 70)`, which is a
  higher band than `RACE_REGISTRY["beastfolk"].vital_baseline.mp` ((30, 50)) — confirming a subrace
  can override a vital bound, not only a static one

#### Scenario: Every other subrace leaves vital_overrides unset
- **WHEN** every `SUBRACE_REGISTRY` entry other than `"foxkin"` and any human social class that
  documents a `vital_overrides` band is inspected
- **THEN** `vital_overrides is None` for that entry, meaning it uses `RaceProfile.vital_baseline`
  unmodified
