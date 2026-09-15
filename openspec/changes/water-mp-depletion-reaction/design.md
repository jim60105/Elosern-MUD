## Context

Implements the MP-depletion machinery clause of `docs/lore/skill-trees/water.md` (潮退 DoT ladder + 溺潮's suffocation) against the shared water-wave contract in `../water-spell-catalog/design.md`. Engine: Evennia 6.1 / Python 3.13, immutable authored data plus deterministic transactional rules. MP is a `GAUGE_KEYS` gauge (`world/rules/traits.py`: `("hp","mp","sp")`); buff `rate` targets already validate `mp`, but `_apply_rate_modifier` only dispatches an outcome on the `target == "hp" and delta < 0` branch, and `_step6_resource_deduction`'s `_deduct_resource` writes the trait directly. The reaction engine (`world/rules/state_reactions.py`) has a closed `_RECOGNIZED_WHEN_KEYS` set and a shared `evaluate_condition` with an open `event:` value slot; `dispatch_outcome_reaction` currently carries only `source_tier` attribution.

## Goals / Non-Goals

**Goals:** Make "MP reached zero via a decrease" one globally-visible engine fact with source + tier attribution; make every existing MP-decrease path route through the one writer; deliver the suffocation payoff through the existing rule tables; ship the three 潮退 DoT rows so the wave's later changes ride a live vocabulary.

**Non-Goals:** No mana-transfer effect family (change 2), no damage-to-MP shield (change 3), no catalog rows (change 5), no water-key branches in generic code, no second rules engine, no suffocation logic in the reaction engine itself (it is a rule row), no main-spec sync, no data-contract tests of any kind (given: all water verification is synthetic behavior).

## Decisions

### D1 — One canonical writer, dispatched-once semantics
New dependency-light module `world/rules/mp_flow.py` owning `apply_mp_change(entity, delta, *, source_skill=None, source_tier=None) -> int` and `remove_mp(entity, *, source_skill, source_tier) -> int` (the drain-all entry change 2 will reuse). It reads stored MP with the module's existing no-create read convention, clamps exactly as the trait already clamps, and when the stored value crosses from positive to zero **on a negative delta** dispatches `dispatch_outcome_reaction(entity, "mp_zero", source_tier=..., source_skill=...)` once per actual crossing. Zero-loss changes (already at zero, clamped no-op), increases, and heals never dispatch. `dispatch_outcome_reaction` gains an optional `source_skill` parameter (default `None`) into its condition context; existing callers are untouched. `mp_zero` is matched by the existing `event: mp_zero` rule shape — the event-name slot is open vocabulary, so no `when` key is added for event matching.

### D2 — Every decrease routes through the writer
`_apply_rate_modifier` calls the writer for `target == "mp"` ticks (both signs — a positive mp rate is a legal authored profile and must not bypass the writer; it simply never dispatches); the hp branch keeps its existing `hp_loss` dispatch untouched. `_step6_resource_deduction`'s staged apply closure routes the `mp` resource through the writer with the cast skill as source (cost payment CAN zero the caster's own MP — the global-fact given makes this correct, and the suffocation rule's source-skill qualification decides whether it ever punishes; today's row is qualified to the drowning skill only). SP/HP deductions keep the existing `_deduct_resource` path. A codegraph/LSP enumeration of every `traits.mp` writer at implementation time is part of the contract: any other MP-decrease writer found (items, future transfer effects) is routed here, never beside it.

