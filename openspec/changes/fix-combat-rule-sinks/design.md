## Context

`world/rules/rulebook/combat_modifiers.yaml` declares 14 adjustment rows evaluated by
`world/rules/combat_modifiers.py` (one condition engine, no origin branching). Of the bundle keys,
`agility` (percentage) and `accuracy` (flat) are consumed in to-hit math
(`world/rules/combat.py:173-190`), and `actions_per_turn: 0` locks actions
(`action_preview.py:102`, `combat.py:569-572`). Four keys have no deterministic sink:

- `defense` (flat): `defense_instinct_defense_bonus`, `guardian_instinct_defense_bonus`
  (yaml:19-24, 56-61) — damage resolution reads `target.skills.effective_value("defense")`
  verbatim (`combat.py:274-275`).
- `atk_phys` (flat): `retainer_martial_training_atk_phys_bonus`, `dual_wield_style_atk_phys_bonus`
  (yaml:50-55, 68-74) — `combat.py:274` reads `actor.skills.effective_value(attack_key)` verbatim.
- `mp_cost` / `sp_cost` (percentage): `precise_mana_control_mp_cost_reduction`,
  `extreme_endurance_sp_cost_reduction` (yaml:43-49, 31-36) — the resource check
  (`action.py:245-251`) and deduction (`action.py:579-599`) use `skill.cost` verbatim, and
  `action_preview.py:96-98` mirrors the verbatim check.

The `combat-modifier-table` main spec (lines 107-117) explicitly labels these four keys
"documented bundle/status vocabulary whose consumption by the deterministic combat/resource math is
owned by later changes" — this change is that later change. `world/rules/` is the sole writer of
game state; all new consumers read via the pure `evaluate_combat_modifiers()` /
`evaluate_combat_modifiers_no_create()` queries and never mutate.

## Goals / Non-Goals

**Goals:**
- Wire `defense`/`atk_phys` flat values into the deterministic damage magnitude and keep every
  damage-estimation surface (overwhelm estimator, monster skill-choice metric) consistent with the
  live formula.
- Wire `mp_cost`/`sp_cost` percentage values into BOTH the resource check and the deduction, with
  one shared rounding/clamping rule, and keep the no-create preview check identical.
- Preserve the single-writer boundary: all adjustments stay read-only queries over the bundle.
- Keep determinism and integer discipline: adjusted costs are integers, no floats in stored state.

**Non-Goals:**
- No new adjustment fields, no new rules, no numeric balance recalibration (seed magnitudes stay
  flavor-consistent "small" values; balance tuning is a later data-only task).
- `effective_power` (`combat.py:193-199`, used by overwhelm power ratio and monster target
  ranking) keeps reading raw effective stats — it is a relative ranking heuristic, not a damage
  prediction (see D-3).
- `accuracy`/`agility`/`actions_per_turn` sinks are untouched (already live).
- No changes to `status_query.py` or `status_display.yaml` — the status panel presents the bundle
  verbatim and stays byte-identical.

## Decisions

- **D-1. Flat `atk_phys`/`defense` adjustments enter the formula at the stat read point.**
  In `_handle_damage` (`combat.py:274-275`), the attack and defense terms become
  `round((effective_attack + atk_bonus) * multiplier) - (effective_defense + def_bonus)` via two
  new pure helpers in `combat.py`: one adjusted-attack helper (applies `atk_phys` only when the
  school is physical, i.e. `attack_key == "atk_phys"`) and one adjusted-defense helper (applies to
  both schools, since defense currently mitigates all damage). The `atk_phys` bonus is therefore
  amplified by crit/solid-hit multipliers while `defense` stays flat — mirroring the stats'
  existing roles in the formula (attack is multiplicative, defense is flat-subtracted). Alternative
  rejected: adding the bonus post-rounding (constant flat damage) — `atk_phys` is literally the
  physical attack stat, so it must enter where the stat enters, exactly as the flat `accuracy`
  bonus enters the to-hit score (`combat.py:184`).

- **D-2. One shared cost-adjustment helper: floor rounding, zero clamp, resource-generic keys.**
  `combat_modifiers.py` gains `apply_cost_modifier(amount, percentage) -> int`:
  `None` → `amount` unchanged; otherwise parse the signed (possibly fractional) percentage with the
  module's existing `_PERCENT_RE` and return `max(0, floor(amount * (1 + pct/100)))`. Bundle key
  mapping is `f"{resource_key}_cost"` (`mp` → `mp_cost`, `sp` → `sp_cost`); an unmapped resource key
  is unchanged, so a future `hp_cost` vocabulary applies automatically without code changes. Floor
  (truncate toward zero on the positive product) is player-favorable for the only current rules
  (reductions) and matches the existing percentage-application style (`_apply_percent_mod`
  multiplies, callers then round/truncate). Clamp at zero means a 100%+ reduction casts for free;
  cost never goes negative. Floats appear only transiently inside the computation.

