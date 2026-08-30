## MODIFIED Requirements

### Requirement: SKILL_REGISTRY contains the full 火-element spell set
`world/skills/registry.py`'s `SKILL_REGISTRY` SHALL declare all ten 火-element spells from design doc
§4.4, each with the exact key, Traditional Chinese `label`, `SkillKind.ACTIVE`, the tier-appropriate
`TargetSpec`/`FactionConstraint` pair, `cost={"mp": <value>}`, `element=ELEMENT_REGISTRY["fire"]`, and
an `effects` list that parses cleanly under `skill-effects-typed-model`'s typed dispatch table. Each
spell's tier SHALL be derivable from its registry grouping (position and MP cost band) without a
dedicated tier field; the tier grouping is a data label only — the numeric cast gate is
retired, and the lineage gate that replaces it reads the registry tree, not the MP band.

| Key | 名稱 | 位階 | TargetSpec | Cost | effects |
|---|---|---|---|---|---|
| `fire_ball` | 火球術 | 學徒 | `TargetSpec.SINGLE` | `mp=14` | `damage:fire:magic` |
| `fire_arrow` | 火焰箭 | 學徒 | `TargetSpec.SINGLE` | `mp=10` | `damage:fire:magic` |
| `firestorm` | 火焰風暴 | 術師 | `TargetSpec.AREA` | `mp=30` | `damage:fire:magic` |
| `scorching_wave` | 灼熱波動 | 術師 | `TargetSpec.SINGLE` | `mp=24` | `damage:fire:magic`, `buff_apply:fire_scorch` |
| `lava_burst` | 熔岩術 | 大師 | `TargetSpec.AREA` | `mp=52` | `damage:fire:magic` |
| `infernal_wrap` | 業火纏繞 | 大師 | `TargetSpec.SINGLE` | `mp=42` | `damage:fire:magic` |
| `dragon_flame` | 龍炎術 | 賢者 | `TargetSpec.AREA` | `mp=95` | `damage:fire:magic` |
| `hellfire` | 煉獄業火 | 賢者 | `TargetSpec.SINGLE` | `mp=78` | `damage:fire:magic` |
| `phoenix_eternal_flame` | 不滅鳳凰焰 | 主宰 | `TargetSpec.AREA` | `mp=150` | `damage:fire:magic`, `self_heal` |
| `world_ending_blaze` | 焚世終焰 | 主宰 | `TargetSpec.SINGLE` | `mp=130` | `damage:fire:magic` |

#### Scenario: All ten 火 spell keys exist with correct kind, target, and cost
- **WHEN** `SKILL_REGISTRY` is inspected for the ten 火 keys (`fire_ball`, `fire_arrow`, `firestorm`, `scorching_wave`, `lava_burst`, `infernal_wrap`, `dragon_flame`, `hellfire`, `phoenix_eternal_flame`, `world_ending_blaze`)
- **THEN** each key is present with `SkillKind.ACTIVE`, `element=ELEMENT_REGISTRY["fire"]`, the
  `TargetSpec`/`FactionConstraint` pair and `cost["mp"]` value documented in this change's `design.md`,
  and a nonempty `effects` list matching this change's `design.md`

#### Scenario: The pre-existing 火 anchor skill(s) were recosted per §4.3, not duplicated
- **WHEN** `SKILL_REGISTRY` is inspected for `fire_ball`
- **THEN** it is present exactly once (no duplicate key), with its `cost["mp"]` updated
  (`fire_ball` from `mp=20` to `mp=14`), and every other field (`label`, `target_spec`, `element`, `effects`) unchanged from before
  this change

