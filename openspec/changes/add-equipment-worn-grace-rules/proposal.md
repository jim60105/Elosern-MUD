# Proposal: add-equipment-worn-grace-rules

## Why

The Church of Light worships through revealed, aroused devotion (以坦露為聖;
tmp/story_settings/world_info.md), and P1/P4 planted the pieces — named
Church gear with positive `exposure_bias`, effective-exposure rule matching —
but no rule yet REWARDS that devotion. This is P5 of the equipment-effects
design (parent §9): the `equipment_worn` condition vocabulary that lets the
combat-modifier rulebook read what an actor is wearing, plus the 恩典
(grace) rules that turn worn Church vestments and holy emblems into arousal-
gated blessings.

## What Changes

- New condition vocabulary member `equipment_worn: <item_key>` (single item
  key, AND-composed with existing conditions): the condition contexts
  (handler path, no-create path, AND partial contexts used by presentation)
  gain a `worn_item_keys` fact — the same pure stored-equipment read the
  shipped `dual_wielding` fact uses; rules match iff that key is currently
  worn.
- Referential validation runs at the COMBAT rulebook's own load-site
  preflight (before matching or startup mirroring): `equipment_worn` values
  must be strings naming an `ITEM_REGISTRY` item with an `equipment_slot`;
  unknown/slot-less keys fail loading. The shared evaluator only adds the
  generic mechanism (membership test, non-string → `ValueError`,
  missing-fact → fail-closed), and the sexual-transition loader rejects the
  vocabulary (its contexts lack the fact — a never-matching rule must not
  ship). Note: with the shipped 5-accessory slot budget, the Church grace
  rules are designed to STACK (declared intentional; merge-tested).
- Authored 恩典 rules (combat_modifiers.yaml data, each with its
  `status_display.yaml` label + severity so the shipped display-coverage
  test stays green):
  - `sister_vestment_grace`: 修女聖袍 + arousal ≥ 中等 → defense +4
    (the parent §9 example).
  - `saintess_vestment_grace`: 圣女聖袍 + arousal ≥ 中等 → defense +6.
  - `holy_emblem_grace`: 光輝聖徽 + arousal ≥ 高度 → heal_gain +10%
    (consumed by P2's heal funnel — rule-table soft percents were always
    in the adjustments vocabulary).
  - `pilgrim_medallion_grace`: 朝聖者銅符 + arousal ≥ 微興奮 → defense +2.
- Preview, resist scoring, overwhelm estimation, and live resolution pick
  the grace facts up for free through the shared context — no second
  formula; a mismatch test locks presentation-parity.

No backward compatibility or migration work.

## Capabilities

### New Capabilities

(None.)

### Modified Capabilities

- `combat-modifier-table`: ADDED requirement — `worn_item_keys` context
  fact in all three context sources, `equipment_worn` AND-composition,
  grace-rule firing parity between preview and resolution, declared
  multi-slot stacking, display coverage for every grace rule.
- `rulebook-schema`: ADDED requirement — generic `equipment_worn`
  mechanism plus combat-side referential preflight before any matching or
  mirroring.
- `sexual-transition-rulebook`: ADDED requirement — transition loader
  rejects the unbacked vocabulary at load.

## Impact

- `world/rules/rulebook/schema.py`: generic condition branch + `ValueError`
  on non-string values.
- `world/rules/combat_modifiers.py`: load-site grace preflight (referential
  validation), both context builders + the presentation partial-context
  `setdefault` gain the fact.
- `world/rules/sexual_transitions.py`: loader guard rejecting
  `equipment_worn`.
- `world/rules/rulebook/combat_modifiers.yaml`: four authored grace rules;
  `world/rules/rulebook/status_display.yaml`: four label+severity entries.
- Tests: condition unit tests (match/no-match/missing-fact/non-string
  raise), combat preflight + transition-loader rejection tests, grace-rule
  behavior via fixed-seed resolution + no-create parity, declared multi-
  accessory merge test, helper purity assertion (no handler materialization
  or writes), display-coverage test green, existing modifier suites green.
- Not affected: equipment rulebook (P1), stored traits, command surface
  (docs untouched, `tests/test_command_docs.py` green), payloads (P6/P7).