- **D-3. Both resolver steps and the preview share the same adjusted-cost computation.**
  `action.py` gains a private `_adjusted_costs(actor, skill) -> dict[str, int]` built from
  `evaluate_combat_modifiers(actor)` plus `apply_cost_modifier`; `_step2_resource_check`
  (`action.py:245-251`) and `_step6_resource_deduction` (`action.py:579-599`) both consume it, so
  the check, the commit-time recheck, and the staged `resource_spend|...|{adjusted}` description
  (and therefore the event-log `amount` and `trait_delta`) can never drift. The staged description
  carries the adjusted amount so logs report the real deduction. `action_preview.py:96-98`
  `_skill_wide_failure` computes the same adjusted costs from the no-create bundle it already
  evaluates for the `actions_per_turn` check (line 102) — one evaluation, both checks. Parity is
  guaranteed because both evaluation paths are pure reads of the same stored state (the main spec
  already requires no-create identity for `skill_owned` rows), and steps 2 and 6 run before any
  commit, so state cannot change between them. Alternative rejected: passing precomputed costs
  through the pipeline — the preview is a separate module and the two resolver steps already
  re-read state independently; a shared helper is the single point of truth.

- **D-4. Damage-estimation surfaces consume the shared adjusted-stat helpers.**
  `overwhelm.py:159-175` `_expected_damage_per_attack` switches its raw `effective_value` reads to
  the new combat helpers (`combat._adjusted_attack(attacker, "atk_phys")`,
  `combat._adjusted_defense(defender)`) so overwhelm classification cannot diverge from live damage.
  `monster_behaviour.py:275-285` `_choose_skill.expected_damage` applies the same adjustment:
  without it the metric understates physical candidates relative to magic ones (the `atk_phys`
  bonus is constant per candidate only when every candidate shares the same school — it does not),
  so ordering could flip. `effective_power` is deliberately NOT changed: it ranks entities by raw
  stats for the overwhelm power ratio and monster target selection; it is a heuristic, the flat
  bonuses are small relative to stat sums, and changing it would alter monster targeting and
  verdicts beyond damage consistency. This scoping is documented and tested only via behavior
  (existing tests keep passing; new tests target the damage/estimation surfaces).
  `default_attack_policy`'s monster eligibility check (`combat.py:513-517`) also keeps the
  verbatim `skill.cost` comparison: it is a conservative action-selection heuristic — if it ever
  over-skips a skill, the fallback path (and the resolver's authoritative adjusted check) still
  resolves correctly, and monsters never own the cost-reduction skills today (they are player
  passive skills; conferred grants target companions).

- **D-5. Comment-only YAML updates; no magnitude recalibration.**
  The seed magnitudes (flat ±5, -10%) remain: they were chosen as small flavor-consistent
  adjustments and remain small when live (a +5 `atk_phys` is ≤ 10 extra damage on a crit; -10%
  cost floors the deduction by at most 10% of the base). Inline comments in
  `combat_modifiers.yaml` get updated where they claim a field is "the closest existing adjustment
  field" / "shared cost vocabulary" — they now state the field is consumed by live damage or
  resource math (e.g. the `defense` rows' comments note the bonus enters damage mitigation).

## Risks / Trade-offs

- [Risk] Damage math now evaluates the bundle up to ~4× per target (to-hit attacker/defender plus
  adjusted-attack/defense), multiplying pure-query calls. → Mitigation: all evaluations are
  in-memory reads over already-loaded state; the codebase already evaluates per target in
  `_to_hit`; no caching layer is added (matches the pure-query spec).
- [Risk] Magic-school damage against a `defense`-bonus owner changes (defense now mitigates it
  harder) — a real behavior change beyond physical math. → Mitigation: it is the direct
  consequence of defense's existing dual-school role in the formula (D-1); covered by an explicit
  test and documented in the delta spec scenario.
- [Risk] Existing tests with implicit reliance on the inert keys (e.g. an entity owning these
  skills inside a combat test) would change expectations. → Mitigation: greps today show no combat
  test owns these skills, but the apply phase re-runs the full `world.rules` suite plus the
  repository-wide contracts and fixes any such test in the same change.
- [Risk] A malformed percentage string in the rule table would make `apply_cost_modifier` raise
  `ValueError` inside `_step2_resource_check`, which only `RejectedAction` is caught around in
  `resolve()`/`preflight()`, breaking the always-return-`ActionResult` contract. → Mitigation:
  fail loud is deliberate and matches the existing `_apply_percent_mod` precedent (`combat.py:149-
  156`); the rule-table correspondence test plus the new per-rule tests exercise every seed row's
  percentage, so a data error surfaces in CI at merge time, not silently in play.
- [Risk] Floor rounding + zero clamp could make a -10% rule reduce a 1-cost skill to 0 (free). →
  Mitigation: deliberate, spec'd semantics ("never negative cost; cast for free at zero"); the
  current seed rules are -10% and the zero clamp only bites at costs ≤ 4 with compounding rules,
  none of which exist today.

## Migration Plan

Purely additive wiring: new pure helpers, two call-site changes in `action.py`, one in
`action_preview.py`, formula changes in `combat.py`, and consumer swaps in `overwhelm.py` /
`monster_behaviour.py`; YAML changes are comments only. No data migration, no backward
compatibility (unreleased project, zero users). Rolls back by reverting the call sites — no state
format change.

## Open Questions

None.
