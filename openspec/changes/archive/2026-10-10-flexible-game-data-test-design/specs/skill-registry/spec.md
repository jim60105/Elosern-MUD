# Spec Delta

## MODIFIED Requirements

### Requirement: dual_wield_style is a PASSIVE stance, not a castable ACTIVE skill
`dual_wield_style` SHALL declare `kind=SkillKind.PASSIVE`, `target_spec=TargetSpec.NONE`, and an
empty `cost` (reclassified from the previous `SkillKind.ACTIVE` with `TargetSpec.SELF` and
`cost={"sp": 8}`).

#### Scenario: dual_wield_style is not castable via the normal ACTIVE-skill cast path
- **WHEN** a player who owns `dual_wield_style` as a passive skill attempts to cast it
- **THEN** the attempt is rejected with `SKILL_NOT_ACTIVE` at the resolver's ownership step (and
  `action_preview` reports the same `SKILL_NOT_ACTIVE` reason) ;  never `UNKNOWN_EFFECT_ID`

#### Scenario: Ownership still grants the rule-table adjustment
- **WHEN** an entity owns `dual_wield_style` as a passive skill and has two weapons equipped
- **THEN** `evaluate_combat_modifiers(entity)` returns the authored positive atk_phys adjustment through the same ownership rule

#### Scenario: The previous ACTIVE declaration had no working cast path
- **WHEN** the pre-reclassification declaration is examined
- **THEN** `weapon_style` is not registered in `action.py`'s `_EFFECT_HANDLERS`, so an in-combat cast
  attempt unconditionally rejected `UNKNOWN_EFFECT_ID` at effect resolution

#### Scenario: Out-of-combat cast attempts were rejected earlier
- **WHEN** the pre-reclassification skill was cast out of combat
- **THEN** the attempt was rejected earlier as `SKILL_NOT_USABLE_OUT_OF_COMBAT`

#### Scenario: The declared stance effect string is unchanged
- **WHEN** `dual_wield_style`'s `effects` are inspected after reclassification
- **THEN** they remain `["weapon_style:dual_wield"]` ;  the typed `WeaponStyleEffect` remains the
  declared stance representation

#### Scenario: The rule-table combat adjustment keeps its declaration path
- **WHEN** the `combat-modifier-table` capability's adjustment is resolved for an owner
- **THEN** `dual_wield_style_atk_phys_bonus` continues to resolve from ownership via the
  `skill_owned` + `dual_wielding` rule row

### Requirement: Reincarnation boon labels match the preset character names
The three per-character 轉生特典 passives SHALL declare labels that read 轉生祝福‧悠花
(`reincarnation_boon_yuka`), 轉生祝福‧悠奈 (`reincarnation_boon_yuna`), and 轉生祝福‧伊洛希雅
(`reincarnation_boon_elosia`) ;  each matching the `display_name` of the preset character whose kit
declares that boon in `PLAYER_PRESET_REGISTRY`. Their keys, costs, kinds, and target
specs SHALL NOT change, and each `effects` list keeps its shape.

#### Scenario: Every preset-carried boon label equals its owner's display name exactly
- **WHEN** the label of each `reincarnation_boon_*` skill declared by a preset's skill kit is
  compared against that preset's `display_name`
- **THEN** the label equals exactly `轉生祝福‧<display_name>` (轉生祝福‧悠花, 轉生祝福‧悠奈,
  轉生祝福‧伊洛希雅), and the skill's `kind`, `target_spec`, `cost`, and `effects` are
  byte-identical to the shipped registry values (all PASSIVE, `TargetSpec.NONE`, empty cost,
  a valid scoped wind practice-growth effect / `combat_prediction:武感` / `sexual_magic_mastery` respectively)

#### Scenario: The status display row follows the corrected name
- **WHEN** the `status_display.yaml` row keyed `reincarnation_boon_yuka_agility_bonus` is inspected
- **THEN** its label is 轉生祝福‧悠花敏捷提升

#### Scenario: The 伊洛希雅 boon effect string is re-keyed to the scoped growth rate
- **WHEN** the 伊洛希雅 boon's `effects` list is inspected
- **THEN** its effect string is a valid scoped `growth_rate:practice:<authored multiplier>:wind` ;  a scoped growth rate naming the wind
  tree, replacing the unscoped `growth_rate:practice:100`, whose three-segment form no longer parses;
  this is the only re-keying across the three boons' `effects` lists

### Requirement: Lightning spell progression composes executable turn-order behavior
The lightning spell family SHALL provide the documented 回合 progression as executable skill behavior using the common effect, audience, policy, buff, modifier, reaction and lineage mechanisms, with its two-root branching lineage's two 主宰 routes converging only at the two-parent 神格 canopy. Numeric magnitudes and durations SHALL be authored data validated at load and consumed at apply; tests SHALL NOT duplicate their literal values. Fixed synthetic fixtures SHALL independently prove the mechanisms.