### D3 — Rule-layer source filtering via a closed when key
Add exactly one `when` key `event_source_skill` (exact skill-key match against the event's `source_skill`; absent event source never matches) to `_RECOGNIZED_WHEN_KEYS` and `evaluate_condition`. Validation (`validate_state_reaction_rules`) fails closed when `event_source_skill` appears on a rule with no `event`. This is the water wave's realization of "suffocation filters source at the rule layer, never by not-dispatching": the event always fires; only the drowning node qualifies for suffocation. Alternate synthetic rules prove a second element could qualify a different source with the same key.

### D4 — Ship the water rulebook rows here (no-silent-window given)
`buffs.yaml` gains three 潮退 rows — the lore names the DoT 潮退 once but index §3.3 tiers it, and reaction rules can only qualify by source skill, so the ladder ships as tier-keyed definitions: `ebbing` (rate `{target: mp, delta: -5}`, tick 10, duration 60, debuff), `ebbing_deep` (−12), `ebbing_maelstrom` (−18). `unique_per_source` stacking is NOT used (one source key per cast would refresh across tiers wrongly); the DoT uses the same refresh semantics as `poisoned`/`dark_corrosion`, and 深淵巨口's per-stack restore bonus (change 2) reads the active 潮退 definition keys it owns. `suffocated`: duration 40, debuff, empty modifiers, plus `combat_modifiers.yaml` row `suffocation_locks_actions: {when: {buff_active: suffocated}, then: {actions_per_turn: 0}}` — the same lock mechanism `paralysis` and `climax_in_progress_locks_actions` already use, so both the combat turn-skip and the cast-time `ACTION_FORBIDDEN` gate work with zero new code. `state_reactions.yaml` gains `drowning_suffocation`: `when: {event: mp_zero, event_source_skill: <ebbing_maelstrom's owning node key — the catalog binds the drowned_surging node here via the authored qualification; during this change the row is validated against the synthetic test fixture's authored shape and ships qualified to the future key only once the catalog change registers it — see D5}`, `then: {apply_buff: suffocated}`. `status_display.yaml` gains fail-closed display rows for every new buff key (`潮退`, `潮退·深`, `潮退·漩`, `窒息`).

The old dev-era `water_shield` bounds row stays untouched here — change 3 replaces it. `water_bind` stays (deep-sea bind continues to use it); change 5 re-homes it.

### D5 — Suffocation rule authoring timing
Because `validate_state_reaction_rules` fails closed on unknown `then` buffs but `event_source_skill` values are validated against `SKILL_REGISTRY` only lazily at evaluation (same closed-on-missing posture as `skill_qualified`), the `drowning_suffocation` row MAY ship in this change keyed to `drowned_surging` even though that registry node arrives with change 5: the row is inert-but-valid until the node exists, and the batch order guarantees the catalog change lands last in the same wave before anything is considered live. The synthetic behavior tests use a synthetic source key, never the real node.

### D7 — Interface ownership opened by this change
| Interface | First owner | Consumers |
|---|---|---|
| `apply_mp_change` / `remove_mp` canonical writer | this change | change 2 (drain/restore sides of every transfer), change 3 (MP divert pays through it), catalog data |
| `mp_zero` event + `event_source_skill` when key | this change | any future element's depletion rule; no water keys in generic code |
| 潮退 tier-keyed DoT rows + active-stack query | this change | change 2 `ring_of_reflux` per-stack bonus reads the three keys; catalog binds them |
| `suffocated` marker + `actions_per_turn` lock | this change | catalog row for 溺潮's reaction binding |

## Risks / Trade-offs

- The DoT refresh-vs-stack gap: lore says 潮退 是可疊加 (stackable) marks while the shipped stacking vocabulary is `refresh`/`unique_per_source`. Resolution: the wave ships refresh-tier rows; a per-cast-instance stacking mode is change 2's decision (its restore bonus needs counts) — if change 2 introduces an instance-key scheme (`unique_per_source` with per-cast source keys), the DoT rows move to it in that change, which owns this design line.
- Routing the cast cost means a caster CAN zero their own MP and dispatch `mp_zero`; the rule layer decides punishment, and today's only listener is the drowning-qualified row. Accepted per the global-fact given.
- `mp_zero` dispatch inside `PendingEffect.apply()` can raise nothing by design (reactions apply buffs; apply_buff cannot reject an authored key), so step-6 rollback semantics are unchanged; the cascade rides the same transaction that already contains `hp_loss` cascades.

## Migration Plan

No migrations, no aliases (zero users). Land writer + routing + when-key + rows + synthetic behavior tests in one commit per task group; focused tests only. Main-spec sync stays in the separately authorized archive workflow.

## Verification contract (shared, per wave design D-common)

unittest synthetic entities (no-create fixtures like the existing buff tests' `_entity()`) must fail on plausible bugs: double dispatch on already-zero MP, dispatch on increase, cast-cost bypass leaving no event, hp-branch regression, refresh-not-new-instance misfire, immunity blocking (潮退 is a debuff — worn-equipment debuff immunity must refuse it without suppressing the writer), and cascade rollback inside a failing clock advance. Focused invocation in tasks.md; `MUD_TEST_SETTINGS=1` via the tool env, never a shell prefix.
