## Context

`combat_modifiers.yaml` + `world/rules/combat_modifiers.py`'s `evaluate_combat_modifiers()` is a pure
query: build a context from live entity state, evaluate every rule's `when` via `evaluate_condition()`,
merge matching rules' adjustment bundles. It already mixes `buff_active` conditions (poison, fear) and
sexual-field-threshold conditions (`field`/`gte`/`equals`) with no branching between origins. Eight
registered skills' `passive_buff`/`combat_prediction` effects have no consumer at all today.

## Goals / Non-Goals

**Goals:**
- Give the eight currently-dead passive skills a real, working adjustment.
- Do it as data (YAML rows), not new Python branches, matching the existing table's own
  no-special-casing rule.

**Non-Goals:**
- Does not touch `stat_multiply` (explicitly excluded — see `skill-effects-typed-model`'s D2/D3
  discussion; that remains `SkillHandler.effective_value`'s territory).
- Does not implement `element_mastery_rank` (a separate cast-gate mechanism, not an adjustment bundle —
  see `element-mastery-cast-gate`).
- Does not decide final numeric balance beyond "small" bonuses consistent with each skill's flavor —
  exact numbers are a task-list detail, not an architectural decision, and can be tuned later without
  another proposal since they live in YAML.

## Decisions

- **`skill_owned` reads `entity.skills.owned_keys()` directly**, not a cached/derived set — this
  function is already cheap (list concatenation over stored data) and `evaluate_combat_modifiers()` is
  already documented as a pure, no-caching query; adding a second caching layer here would be
  premature.
- **One YAML row per skill, not one row with an `any_of` list**, so each skill's specific bonus is
  independently readable and independently testable, matching the granularity of the existing
  `poison_agility_penalty`/`fear_agility_and_accuracy_penalty` rows.
- **`reincarnation_boon_yuka`'s malformed nothing-special case**: its effect string
  (`combat_prediction:武感`) already matches the `combat_prediction` prefix correctly (unlike
  `reincarnation_boon_yuna`'s malformed three-segment string, fixed separately in
  `divine-mystery-skills`) — no string-format fix needed here, only a new consuming rule row.

## Risks / Trade-offs

- [Risk] A skill's flavor name doesn't map obviously to one numeric adjustment (e.g. what does
  "精準魔力控制" translate to mechanically?). → Mitigation: task list requires picking the closest
  existing adjustment field (`accuracy`, `defense`, spell-cost-adjacent field if one exists) per skill
  and documenting the mapping rationale in the YAML row's own inline comment, rather than inventing a
  new adjustment field per skill.

## Migration Plan

Purely additive YAML rows plus one new condition type — no removal, no data migration. Lands after
`skill-effects-typed-model`; before `weapon-style-stance-split` and `conferral-generalization`.

## Open Questions

None.