#### Scenario: The extra-action grant provisions its second slot while live and one after lapse
- **WHEN** a synthetic self-only grant composition mounts the authored extra-action row and the round loop next provisions that combatant while the mount is live, and separately the mount is allowed to lapse before the next provisioning
- **THEN** the live-mount combatant receives exactly two action slots at its sequence position within the one round settlement, the lapsed combatant receives exactly one, and no other combatant's slot count changes at either provisioning

#### Scenario: The ward micro-rung marks melee attackers and the declared chance decides
- **WHEN** a synthetic ward carrier is struck by a landed physical attack from a living attacker, then by a magic attack, a missed swing and a sourceless write, and separately the marked attacker is gated by the authored declared-chance lock under fixed losing and winning dice
- **THEN** only the qualifying physical attacker carries the live retreat-marker instance attributed to the ward holder refreshed per qualifying strike, the magic/miss/sourceless paths apply nothing, the losing dice produce the skip event recording the authored chance and the consumed roll while the winning dice let the marked attacker act, and the marker itself mutates no initiative sequence

#### Scenario: The self advance and the canopy tail-push relocate only the still-to-act
- **WHEN** a synthetic self-advance composition mounts its authored advance row on a caster whose round slot has not arrived, and a synthetic canopy area composition strikes victims some of whom have already acted this round
- **THEN** the caster acts ahead of every combatant still to act that round, each struck not-yet-acted victim moves behind them, already-acted victims keep their completed turns, every other relative order is unchanged, and the following round re-rolls clean

#### Scenario: The paralysis ladder locks at the authored rungs on family keys
- **WHEN** a synthetic single-target composition applies the authored base 麻痺 row and another applies the authored enhanced rung, and the clock advances to each authored expiry
- **THEN** each holder's every action attempt resolves zero actions through the rule-table path for exactly its authored duration, the shipped marker-path inventory is unchanged throughout, and expiry restores action resolution

#### Scenario: The three-strike 多段 rung lands three judgments in one paid cast
- **WHEN** a synthetic 多段 composition with the authored count of two extra strikes and coefficient strikes one target under fixed rolls covering an all-hit sweep and a miss-interrupted sweep
- **THEN** exactly three independent rolls are recorded in order with the same authored coefficient per landing strike, resources and practice move once, and at most one terminal defeat or knockout emits regardless of which strikes cross a threshold

#### Scenario: The execution and devastation rungs price their clauses
- **WHEN** a synthetic 處決級 composition strikes a high-defense target, and a synthetic 毀滅級 area composition strikes a mixed battlefield
- **THEN** the execution strike skips defense subtraction entirely and each devastation victim takes the authored coefficient plus its authored maximum-HP share with allies untouched

#### Scenario: Branching and the two-parent capstone gate through the lineage engine
- **WHEN** a synthetic family replicates the documented two-root chains, the authored branch points and the two-parent canopy prerequisite shape
- **THEN** use rejects until every authored threshold is met, the canopy unlocks only when BOTH authored parents reach their authored thresholds, each route progresses independently, and prerequisite caps stay derived from the shared reverse-edge map with leaves at the shared tip cap

#### Scenario: Retired dev-era clauses resolve as ordinary rejections
- **WHEN** a caller casts a never-existing lightning key through the ordinary cast surface after replacement, or references the retired bounds-illusion payloads as effect bindings
- **THEN** each rejects with the existing unknown-skill or unknown-definition reason exactly like any never-existing key, and no alias, redirect or deprecated row exists that any cast or buff path could land on

#### Scenario: The documented turn-order rungs compose the family
- **WHEN** the lightning family's authored rungs are enumerated
- **THEN** they comprise an extra-action grant mounted as a detectable self-only buff and settled
  through the turn loop's action-count consumption at the authored duration; in-round order rewriting
  as declarative position markers only ;  a self advance mounted by its authoring node and tail
  retreats reaching the melee attackers of the two detection mounts through the shared
  outcome-reaction vocabulary and the struck victims of the 神格 canopy through the enemy-audience
  effect leg, each settled through the round loop's declarative fold at authored keys with
  already-acted combatants untouchable; the 麻痺 ladder locking every action through the shipped
  rule-table path at the authored-duration rungs on family-owned keys with the shipped
  marker-path inventory untouched; a declared-chance micro-rung whose one recorded per-round roll
  decides the skip; a 多段 rung resolving three independent strikes under the widened cap with the
  shipped once-paid and single-terminal-emission discipline; a 處決級 execution rung that ignores
  defense; and 毀滅級 devastation rungs
