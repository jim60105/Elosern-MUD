## Context

Delivers dark's HP-掠取 verb — the erosion-tick transfer clause of `docs/lore/skill-trees/dark.md` (shadow_torture / shadow_blight / dark_corrosion_domain: 「流失量全額轉入施法者」; design note 侵蝕即掠取: 「凡受蝕者每次流失的 HP 全額轉入當初施加侵蝕的施法者…施法者死亡或受蝕者死亡，該條掠取即熄滅」) — against the shared wave contract in `../dark-spell-catalog/design.md`. Predecessors: the FULLY ARCHIVED light and water waves shipped every surface this rides — the attributed hp-loss write path with `actual_loss` computation inside `_apply_rate_modifier`, grant-time `source_pk`/`source_skill` persistence on damaging rate buffs (`buff-handler-integration`'s source-identity requirement), and `gauge_transfer`'s caster-share leg (`_handle_gauge_transfer`'s hp credit: clamped at maximum, guarded `current <= 0 → return`).

Pre-audited engine facts (verified at authoring):

- `_apply_rate_modifier` (`world/rules/buffs.py`) already computes `actual_loss = max(0, int(before - max(0.0, after)))` per hp tick and dispatches exactly one `hp_loss` outcome afterwards; the buff cache already carries the origin caster's dbref (`source_pk`) and skill key under the shipped attribution contract (`_handle_buff_apply` pops caller-supplied values, derives from the actor, rejects actors without a resolvable positive-int pk).
- `TickRecord` already carries `source_pk` for the upkeep death-credit settlement (`world/rules/upkeep.py::_resolve_source`); that consumer is HP-crossing credit only and stays untouched — the leech credit is a separate concern at the tick site, not a new upkeep stage.
- The reaction engine (`world/rules/state_reactions.py`) is victim-scoped with a closed then-vocabulary {`apply_buff`, `remove_buff`, `pleasure_gain`} and no amount or cross-entity recipient in its dispatch context; `dispatch_outcome_reaction(entity, "hp_loss", …)` carries only `source_tier`/`source_skill`.
- `parse_effect`'s `gauge_transfer` family parses a cast-time event (D0 of the archived water-mana-transfer change pre-authorized dark to author `gauge_transfer:hp:drain:*` **data** for its 掠取 nodes).

## Goals / Non-Goals

**Goals:** One declarative transfer clause on the buff rate row; per-tick exactly-once credit of the ACTUAL eroded HP to the grant-time origin caster; extinguishment on either party's death, expiry or dispel; a behavior-test-only proof; everything generic — any future element's DoT may declare a share, dark authors 1.0.