### Requirement: SKILL_REGISTRY contains the full 水-element spell set
`world/skills/registry.py`'s `SKILL_REGISTRY` SHALL declare all ten 水-element spells from design doc
§4.4, each with the exact key, Traditional Chinese `label`, `SkillKind.ACTIVE`, the tier-appropriate
`TargetSpec`/`FactionConstraint` pair, `cost={"mp": <value>}`, `element=ELEMENT_REGISTRY["water"]`, and
an `effects` list that parses cleanly under `skill-effects-typed-model`'s typed dispatch table. Each
spell's tier SHALL be derivable from its registry grouping (position and MP cost band) without a
dedicated tier field; the tier grouping is a data label only — the numeric cast gate is
retired, and the lineage gate that replaces it reads the registry tree, not the MP band.

| Key | 名稱 | 位階 | TargetSpec | Cost | effects |
|---|---|---|---|---|---|
| `water_bolt` | 水箭術 | 學徒 | `TargetSpec.SINGLE` | `mp=12` | `damage:water:magic` |
| `minor_heal` | 治癒滴露 | 學徒 | `TargetSpec.SINGLE` | `mp=11` | `heal:single` |
| `healing_spring` | 治癒之泉 | 術師 | `TargetSpec.AREA` | `mp=28` | `heal:area` |
| `water_shield` | 水盾術 | 術師 | `TargetSpec.SINGLE` | `mp=22` | `buff_apply:water_shield` |
| `abyssal_whirlpool` | 深海漩渦 | 大師 | `TargetSpec.AREA` | `mp=50` | `damage:water:magic`, `buff_apply:water_bind` |
| `wellspring_of_life` | 生命湧泉 | 大師 | `TargetSpec.SINGLE` | `mp=40` | `heal:single` |
| `tsunami` | 海嘯術 | 賢者 | `TargetSpec.AREA` | `mp=95` | `damage:water:magic` |
| `tidal_revival` | 復生之潮 | 賢者 | `TargetSpec.SINGLE` | `mp=78` | `heal:single` |
| `sea_of_life` | 生命之海 | 主宰 | `TargetSpec.AREA` | `mp=160` | `heal:area` |
| `abyssal_tide` | 深淵巨潮 | 主宰 | `TargetSpec.AREA` | `mp=145` | `damage:water:magic` |

#### Scenario: All ten 水 spell keys exist with correct kind, target, and cost
- **WHEN** `SKILL_REGISTRY` is inspected for the ten 水 keys (`water_bolt`, `minor_heal`, `healing_spring`, `water_shield`, `abyssal_whirlpool`, `wellspring_of_life`, `tsunami`, `tidal_revival`, `sea_of_life`, `abyssal_tide`)
- **THEN** each key is present with `SkillKind.ACTIVE`, `element=ELEMENT_REGISTRY["water"]`, the
  `TargetSpec`/`FactionConstraint` pair and `cost["mp"]` value documented in this change's `design.md`,
  and a nonempty `effects` list matching this change's `design.md`

### Requirement: SKILL_REGISTRY contains the full 土-element spell set
`world/skills/registry.py`'s `SKILL_REGISTRY` SHALL declare all ten 土-element spells from design doc
§4.4, each with the exact key, Traditional Chinese `label`, `SkillKind.ACTIVE`, the tier-appropriate
`TargetSpec`/`FactionConstraint` pair, `cost={"mp": <value>}`, `element=ELEMENT_REGISTRY["earth"]`, and
an `effects` list that parses cleanly under `skill-effects-typed-model`'s typed dispatch table. Each
spell's tier SHALL be derivable from its registry grouping (position and MP cost band) without a
dedicated tier field; the tier grouping is a data label only — the numeric cast gate is
retired, and the lineage gate that replaces it reads the registry tree, not the MP band.

