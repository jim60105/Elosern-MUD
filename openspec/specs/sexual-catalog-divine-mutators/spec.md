# sexual-catalog-divine-mutators Specification

## Purpose

Register the four `C7b` 神之秘法 acts — 感度創世, 恥辱剝奪, 絕對從屬, 無垢回歸 — completing the divine
line that `sexual-catalog-divine-core` started with three. Each act is hand-built (not via
`_act_family()`), declares `requires_divine_arts=True` (so the shipped race gate is the line's
containment), an empty `unlock` mapping, `target_part=None` (神之秘法 is a parless line),
`resistible=True`, and no counters. Each introduces one new general-purpose `action.py` effect
prefix (`divine_saturate_sensitivity:`, `divine_clamp_shame:`, `divine_mark_submission:`,
`divine_restore_purity:`) and one new `SexualState` mutator
(`saturate_sensitivity`, `clamp_shame_to`, `mark_submission`, `restore_purity`); 絕對從屬
additionally wires a `submission_marks` short-circuit term into `resist_verdict()`.

## Requirements

### Requirement: Four hand-built acts extend DIVINE_ACTS, gated exclusively by requires_divine_arts, with no counter unlock
`world/skills/sexual_acts/divine.py`'s `DIVINE_ACTS` tuple SHALL contain, in addition to
`sexual-catalog-divine-core`'s three entries, exactly four more `(SkillDef, SexualActDef)` pairs —
`感度創世`, `恥辱剝奪`, `絕對從屬`, `無垢回歸` — each declaring `requires_divine_arts=True`,
`unlock={}`, `TargetSpec.SINGLE`, `target_part=None`, `resistible=True`, `actor_counters=()`,
`participant_counters=()`. None SHALL be constructed via `_act_family()`, and none SHALL modify or
remove any of `sexual-catalog-divine-core`'s three existing entries.

#### Scenario: A non-divine race cannot cast any of the four acts regardless of counters
- **WHEN** an actor whose race's `can_use_divine_arts` is `False` attempts to cast any of the four
  acts, regardless of that actor's lifetime counter values
- **THEN** `_step1_divine_arts_gate` rejects the cast with `RejectReason.DIVINE_ARTS_FORBIDDEN`

#### Scenario: DIVINE_ACTS grows to seven entries without altering the first three
- **WHEN** `world.skills.sexual_acts.divine.DIVINE_ACTS` is inspected after this change
- **THEN** it contains seven entries, and the three keys `sexual-catalog-divine-core` registered
  resolve to `SkillDef`/`SexualActDef` pairs identical to before this change

### Requirement: 感度創世 saturates the target's sensitivity, excluding the actor and tolerating a resisted cast
`感度創世` SHALL declare one effect, `divine_saturate_sensitivity:感度創世`. Its handler SHALL, for the
resolved target excluding the actor, call `target.sexual.saturate_sensitivity()`. An empty `targets`
list (a resisted sole target) SHALL be handled as a no-op, never a rejection.

#### Scenario: Casting 感度創世 saturates the target's named body parts
- **WHEN** `感度創世` is cast at a target
- **THEN** every `BODY_PARTS` member of that target's sensitivity reads `"敏感異常"` afterward

#### Scenario: A resisted cast is a no-op, not a rejection
- **WHEN** `感度創世` is cast at a target whose resist contest resolves `resisted=True`
- **THEN** the cast succeeds (the resist verdict is logged), the target's sensitivity is unchanged,
  and no `RejectedAction` is raised

### Requirement: 恥辱剝奪 pins the target's shame at 成癮, eagerly rejecting a Monster target before staging any mutation
`恥辱剝奪` SHALL declare one effect, `divine_clamp_shame:恥辱剝奪`. Its handler SHALL check
`isinstance(target, Monster)` for the resolved target (excluding the actor) *before* staging any
`PendingEffect`, and SHALL raise `RejectedAction(RejectReason.EFFECT_RESOLUTION_FAILED, ...)` directly
if so, rather than staging a mutation that raises `ValueError` from inside its own `apply()` closure
(which would surface as `RejectReason.COMMIT_FAILED` instead). For a non-`Monster` target, it SHALL
stage `target.sexual.clamp_shame_to("成癮")`. An empty `targets` list SHALL be a no-op.