**Non-Goals:** No dark registry rows or erosion buff rows (catalog change owns the data); no `state_reactions.yaml` vocabulary growth; no new scheduler, ledger, or second transfer family; no MP-side leech (the water wave's mp drains already own that gauge); no data-contract tests (ratified NON-GOAL); no cast-time drain work of any kind (`gauge_transfer:hp:drain:*` already shipped — see D2 boundary).

## Decisions

### D1 — Carrier: the buffs.yaml rate-row transfer clause, NOT a state_reactions then-clause (ratified decision, evidence-based)

Two candidate homes were examined; the reaction then-clause loses on every axis, and adopting it would in fact build a second engine inside the reaction layer:

| Axis | buffs rate-row clause (chosen) | state_reactions then-clause (rejected) |
|---|---|---|
| Amount basis | `actual_loss` is ALREADY computed at the exact tick site (post-clamp, floor-aware) | the `hp_loss` dispatch payload carries no amount — only `source_tier`; a then-clause would re-derive (double-read) or require widening the event payload into the closed reaction grammar |
| Recipient | the buff cache already persists the grant-time origin `source_pk` (the lore's 「當初施加侵蝕的施法者」 snapshot is exactly this shipped field); credit rides the shipped `gauge_transfer` caster-share clamped-increase leg | the reaction engine is structurally victim-scoped: `then` may only write to the dispatched entity; a transfer needs a cross-entity recipient — a new verb class, new dispatch context, new validation — i.e. a second rules engine inside the one the constitution forbids duplicating |
| Exactly-once | one tick, one computed loss, one credit, in one function | the `hp_loss` dispatch point is shared by ALL hp-loss paths (melee damage, drain, ticks); an amount-carrying reaction keyed on hp_loss while `buff_active: <erosion>` would also credit non-erosion losses (or need event-carrier disambiguation it doesn't have) |
| Recursion | the credit leg performs a clamped pure increase and dispatches no outcome — the victim's own reaction set is untouched | crediting through any writer that dispatches `hp_loss`-family facts risks re-entering the reaction engine that produced the credit |
| Precedent | the water wave's caster-share fold (`action.py` `_handle_gauge_transfer`) is the shipped shape of "pay the caster from what actually left the target" | the reaction engine has never moved resources or gauges; `pleasure_gain` is its only quantity and it is victim-scoped by design |

The clause shape: `modifiers: {rate: {target: hp, delta: <negative>, caster_share: <fraction in (0,1]>}}`, validated fail-closed at `load_buff_definitions` (reject on non-hp target, non-negative delta, non-finite/out-of-range/boolean value, or co-declaration with `recovery`/`scale_from_source`). The full-amount lore clause authors `caster_share: 1.0`. Fire's `fire_scorch`/`poisoned` rows declare nothing and tick bit-identically — the clause is additive vocabulary, zero dark keys in generic code.

### D2 — The gauge_transfer boundary (mandatory fit check, one paragraph)

The archived water-mana-transfer design (D0) obliges the dark wave to check `gauge_transfer:hp:drain:*` before inventing anything, and the answer is a clean split with zero overlap: **`gauge_transfer` is a cast-event verb** — the spell resolves, the handler drains an authored fixed/fraction/whole amount from the target's CURRENT pool at commit time, and the caster-share policy pays a share of what was actually taken, all inside one paid action. **The erosion leech is an ongoing-DoT conversion** — there is no cast event at the moment of transfer; the amount is whatever one 10-second rate tick actually eroded (post-clamp, floor-bound at zero), the recipient is the caster snapshotted at buff-grant time (which may have happened hundreds of seconds earlier, by a different cast instance, and whose current state must not change the credit basis), and the lifetime is the buff's, not the action's. Retrofitting `gauge_transfer` to cover it would mean a deferred re-executing transfer effect with its own scheduling — the second engine the constraints forbid. Conversely, any dark node whose recovery is a cast-time event authors purely as `gauge_transfer:hp:drain:*` data plus the appropriate `GaugeTransferPolicy` share (the D0 note's authorization stands and applies to any such future node; the current 13-node table contains none — the void_annihilation/abyssal_apotheosis clauses are self-heal on the caster's own missing HP, owned by `dark-self-recovery-missing-fraction`, per dark.md's 掠取與自癒是兩回事 note which also rules the two mechanisms never double-price each other).

### D3 — Credit semantics (the pinned invariants)

1. **Exactly-once attribution per tick.** One tick computes `actual_loss` once; the credit is `floor(actual_loss × caster_share)` paid in the same pass. The `hp_loss` outcome dispatch stays exactly where it is (one dispatch per qualifying crossing-loss, unchanged), and the credit leg dispatches NOTHING — no `hp_loss` for the caster, no `negative_buff_added`, no reaction re-entry. Tests must fail on a double credit and on a credit that fires the victim's reactions a second time.
2. **No double death settlement.** The victim's tick-to-zero crossing keeps its single terminal settlement in the combat/defeat pipeline (unchanged behavior: the tick already floors at the write path's rules and `settle_upkeep` already projects the defeat credit from `TickRecord`). The leech never participates in settlement: a tick that would kill the victim still credits the caster only for HP actually removed before the crossing, and the removal of the buff on a dead victim produces no further credit.
3. **No resurrection credit; HP floor.** The credit only ever increases a LIVING origin caster (`current > 0` guard, mirroring the shipped `gauge_transfer` actor-share leg and `_restored_amount`'s never-revive posture), clamped at the caster's maximum — a dead origin is skipped silently per tick (which also realizes extinguishment), and an over-full caster absorbs into the cap with no spill.
4. **No below-floor credit.** The credit magnitude derives from `actual_loss` — by construction never more than the victim actually lost — so a victim floored at zero contributes at most its remaining HP, matching the lore's 「敵人流完 HP 就無可再抽」.
5. **Origin snapshot and extinguishment.** Origin = the buff cache's grant-time `source_pk` (refresh already replaces it with the newest caster under the shipped source-replacement contract — the lore's 「當初施加」 reads to the most recent applicator, the same semantics upkeep credit uses). Extinguished when: the buff expires/is dispelled/cleaned (instance gone → no tick → no credit, automatic); the victim dies (no ticks after settlement); the origin dies or cannot be resolved to a living entity (per-tick skip, exactly how upkeep silently skips unresolvable `source_pk`). Resolution reuses the upkeep `_resolve_source` posture (roster first, then db lookup) without extending that function's contract.
6. **Genericness.** No element key is read anywhere; any future hp-target rate row may declare a share. The leech is dark's verb by allocation, enforced by lore review, not by a code branch.

### D4 — Interface ownership (opened by this change)

| Interface | Owner | Consumers |
|---|---|---|
| `caster_share` clause in the buffs rate grammar (validation + tick-site credit leg) | this change | `dark-spell-catalog` authors the erosion rows' data (`shadow_torture`/`shadow_blight`/`dark_corrosion_domain` buff rows at share 1.0) |
| Origin-resolution posture at the tick site (grant-time `source_pk`, living-only credit) | this change | any future DoT-family element |

## Risks / Trade-offs

- **Refresh steals the origin.** A second caster re-applying the same erosion key redirects future ticks' credit to themselves (refresh stacking, single instance). This is the shipped source-replacement contract and matches upkeep kill-credit; per-caster leech instances would need `unique_per_source` erosion keys — not authored, not needed by the lore.
- **Crossing-tick loss accounting.** The lore says the leech dies with the victim; a lethal tick therefore credits only the pre-crossing HP actually removed (floor-bound), never the "overkill" remainder — same basis upkeep credit already uses (`applied = min(-delta, hp_before)`).
- **Dead-caster per-tick lookup cost** is one roster/dbref resolution on ticks that can no longer credit; acceptable at DoT cadence (per 10 s) and identical in shape to the existing upkeep unresolvable-source path.

## Migration Plan

No migrations. Definition validation → tick-site credit leg → synthetic behavior suite → shard registration, in one reviewable slice. The erosion buff rows themselves land in `dark-spell-catalog` (this change ships zero live `caster_share` rows — inert-but-valid vocabulary exactly as the water wave shipped `gauge_transfer`'s hp leg ahead of its consumers).

## Verification contract

Shared wave contract (`../dark-spell-catalog/design.md`): synthetic buffs/entities only; tests MUST fail on plausible bugs — credit on requested-not-actual loss, credit to a dead origin, double dispatch of `hp_loss`, credit bypassing the caster's maximum, share paid after the buff expired, `caster_share` accepted on a non-hp/non-damaging row, and a refresh that keeps crediting the previous origin when the contract says newest-caster-wins. Real settlement through `tick_buffs`/upkeep, not unit-level function poking alone.
