## Why

`SkillDef.effects` stores raw `"prefix:arg1:arg2"` strings that each consumer re-parses ad hoc.
Six of the seven prefixes the registry declares (`movement`, `weapon_style`, `element_mastery_rank`,
`passive_buff`, `passive_trait`, `combat_prediction`) have no consumer anywhere in the codebase, so 18
of the ~28 non-innate skills in `SKILL_REGISTRY` are silently inert — owning or casting them does
nothing. This was confirmed by the run-2 game-logic audit and traced to the same root cause: an
unrecognized effect prefix fails silently (cast rejects `UNKNOWN_EFFECT_ID`, or ownership is just never
read) instead of failing loudly. This change is the foundation every other skill-system-redesign
proposal builds on (see `docs/superpowers/specs/2026-08-12-skill-system-redesign-design.md` §3.1, D1,
D3).

## What Changes

- Add `world/skills/effects.py` defining one frozen dataclass per effect prefix (`StatMultiplyEffect`,
  `GrowthRateEffect` (the read-time `growth_rate` prefix `reincarnation_boon_elosia` already declares
  and `world/rules/progression.py` consumes), `ElementMasteryEffect`, `SexualMasteryEffect`,
  `RuleTableEffect`, `FlavorEffect`, `MovementEffect`, `WeaponStyleEffect`, `ConferralEffect`,
  `DivineMysteryEffect`, plus thin wrappers for the already-working
  `confer_skill_partial`/`set_disguise` (named `DisguiseEffect` explicitly, since
  `conferral-generalization` references it by that name)/`buff_apply`/`self_buff_apply`/
  `confer_growth_rate`/`sexual_event`/`damage`/`disengage` prefixes) and a single dispatch function
  `parse_effect(effect_id: str)`.
- `SkillDef.__post_init__` parses every string in `effects` through `parse_effect`; an unrecognized
  prefix raises `ValueError` **at registry-load time** (server import), not at first use.
- **BREAKING** (internal only, zero users): `SkillDef` gains a derived `parsed_effects: tuple` field.
  Existing ad hoc `effect_id.split(":")` parsing in `world/skills/handler.py` is replaced with reads of
  `parsed_effects`, behavior-preserving for the one prefix (`stat_multiply`) it already handled.
- `body_enhancement` / `body_enhancement_extreme` / `body_enhancement_basic` reclassify from `ACTIVE`
  to `PASSIVE` (D3 of the design doc) — there is no working cast path for them today and none is being
  built; ownership alone already applies the multiplier via `effective_value`.
- `reincarnation_boon_yuna`'s malformed three-segment effect string (`"element_mastery_rank:性魔法:主宰"`,
  inconsistent with every other mastery skill's two-segment form) is corrected to
  `["sexual_magic_mastery"]` — moved here from `divine-mystery-skills` (found during rubber-duck review:
  this change's own registry-load validation would otherwise fail to import at the moment it lands,
  since the malformed string doesn't parse under any recognized prefix and no other change in this
  batch declares itself a prerequisite of this one). `divine-mystery-skills` still owns
  `sexual_magic_mastery`'s new castable-skill behavior.
- Add the MP cost-tier constants table (design doc §4.3) as `world/skills/cost_tiers.py`, consumed by
  later spell-catalog proposals — declared here since every one of them needs it and it has no other
  natural owner.
- Remove the stale `world/skills/registry.py` module-docstring claim that `stat_multiply` is "the only
  effect-ID convention interpreted by this package."

## Capabilities

### New Capabilities
- `skill-effect-model`: the typed effect-parsing module, its dispatch contract, and the
  registry-load-time validation guarantee (unrecognized prefix raises at import, not at use).

### Modified Capabilities
- `skill-registry`: `SkillDef.__post_init__` now rejects unknown effect prefixes at construction
  (previously accepted any string unconditionally); `body_enhancement` family's `kind` changes from
  `ACTIVE` to `PASSIVE`.

## Impact

- `world/skills/registry.py`, `world/skills/handler.py` (parsing only — `effective_value`'s multiplier
  math is unchanged), new `world/skills/effects.py`, new `world/skills/cost_tiers.py`.
- No dependents yet exist in `action.py`'s cast handlers or `combat_modifiers.py` — those are updated
  by later proposals (`heal-effect-handler`, `skill-owned-rule-condition`, `weapon-style-stance-split`,
  `element-mastery-cast-gate`, `conferral-generalization`, `divine-mystery-skills`,
  `movement-skill-waiver`, `skill-content-completion`, and the eight `spell-catalog-*` changes), all of
  which depend on this change landing first.