#### Scenario: Casting 恥辱剝奪 pins a non-Monster target's shame permanently
- **WHEN** `恥辱剝奪` is cast at a non-`Monster` target
- **THEN** that target's `shame.level` reads `"成癮"` afterward and does not move on a subsequent
  `decay_tick`

#### Scenario: Casting 恥辱剝奪 at a Monster target is rejected with EFFECT_RESOLUTION_FAILED, before any mutation is staged
- **WHEN** `恥辱剝奪` is cast at a `Monster` target
- **THEN** the action is rejected via `RejectedAction(RejectReason.EFFECT_RESOLUTION_FAILED, ...)`
  (never `RejectReason.COMMIT_FAILED`), and that target's `shame` remains pinned at `"無"`

### Requirement: 絕對從屬 marks the target as permanently auto-complying toward the caster, keyed by a guaranteed-unique identity
`絕對從屬` SHALL declare one effect, `divine_mark_submission:絕對從屬`. Its handler SHALL, for the
resolved target excluding the actor, call `target.sexual.mark_submission(str(actor.id))` — the actor's
database id, never `_entity_key(actor)`/`.key`, since `.key` is not guaranteed unique across entities
(same-species `Monster` spawns share an identical `.key`) and this mark has no removal path. An empty
`targets` list SHALL be a no-op.

#### Scenario: Casting 絕對從屬 makes every future contest against that caster auto-comply
- **WHEN** `絕對從屬` is cast by actor A at target B, and any later `resist_verdict(A, B)` call is made
- **THEN** that later call returns `resisted=False, auto_comply=True, roll=None`

#### Scenario: The mark does not affect contests against a different actor
- **WHEN** `絕對從屬` is cast by actor A at target B, and a later `resist_verdict(C, B)` call is made
  for some other actor C
- **THEN** that call resolves through the ordinary contest (or another applicable short circuit),
  unaffected by A's mark

#### Scenario: Two distinct entities sharing an identical .key are not confused by the mark
- **WHEN** `絕對從屬` is cast by actor A at target B, and a second, distinct entity D shares the exact
  same `.key` string as A (e.g. two `Monster` instances of the same species), and a later
  `resist_verdict(D, B)` call is made
- **THEN** that call does **not** auto-comply via the submission mark — the mark was stored keyed by
  `str(A.id)`, not `A.key`, so D's distinct `id` does not match it

### Requirement: 無垢回歸 restores the target's virgin flag without touching experience_types
`無垢回歸` SHALL declare one effect, `divine_restore_purity:無垢回歸`. Its handler SHALL, for the
resolved target excluding the actor, call `target.sexual.restore_purity()`. An empty `targets` list
SHALL be a no-op.

#### Scenario: Casting 無垢回歸 reverses a target's False virgin flag
- **WHEN** `無垢回歸` is cast at a target whose `virgin` is `False`
- **THEN** that target's `virgin` reads `True` afterward, and its `experience_types` is unchanged

### Requirement: The four new effect prefixes are line-agnostic dispatch-table entries
`action.py`'s `_EFFECT_HANDLERS` SHALL register `divine_saturate_sensitivity:`, `divine_clamp_shame:`,
`divine_mark_submission:`, and `divine_restore_purity:` as ordinary prefixes. No handler SHALL read
`SkillDef.requires_divine_arts` or otherwise branch on the calling `SkillDef`'s line.

#### Scenario: A hypothetical non-divine SkillDef naming one of the four prefixes is handled identically
- **WHEN** a hypothetical `SkillDef` outside the 神之秘法 line declares
  `effects=["divine_mark_submission:test"]` and is cast
- **THEN** the handler calls `mark_submission` on its resolved target exactly as it would for
  `絕對從屬`, without rejecting the cast for lacking `requires_divine_arts`