| Key | 名稱 | 位階 | TargetSpec | Cost | effects |
|---|---|---|---|---|---|
| `stone_shard` | 石礫術 | 學徒 | `TargetSpec.SINGLE` | `mp=12` | `damage:earth:magic` |
| `hardened_skin` | 硬化肌膚 | 學徒 | `TargetSpec.SELF` | `mp=10` | `self_buff_apply:earth_hardened_skin` |
| `stone_armor` | 岩甲術 | 術師 | `TargetSpec.SINGLE` | `mp=24` | `buff_apply:earth_stone_armor` |
| `dust_veil` | 沙塵術 | 術師 | `TargetSpec.AREA` | `mp=22` | `buff_apply:earth_dust_veil` |
| `earth_bind` | 地縛術 | 大師 | `TargetSpec.AREA` | `mp=42` | `buff_apply:earth_root` |
| `rockslide` | 岩壁崩落 | 大師 | `TargetSpec.AREA` | `mp=48` | `damage:earth:magic` |
| `earthquake` | 地震術 | 賢者 | `TargetSpec.AREA` | `mp=90` | `damage:earth:magic` |
| `earthen_ward` | 大地庇護 | 賢者 | `TargetSpec.AREA` | `mp=75` | `buff_apply:earth_ward` |
| `mountain_collapse` | 山嶽崩落 | 主宰 | `TargetSpec.AREA` | `mp=150` | `damage:earth:magic` |
| `earths_judgment` | 大地審判 | 主宰 | `TargetSpec.SINGLE` | `mp=130` | `damage:earth:magic` |

#### Scenario: All ten 土 spell keys exist with correct kind, target, and cost
- **WHEN** `SKILL_REGISTRY` is inspected for the ten 土 keys (`stone_shard`, `hardened_skin`, `stone_armor`, `dust_veil`, `earth_bind`, `rockslide`, `earthquake`, `earthen_ward`, `mountain_collapse`, `earths_judgment`)
- **THEN** each key is present with `SkillKind.ACTIVE`, `element=ELEMENT_REGISTRY["earth"]`, the
  `TargetSpec`/`FactionConstraint` pair and `cost["mp"]` value documented in this change's `design.md`,
  and a nonempty `effects` list matching this change's `design.md`

### Requirement: SKILL_REGISTRY contains the full 風-element spell set
`world/skills/registry.py`'s `SKILL_REGISTRY` SHALL declare all ten 風-element spells from design doc
§4.4, each with the exact key, Traditional Chinese `label`, the tier-appropriate
`TargetSpec`/`FactionConstraint` pair, `cost={"mp": <value>}`, `element=ELEMENT_REGISTRY["wind"]`, and
an `effects` list that parses cleanly under `skill-effects-typed-model`'s typed dispatch table. Nine
of the ten declare `SkillKind.ACTIVE`; `flight` stays `SkillKind.PASSIVE` per `movement-skill-waiver`.
Each spell's tier SHALL be derivable from its registry grouping (position and MP cost band) without a
dedicated tier field; the tier grouping is a data label only — the numeric cast gate is
retired, and the lineage gate that replaces it reads the registry tree, not the MP band.

| Key | 名稱 | 位階 | TargetSpec | Cost | effects |
|---|---|---|---|---|---|
| `wind_blade` | 風刃術 | 學徒 | `TargetSpec.AREA` | `mp=14` | `damage:wind:magic` |
| `gale_step` | 疾風術 | 學徒 | `TargetSpec.SELF` | `mp=10` | `self_buff_apply:wind_haste` |
| `flight` | 飛行術 | 術師 | `TargetSpec.SELF` | `mp=22` | `movement:flight` |
| `tornado_blade` | 龍捲風刃 | 術師 | `TargetSpec.SINGLE` | `mp=26` | `damage:wind:magic` |
| `storm_domain` | 暴風領域 | 大師 | `TargetSpec.AREA` | `mp=50` | `damage:wind:magic` |
| `gale_dance_strike` | 疾風刃舞 | 大師 | `TargetSpec.SINGLE` | `mp=40` | `damage:wind:magic` |
| `heavens_wrath_storm` | 天譴風暴 | 賢者 | `TargetSpec.AREA` | `mp=90` | `damage:wind:magic` |
| `haste_domain` | 神速領域 | 賢者 | `TargetSpec.AREA` | `mp=70` | `buff_apply:wind_haste_domain` |
| `vacuum_severance` | 真空斬滅 | 主宰 | `TargetSpec.SINGLE` | `mp=130` | `damage:wind:magic` |
| `sky_tempest` | 蒼穹暴風 | 主宰 | `TargetSpec.AREA` | `mp=150` | `damage:wind:magic` |

