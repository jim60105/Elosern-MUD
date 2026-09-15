## MODIFIED Requirements

### Requirement: combat_modifiers.yaml is one table evaluated by one condition engine, with no
special-case branch between buff-origin and sexual-origin rows
`world/rules/rulebook/combat_modifiers.yaml` SHALL contain both buff-presence rules (poison, paralysis,
fear) and sexual-field-threshold rules (arousal, climax phase), and `world/rules/combat_modifiers.py`
SHALL evaluate every rule in the table through the identical `evaluate_condition()` function from
`world/rules/rulebook/schema.py`. No function in `combat_modifiers.py` SHALL contain a conditional
branch that distinguishes a sexual-origin condition from a buff-origin condition. Action-locking
marker buffs added by the MP-depletion reaction wave (a suffocation marker, and the bind marker the
water wave binds through the table) SHALL join as ordinary `buff_active`-origin rows carrying the
existing `actions_per_turn: 0` bundle value — no new bundle key, no marker-specific consumer code —
and every new rule ID SHALL keep the one-unit-test correspondence the table already enforces.
The mana-transfer wave SHALL extend the merged bundle with exactly two further generic leaf values
following the existing heterogeneous-value posture: `{gauge}_regen_scale` (a per-gauge regen
multiplier consumed only by the world-clock regen stage) and `recovery_share_bonus` (an additive
drain-recovery share bonus consumed only by the mana-transfer caster-share read site). Both SHALL be
produced by ordinary `buff_active`-origin rows, SHALL be absent-by-default rather than defaulted in
table code, and SHALL NOT introduce a marker-specific consumer, an element name, or a skill key
anywhere in the table or its evaluation module.

#### Scenario: The seed table contains both condition origins
- **WHEN** `world/rules/rulebook/combat_modifiers.yaml` is loaded
- **THEN** it contains at least one rule whose `when` uses `buff_active` (e.g. `poison_agility_penalty`,
  `paralysis_locks_actions`, `fear_agility_and_accuracy_penalty`) and at least one rule whose `when`
  uses `field`/`gte`/`equals` against a sexual-state field (e.g.
  `high_arousal_agility_accuracy_penalty`, `climax_in_progress_locks_actions`)

#### Scenario: No source-level branching distinguishes rule origin
- **WHEN** `world/rules/combat_modifiers.py`'s source is inspected
- **THEN** it contains no conditional (e.g. `if rule.id.startswith(...)`, `if "arousal" in rule.when`)
  that special-cases a sexual-origin rule differently from a buff-origin rule when evaluating them

#### Scenario: A newly added lock-marker row locks through the shared mechanism
- **WHEN** a synthetic entity holds a marker buff whose only mechanical row is a new
  `buff_active`-conditioned `actions_per_turn: 0` rule
- **THEN** the merged bundle reports the zero exactly as `paralysis_locks_actions` does, the existing
  turn-skip and cast-gate consumers observe it with no code change, and expiry restores action

#### Scenario: New leaf values ride the same merge without defaulting
- **WHEN** `evaluate_combat_modifiers(entity)` runs for an entity holding only a regen-lock marker,
  only a share-bonus marker, and neither
- **THEN** each bundle contains exactly its one new leaf value from its row, the third bundle lacks
  both keys entirely (absent, not zero, for `regen_scale`), and every pre-existing leaf value is
  merged unchanged
