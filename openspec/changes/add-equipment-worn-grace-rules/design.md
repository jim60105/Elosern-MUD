# Design: add-equipment-worn-grace-rules

## Context

Parent design §9. `world/rules/rulebook/schema.py` owns condition
evaluation: `evaluate_condition` supports the shipped vocabulary
(`buff_active`, `skill_owned`, `dual_wielding`, ordered-field `gte`/`lte`
on arousal/climax_phase/exposure; allowed-keys list at :61, validation at
:107). Condition facts arrive via context: `_build_context` (handler path),
`build_no_create_condition_context` (pure stored reads), and
`matched_combat_modifiers`' presentation partial-context `setdefault` of
`dual_wielding` (:238) so status displays cannot diverge from resolution.
`normalized_equipment` (P2 lazy-import pattern, malformed → empty) is the
canonical worn-set read. `dual_wielding_from_storage`
(`world/skills/equipment.py`) is the shipped purity precedent for an
equipment condition fact. Arousal comparisons use `AROUSAL_LEVELS`
(平靜／微興奮／中等／高度／極限). P4 already routes EFFECTIVE exposure into
the same contexts.

## Goals / Non-Goals

**Goals:**

- One new condition, `equipment_worn`, matching a single worn item key.
- Fail-closed loader validation against `ITEM_REGISTRY` (exists + slot).
- Four authored 恩典 rules with display labels, firing identically in
  preview, resist, and live resolution.

**Non-Goals:**

- Multi-key/any-of matching (single key AND-composes across rules — one
  rule per item keeps the display mapping 1:1), new items (P1), grace
  rules on non-Church gear, `pleasure_gain` rule-table consumption (P4's
  deferred reservation), payload changes (P6/P7).

## Decisions

### D1 — Fact injection mirrors `dual_wielding` exactly

`worn_item_keys_from_storage(entity)` lives in
`world/rules/equipment_effects.py` (pure stored read via the P2
function-local normalized-equipment import; malformed → empty frozenset;
writes nothing; imports no rules modules — the module edge
`combat_modifiers → equipment_effects` already exists from P2's merge and
stays acyclic). All three context sources gain the fact: both builders
set it; `matched_combat_modifiers` gains a `setdefault("worn_item_keys",
...)` beside the shipped `dual_wielding` default so presentation,
preview, and resolution share one fact. `evaluate_condition` grows one
branch: `equipment_worn` matches iff the string is in
`context["worn_item_keys"]`; a missing context key FAILS the condition
(fail-closed). The single-key shape (parent §9) keeps `status_display`
rule↔label 1:1 and AND-composition free.

### D2 — Vocabulary in the shared evaluator, referential validation per table

`schema.py` gains only the generic MECHANISM: the `equipment_worn` branch
(membership in `context["worn_item_keys"]`, missing fact → fail-closed) and
a `ValueError` for non-string values at evaluation time. Referential
validation is table-specific and runs at the combat rulebook's load site:
`combat_modifiers` wraps `load_rules` with a preflight that rejects, rule
by rule and BEFORE any matching or Script mirroring, any
`equipment_worn` whose value is not a string, not an `ITEM_REGISTRY`
member, or not slot-bearing. (Today the shipped `dual_wielding` bool check
is lazy-evaluated inside `evaluate_condition`; the grace preflight must
NOT repeat that mistake — a dead rule must never boot.) Because the shared
schema now accepts the vocabulary syntactically, every OTHER consumer of
`evaluate_condition` whose context lacks the fact must reject it at its own
load site: `sexual_transitions._load_rules` gains a guard rejecting
`equipment_worn` (a silently-never-matching transition rule is exactly the
failure mode the referential check exists to prevent). This keeps the
shared schema generic without leaking a live-looking no-op into sexual
rulebooks.

### D3 — Authored grace set is closed, doctrine-shaped, and stackable

The four rules named in the proposal ship as data; magnitudes sit inside
their item's rarity tier (rule-table defense values 2/4/6 below the
plate-armor flat 8; the emblem's heal_gain +10% rides P2's merged heal
funnel, consumed exactly like an equipment heal_gain). Arousal gates
(微興奮/中等/高度) encode the 敬拜弧線: modest devotion grants modest
protection, rapture grants the emblem's healing. The shipped slot model
allows FIVE concurrent accessories, so 圣女聖袍 + 光輝聖徽 + 朝聖者銅符 can
all match at once (+6/+2 defense and +10% heal_gain merging); this stacking
is declared intentional in the spec with a multi-slot merge test, so the
balance audit sees the real ceiling, not a per-rule view. No negative
Church values (mirrors P1's Church-set named-key invariant test, which this
change extends to the grace rules' adjustments).

### D4 — Arousal vocabulary stays canonical

Gates use `AROUSAL_LEVELS` strings only (parent design §9; the shipped `gte`
comparator). No new numeric thresholds.

## Risks / Trade-offs

- [Rules referencing items that a future rename removes] → D2's referential
  check converts every rename into a loud loader failure.
- [Presentation contexts constructed ad hoc elsewhere] → the `setdefault`
  in the shared matcher covers them all; a parity test asserts display and
  resolution bundles agree for a grace-wearing actor.
- [Grace stacking with P2's exposure rule + equipment defense could
  overweight Church kits] → bounded by authored values (max +6 defense +
  item flats inside rarity budgets); balance sheet in P1's design appendix
  remains the audit baseline.

## Open Questions

None.