#### Scenario: All ten 風 spell keys exist with correct kind, target, and cost
- **WHEN** `SKILL_REGISTRY` is inspected for the ten 風 keys (`wind_blade`, `gale_step`, `flight`, `tornado_blade`, `storm_domain`, `gale_dance_strike`, `heavens_wrath_storm`, `haste_domain`, `vacuum_severance`, `sky_tempest`)
- **THEN** each key is present with its documented kind (nine `SkillKind.ACTIVE`; `flight` stays
  `SkillKind.PASSIVE` per `movement-skill-waiver`), `element=ELEMENT_REGISTRY["wind"]`, the
  `TargetSpec`/`FactionConstraint` pair and `cost["mp"]` value documented in this change's `design.md`,
  and a nonempty `effects` list matching this change's `design.md`

#### Scenario: The pre-existing 風 anchor skill(s) were recosted per §4.3, not duplicated
- **WHEN** `SKILL_REGISTRY` is inspected for `wind_blade` and `flight`
- **THEN** each is present exactly once (no duplicate key), with its `cost["mp"]` updated
  (`wind_blade` from `mp=24` to `mp=14`; `flight` from `mp=10` to `mp=22`), and every other field (`label`, `target_spec`, `element`, `effects`) unchanged from before
  this change

### Requirement: SKILL_REGISTRY contains the full 雷-element spell set
`world/skills/registry.py`'s `SKILL_REGISTRY` SHALL declare all ten 雷-element spells from design doc
§4.4, each with the exact key, Traditional Chinese `label`, `SkillKind.ACTIVE`, the tier-appropriate
`TargetSpec`/`FactionConstraint` pair, `cost={"mp": <value>}`, `element=ELEMENT_REGISTRY["lightning"]`, and
an `effects` list that parses cleanly under `skill-effects-typed-model`'s typed dispatch table. Each
spell's tier SHALL be derivable from its registry grouping (position and MP cost band) without a
dedicated tier field; the tier grouping is a data label only — the numeric cast gate is
retired, and the lineage gate that replaces it reads the registry tree, not the MP band.

| Key | 名稱 | 位階 | TargetSpec | Cost | effects |
|---|---|---|---|---|---|
| `spark_shock` | 電擊術 | 學徒 | `TargetSpec.SINGLE` | `mp=13` | `damage:lightning:magic` |
| `static_ward` | 靜電護體 | 學徒 | `TargetSpec.SELF` | `mp=10` | `self_buff_apply:lightning_static_ward` |
| `chain_lightning` | 雷鎖術 | 術師 | `TargetSpec.AREA` | `mp=27` | `damage:lightning:magic` |
| `paralyzing_bolt` | 麻痺電擊 | 術師 | `TargetSpec.SINGLE` | `mp=24` | `damage:lightning:magic`, `buff_apply:paralysis` |
| `thunder_combo` | 雷霆連擊 | 大師 | `TargetSpec.SINGLE` | `mp=46` | `damage:lightning:magic` |
| `lightning_strike` | 落雷術 | 大師 | `TargetSpec.AREA` | `mp=50` | `damage:lightning:magic` |
| `heavens_thunder` | 天雷降臨 | 賢者 | `TargetSpec.AREA` | `mp=92` | `damage:lightning:magic` |
| `thunder_gods_haste` | 雷神之速 | 賢者 | `TargetSpec.SELF` | `mp=68` | `self_buff_apply:lightning_extra_action` |
| `judgement_thunder` | 審判雷霆 | 主宰 | `TargetSpec.SINGLE` | `mp=135` | `damage:lightning:magic` |
| `divine_lightning_slaughter` | 神雷滅殺 | 主宰 | `TargetSpec.AREA` | `mp=155` | `damage:lightning:magic` |

