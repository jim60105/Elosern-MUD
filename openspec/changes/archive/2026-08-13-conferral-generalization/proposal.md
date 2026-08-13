## Why

`ConferredSkillGrant` today only supports `stat_multiply` conferral (`trait_keys` + `scale`), matching
統御術's one currently-tested use case. Per the approved design doc §5/D6, 統御術's own description
("授予目標一部分自身技能的效果") implies any continuous-valued effect should be conferrable at a
fractional scale, not just `stat_multiply` — and `skill-owned-rule-condition` is about to add a second
continuous-valued effect family (rule-table adjustments) that conferral should also reach, so this
generalization is done once both mechanisms exist rather than twice.

## What Changes

- `ConferredSkillGrant` simplifies from `{source_key, skill_key, trait_keys, scale}` to
  `{source_key, skill_key, scale}` — `trait_keys` is dropped as redundant, since it is now derivable
  from the referenced skill's own `parsed_effects`.
- `SkillHandler.effective_value` (unchanged multiplier math) and the `skill_owned` rule-table context
  builder (from `skill-owned-rule-condition`) each independently check
  `entity.skills.conferred_grants()` for a grant referencing a skill whose parsed effect they resolve,
  and fold in `resolved_value * grant.scale`.
- Conferral explicitly excludes gate-type effects (`ElementMasteryEffect`, `SexualMasteryEffect`,
  `set_disguise`) — attempting to confer one raises `EFFECT_RESOLUTION_FAILED` at cast-resolution time,
  since "partial spell unlock" or "partial disguise" has no defined meaning. The same rejection applies
  to a skill carrying no continuous-valued effect any grant consumer can resolve (no
  `StatMultiplyEffect`, no `RuleTableEffect`), so a grant can never be recorded as a silent no-op.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `skill-handler`: `ConferredSkillGrant`'s shape changes (`trait_keys` dropped); the conferral
  mechanism generalizes beyond `stat_multiply` to any continuous-valued effect; an explicit exclusion
  list for gate-type effects is added.

## Impact

- `world/skills/handler.py` (`ConferredSkillGrant` dataclass, `effective_value`),
  `world/rules/action.py` (`_handle_confer_skill_partial`'s event-context contract — `confer_trait_keys`
  becomes unnecessary and can be dropped from `requires_event_context`),
  `world/rules/combat_modifiers.py` (new conferral-aware lookup in the `skill_owned` context builder).
- Depends on `skill-effects-typed-model` (typed effects, needed to derive a skill's continuous-valued
  quantity generically) and `skill-owned-rule-condition` (the second consumer this generalizes into).
- Does **not** depend on `element-mastery-cast-gate` — the exclusion of gate-type effects is expressed
  structurally (by effect class), not by testing against a specific mastery skill instance.
