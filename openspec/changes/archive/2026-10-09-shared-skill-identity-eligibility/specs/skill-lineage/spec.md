# Spec Delta

## MODIFIED Requirements

### Requirement: can_use_skill is the single shared use-eligibility predicate
`world/rules/progression.py` SHALL define `can_use_skill(entity, skill) -> bool` as a pure,
side-effect-free query returning `False` unless `skill.key` is in `entity.skills.owned_keys()` and passes shared identity eligibility and applicable restrictions and,
for every declared `SkillPrerequisite`: the prereq key is in `owned_keys()` and
`skill_proficiency_level(entity, prereq.skill_key) >= prereq.min_proficiency`. It SHALL gate every
ACTIVE skill, spell and weapon skill alike.

#### Scenario: A mid-tree spell is gated by its own edge
- **WHEN** an entity owning `firestorm` with `firestorm` practice level 0 and `scorching_wave`
  practice level 2 calls `can_use_skill`
- **THEN** it returns `False` (the `scorching_wave >= 3` edge is unsatisfied)

#### Scenario: The exact threshold passes
- **WHEN** the same entity's `scorching_wave` level is exactly 3
- **THEN** it returns `True`

#### Scenario: The gate is school-agnostic
- **WHEN** an entity owns an ACTIVE weapon skill declaring a prerequisite its practice level does not meet
- **THEN** `can_use_skill` returns `False` on the identical code path used for spells

#### Scenario: A root skill with no prereqs is usable on ownership
- **WHEN** an identity-eligible entity owns `fire_arrow` (no prerequisites)
- **THEN** `can_use_skill` returns `True` regardless of proficiency

#### Scenario: Every consumer reads the single gate
- **WHEN** `ActionResolver` step-1/preflight/resolve, the shared action preview, submission
  revalidation, both skill menus, and `world/rules/combat.py`'s `default_attack_policy` need use
  eligibility
- **THEN** all consume `can_use_skill`, replacing the interim ownership+MP-only gate

#### Scenario: An unmet chain is rejected as an unknown skill
- **WHEN** the resolver's step-1 sees an owned skill whose prerequisite chain is unmet
- **THEN** it rejects with the SAME reason as an unowned skill (`UNKNOWN_SKILL`), its deterministic
  detail naming the first unmet edge in declared order

#### Scenario: No mastery-tier override returns
- **WHEN** 主宰-tier entry is evaluated
- **THEN** it is the prerequisite path (AND semantics over all declared edges); the deleted
  mastery-tier override SHALL NOT be reintroduced

#### Scenario: cost_tiers stays cosmetic
- **WHEN** a skill declares `cost_tiers`
- **THEN** it remains a display-only data label

## ADDED Requirements

### Requirement: Identity rejection is distinct from an unmet prerequisite
Use-eligibility failure SHALL distinguish identity rejection from an unmet prerequisite. An identity-ineligible root SHALL reject without assuming a prerequisite exists and without any dice or state change.

#### Scenario: Owned root cannot crash the gate
- **WHEN** an ineligible owner invokes a skill with no prerequisite edges
- **THEN** a named identity rejection is returned before costs, effects and practice; unmet-edge detail remains reserved for actual unmet edges