#### Scenario: All ten 雷 spell keys exist with correct kind, target, and cost
- **WHEN** `SKILL_REGISTRY` is inspected for the ten 雷 keys (`spark_shock`, `static_ward`, `chain_lightning`, `paralyzing_bolt`, `thunder_combo`, `lightning_strike`, `heavens_thunder`, `thunder_gods_haste`, `judgement_thunder`, `divine_lightning_slaughter`)
- **THEN** each key is present with `SkillKind.ACTIVE`, `element=ELEMENT_REGISTRY["lightning"]`, the
  `TargetSpec`/`FactionConstraint` pair and `cost["mp"]` value documented in this change's `design.md`,
  and a nonempty `effects` list matching this change's `design.md`

### Requirement: SKILL_REGISTRY contains the full 冰-element spell set
`world/skills/registry.py`'s `SKILL_REGISTRY` SHALL declare all ten 冰-element spells from design doc
§4.4, each with the exact key, Traditional Chinese `label`, `SkillKind.ACTIVE`, the tier-appropriate
`TargetSpec`/`FactionConstraint` pair, `cost={"mp": <value>}`, `element=ELEMENT_REGISTRY["ice"]`, and
an `effects` list that parses cleanly under `skill-effects-typed-model`'s typed dispatch table. Each
spell's tier SHALL be derivable from its registry grouping (position and MP cost band) without a
dedicated tier field; the tier grouping is a data label only — the numeric cast gate is
retired, and the lineage gate that replaces it reads the registry tree, not the MP band.

| Key | 名稱 | 位階 | TargetSpec | Cost | effects |
|---|---|---|---|---|---|
| `ice_shard` | 冰錐術 | 學徒 | `TargetSpec.SINGLE` | `mp=13` | `damage:ice:magic` |
| `frost_breath` | 凍結之息 | 學徒 | `TargetSpec.SINGLE` | `mp=11` | `buff_apply:ice_slow` |
| `ice_wall` | 冰牆術 | 術師 | `TargetSpec.SINGLE` | `mp=25` | `buff_apply:ice_wall` |
| `frost_arrow_rain` | 冷凍箭雨 | 術師 | `TargetSpec.AREA` | `mp=28` | `damage:ice:magic` |
| `permafrost_domain` | 永凍領域 | 大師 | `TargetSpec.AREA` | `mp=48` | `buff_apply:ice_freeze` |
| `ice_prison` | 冰封監牢 | 大師 | `TargetSpec.SINGLE` | `mp=44` | `buff_apply:ice_prison` |
| `blizzard` | 暴風雪 | 賢者 | `TargetSpec.AREA` | `mp=88` | `damage:ice:magic` |
| `absolute_tundra` | 絕對凍土 | 賢者 | `TargetSpec.AREA` | `mp=82` | `damage:ice:magic`, `buff_apply:ice_freeze` |
| `absolute_zero` | 絕對零度 | 主宰 | `TargetSpec.SINGLE` | `mp=140` | `damage:ice:magic`, `buff_apply:ice_freeze` |
| `eternal_ice_field` | 永夜冰原 | 主宰 | `TargetSpec.AREA` | `mp=158` | `damage:ice:magic`, `buff_apply:ice_freeze` |

#### Scenario: All ten 冰 spell keys exist with correct kind, target, and cost
- **WHEN** `SKILL_REGISTRY` is inspected for the ten 冰 keys (`ice_shard`, `frost_breath`, `ice_wall`, `frost_arrow_rain`, `permafrost_domain`, `ice_prison`, `blizzard`, `absolute_tundra`, `absolute_zero`, `eternal_ice_field`)
- **THEN** each key is present with `SkillKind.ACTIVE`, `element=ELEMENT_REGISTRY["ice"]`, the
  `TargetSpec`/`FactionConstraint` pair and `cost["mp"]` value documented in this change's `design.md`,
  and a nonempty `effects` list matching this change's `design.md`

