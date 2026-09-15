## Why

Every clause of water's mana-tide verb that is not a DoT or a reaction is a **transfer**: 潮引術 pulls 5 MP and hands half back to the caster; 深淵巨口 drains 20 % of the target's current pool into the caster; 枯海之印 empties the pool and locks regen for 60 s; 回流之環 and 深淵潮汛 pour MP back (40 + a per-潮退-stack bonus; 25 to every ally); 深海神格 drains all enemies and refills all allies in one cast. The effect vocabulary has no MP mover today — `mana_restore`'s 40-MP magnitude exists only as an item-side `stat: mp` row — and the only cross-resource transfer in the engine (`divine_drain`, pleasure→HP/MP/SP) hand-writes the actor's gauges, bypassing the canonical writer the sibling wave made mandatory. Without one typed transfer family, each of these nodes would need its own handler branch: exactly the second-engine shape the design forbids.

## What Changes

- Add the typed `mana_transfer` effect family to `parse_effect`: `mana_transfer:<drain|restore>:<fixed N | fraction f | all>` with a validated magnitude grammar; malformed authoring fails at registry construction.
- Add an immutable `ManaTransferPolicy` to `EffectPolicy` (per-ordinal, validated, `DamagePolicy`-posture fail-closed): `caster_recovery_share` (fraction of the ACTUAL drain returned to the caster), `restore_bonus_per_stack` (marker keys + amount, read on the caster — 回流之環's +10 per 潮退 stack). Caller context can never override authored policy (trusted `ResolvedEffect` path only).
- Register one generic `mana_transfer` cast handler staging per-target `PendingEffect`s: drains go through the canonical MP writer (so a drain that zeroes the target dispatches the wave's `mp_zero` fact with the cast as source); the caster-side share pays through the same writer; restores clamp at each target's MP maximum and route through the writer's increase path. Audience routing comes from the existing `EffectAudience` planning, never handler-local faction tests.
- Ship the per-effect target-state gate that 溺潮's zero-MP-cap redirect needs (design D4): `EffectPolicy.audience_condition` — one validated declarative per-component audience gate (closed gauge-state vocabulary: recipient's MP maximum zero, or positive), evaluated per resolved target at audience planning and mirrored between preflight and final resolution, skipping ONLY the gated component for non-matching targets. No rider field, no reaction-engine branch, no whole-cast rejection. This change ships the gate plus a synthetic proof; the catalog change authors 溺潮's redirect as pure data.
- Add the bounded regen lock: marker buff key `mp_regen_lock` (60 s) whose sole mechanical row is an ordinary `combat_modifiers.yaml` rule contributing a new bundle value `mp_regen_scale: 0`; the world clock's closed-form gauge-regen stage multiplies each gauge's rate by its bundle scale (absent = 1.0), no per-second loop change and no water key in the clock.
- Ship the 深淵潮汛 ally-side 回流 team marker (design D5): one beneficial marker buff (`mana_reflux`, 60 s, refresh) whose sole mechanical row is one ordinary `combat_modifiers.yaml` rule contributing a generic `recovery_share_bonus` bundle value that the transfer handler's caster-share read site folds additively — any drain node authored with a caster share gains the extra percentage with zero per-node code, no evidence ledger and no second engine.

## Capabilities

### New Capabilities
- `mana-transfer-effects`: the typed drain/restore family — magnitude modes, caster-share recovery (including the marker-borne `recovery_share_bonus` folded from the combat-modifier bundle at the same read site), per-stack restore bonus, canonical-writer routing on both sides, audience routing, regen-lock marker semantics, and the zero-cap redirect composition rule.

### Modified Capabilities
- `skill-effect-model`: `parse_effect` classifies the new prefix into a typed dataclass, `EffectPolicy` carries the validated transfer policy, and effect audiences may carry one immutable validated target-state gate (superset edits of the typed-classification and effect-audience requirements).
- `action-resolution-pipeline`: audience planning applies each component's validated `audience_condition` gate with the existing preflight/final agreement (superset of the audience-agreement requirement).
- `world-clock`: gauge regen honors a per-gauge regen-scale bundle value with the same closed-form arithmetic (superset).
- `combat-resolution`: the damage formula gains the unconditional execution-tier bypass (`bypass_defense=True` with an empty predicate, validated) alongside the predicate-matched bypass, so execution-tier nodes are authorable as data (superset of the banded-multiplier requirement).
- `combat-modifier-table`: the regen lock and the reflux share bonus ship as two ordinary `buff_active`-origin rows contributing new generic leaf values to the merged bundle, and the new water marker rows keep the table's one-rule-one-test correspondence (superset).

## Impact

`world/skills/effects.py` (transfer dataclasses + policy field + parse branch + `audience_condition` validation); `world/rules/action.py` (one transfer handler + the audience-planning gate filter, staging closures over snapshotted surfaces); `world/rules/clock.py` (regen stage × bundle scale); `world/rules/rulebook/buffs.yaml`, `combat_modifiers.yaml`, `status_display.yaml` (regen-lock and reflux-marker rows + display entries); new focused test modules registered in `.github/evennia-shards.json`. `openspec list --json` returned an empty change set at authoring time — no serialization gate. Depends on `water-mp-depletion-reaction` (canonical MP writer, 潮退 DoT rows + attribution fields); independent of `water-damage-redirect-shield`. One engineer-day. Verification is synthetic program-behavior tests only — per the ratified NON-GOAL there are no water catalog/data-contract tests, no MP-cost/cap/tier table assertions, no echo tests of the water.md table.

Planning artifacts only this turn; no apply/archive/sync/merge.