### Requirement: SKILL_REGISTRY contains the full 光-element spell set
`world/skills/registry.py`'s `SKILL_REGISTRY` SHALL declare all ten 光-element spells from design doc
§4.4, each with the exact key, Traditional Chinese `label`, `SkillKind.ACTIVE`, the tier-appropriate
`TargetSpec`/`FactionConstraint` pair, `cost={"mp": <value>}`, `element=ELEMENT_REGISTRY["light"]`, and
an `effects` list that parses cleanly under `skill-effects-typed-model`'s typed dispatch table. Each
spell's tier SHALL be derivable from its registry grouping (position and MP cost band) without a
dedicated tier field; the tier grouping is a data label only — the numeric cast gate is
retired, and the lineage gate that replaces it reads the registry tree, not the MP band.

| Key | 名稱 | 位階 | TargetSpec | Cost | effects |
|---|---|---|---|---|---|
| `heal` | 治癒術 | 學徒 | `TargetSpec.SINGLE` | `mp=12` | `heal:single` |
| `light_arrow` | 光箭術 | 學徒 | `TargetSpec.SINGLE` | `mp=14` | `damage:light:magic` |
| `purify` | 淨化術 | 術師 | `TargetSpec.SINGLE` | `mp=22` | `cleanse:status` |
| `mass_heal` | 群體治癒 | 術師 | `TargetSpec.AREA` | `mp=30` | `heal:area` |
| `advanced_heal` | 高級治癒 | 大師 | `TargetSpec.SINGLE` | `mp=46` | `heal:single` |
| `holy_shield` | 聖盾術 | 大師 | `TargetSpec.SINGLE` | `mp=40` | `buff_apply:light_holy_shield` |
| `holy_radiance` | 神聖光輝 | 賢者 | `TargetSpec.AREA` | `mp=90` | `damage:light:magic` |
| `revival_light` | 復甦之光 | 賢者 | `TargetSpec.SINGLE` | `mp=82` | `heal:single` |
| `goddess_blessing` | 女神降福 | 主宰 | `TargetSpec.AREA` | `mp=145` | `heal:area`, `buff_apply:light_blessing` |
| `heavens_judgment_light` | 天啟聖裁 | 主宰 | `TargetSpec.SINGLE` | `mp=135` | `damage:light:magic` |

#### Scenario: All ten 光 spell keys exist with correct kind, target, and cost
- **WHEN** `SKILL_REGISTRY` is inspected for the ten 光 keys (`heal`, `light_arrow`, `purify`, `mass_heal`, `advanced_heal`, `holy_shield`, `holy_radiance`, `revival_light`, `goddess_blessing`, `heavens_judgment_light`)
- **THEN** each key is present with `SkillKind.ACTIVE`, `element=ELEMENT_REGISTRY["light"]`, the
  `TargetSpec`/`FactionConstraint` pair and `cost["mp"]` value documented in this change's `design.md`,
  and a nonempty `effects` list matching this change's `design.md`

### Requirement: SKILL_REGISTRY contains the full 暗-element spell set
`world/skills/registry.py`'s `SKILL_REGISTRY` SHALL declare all ten 暗-element spells from design doc
§4.4, each with the exact key, Traditional Chinese `label`, `SkillKind.ACTIVE`, the tier-appropriate
`TargetSpec`/`FactionConstraint` pair, `cost={"mp": <value>}`, `element=ELEMENT_REGISTRY["dark"]`, and
an `effects` list that parses cleanly under `skill-effects-typed-model`'s typed dispatch table. Each
spell's tier SHALL be derivable from its registry grouping (position and MP cost band) without a
dedicated tier field; the tier grouping is a data label only — the numeric cast gate is
retired, and the lineage gate that replaces it reads the registry tree, not the MP band.

| Key | 名稱 | 位階 | TargetSpec | Cost | effects |
|---|---|---|---|---|---|
| `shadow_bolt` | 暗影箭 | 學徒 | `TargetSpec.SINGLE` | `mp=14` | `damage:dark:magic` |
| `weaken` | 衰弱術 | 學徒 | `TargetSpec.SINGLE` | `mp=11` | `buff_apply:dark_atk_down` |
| `curse` | 詛咒術 | 術師 | `TargetSpec.SINGLE` | `mp=26` | `buff_apply:dark_curse` |
| `dark_burst` | 闇裂術 | 術師 | `TargetSpec.AREA` | `mp=29` | `damage:dark:magic` |
| `dark_corrosion_domain` | 闇蝕領域 | 大師 | `TargetSpec.AREA` | `mp=47` | `damage:dark:magic`, `buff_apply:dark_corrosion` |
| `shadow_torment` | 暗影凌遲 | 大師 | `TargetSpec.SINGLE` | `mp=41` | `damage:dark:magic`, `buff_apply:dark_corrosion` |
| `abyss_devour` | 深淵吞噬 | 賢者 | `TargetSpec.SINGLE` | `mp=85` | `damage:dark:magic` |
| `dark_dominion` | 黑暗支配 | 賢者 | `TargetSpec.AREA` | `mp=72` | `buff_apply:fear` |
| `void_annihilation` | 終焉黑洞 | 主宰 | `TargetSpec.AREA` | `mp=155` | `damage:dark:magic` |
| `netherworld_judgment` | 冥府審判 | 主宰 | `TargetSpec.SINGLE` | `mp=135` | `damage:dark:magic` |

#### Scenario: All ten 暗 spell keys exist with correct kind, target, and cost
- **WHEN** `SKILL_REGISTRY` is inspected for the ten 暗 keys (`shadow_bolt`, `weaken`, `curse`, `dark_burst`, `dark_corrosion_domain`, `shadow_torment`, `abyss_devour`, `dark_dominion`, `void_annihilation`, `netherworld_judgment`)
- **THEN** each key is present with `SkillKind.ACTIVE`, `element=ELEMENT_REGISTRY["dark"]`, the
  `TargetSpec`/`FactionConstraint` pair and `cost["mp"]` value documented in this change's `design.md`,
  and a nonempty `effects` list matching this change's `design.md`

### Requirement: All eight elements have a mastery skill
`SKILL_REGISTRY` SHALL contain `water_mastery`, `earth_mastery`, `lightning_mastery`, and
`ice_mastery`, each `PASSIVE`, `TargetSpec.NONE`, with `element` set to the corresponding
`world.lore.elements.ELEMENT_REGISTRY` entry and `effects=["passive_trait:element_mastery"]`, matching
the existing four mastery skills' (`fire_mastery`/`dark_mastery`/`wind_mastery`/`light_mastery`) shape
exactly (all eight move to the flavor form together with the retired cast gate).

#### Scenario: All eight elemental-mastery skills are present
- **WHEN** `SKILL_REGISTRY` is inspected
- **THEN** it contains a `PASSIVE` entry for fire, water, wind, earth, lightning, ice, light, and dark
  mastery, each with `element` set to the corresponding `ELEMENT_REGISTRY` entry

### Requirement: reincarnation_boon_yuna's effect string is well-formed
`reincarnation_boon_yuna` SHALL declare `effects=["sexual_magic_mastery"]` (corrected from the
malformed three-segment `"element_mastery_rank:性魔法:主宰"`, which never parsed as a recognized
prefix). `sexual_magic_mastery` remains the sole mastery-domain declaration for this skill; the
`element_mastery_rank` prefix itself left the recognized prefix set with the retired cast gate.

#### Scenario: reincarnation_boon_yuna parses as SexualMasteryEffect
- **WHEN** `SKILL_REGISTRY["reincarnation_boon_yuna"].parsed_effects` is inspected
- **THEN** it contains exactly one `SexualMasteryEffect` instance and no `ElementMasteryEffect`
