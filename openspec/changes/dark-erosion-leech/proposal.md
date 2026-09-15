## Why

Dark's exclusive combat verb per the constitution (`docs/lore/skill-trees/index.md` §4.2 dark row) is 屬性增減益 + 心理性靜止 + **HP 掠取**, and the ratified border clause names its carrier precisely: 「侵蝕 tick 轉入施法者的 HP 屬本動詞延伸」. The updated node table (`docs/lore/skill-trees/dark.md`, commit b69d47a) now states the clause on every erosion node — `shadow_torture`, `shadow_blight`, `dark_corrosion_domain` all carry 「流失量全額轉入施法者」 — and the design note 侵蝕即掠取 fixes the mechanics: every HP an eroded victim loses transfers in full to the caster who applied the erosion; the leech extinguishes when either party dies. Today a buff rate tick damages HP through `_apply_rate_modifier` (`world/rules/buffs.py`) and the loss simply vanishes — dark's only effect-layer distinction from fire's 灼燒 line (「火的灼燒只燒人，暗的侵蝕燒了還要回收」) is unimplementable. This change ships that tick-carried transfer as one declarative vocabulary extension to the existing rate-modifier surface.

User-ratified givens recorded: **no second rules engine, no dark-key branches in generic code** — the leech is a validated clause on the existing `buffs.yaml` rate row, settling through the EXISTING attributed hp-loss write path on the victim and crediting the origin caster's HP through the same clamped-increase leg the shipped `gauge_transfer` caster-share already uses. **NON-GOAL: 遊戲資料契約** — verification is behavior contracts on synthetic buffs/state transitions only. **Clean cut, zero users**: no migrations, no aliases.

## What Changes

- Extend the `buffs.yaml` rate-modifier grammar with one optional validated transfer clause (`caster_share`, a finite fraction in (0, 1]) legal ONLY on an hp-target negative-delta rate row; every other placement fails closed at definition load. The full-amount dark leech authors as `caster_share: 1.0`.
- On each damaging tick, `_apply_rate_modifier` (which already computes the tick's `actual_loss` and already has the grant-time `source_pk`/`source_skill` attribution in the buff cache) resolves the origin caster from the persisted grant-time source and credits `floor(actual_loss × caster_share)` HP to that caster through the same clamped-alive-increase leg `gauge_transfer`'s caster-share HP leg uses: never above the caster's maximum, never to a dead caster (no resurrection credit), exactly once per tick on the ACTUAL loss, dispatching no further hp-loss outcome (no recursion into the victim's or caster's reactions).
- Leech lifetime rides the buff instance: refresh replaces the origin with the newest caster exactly as the existing damaging-buff source-replacement contract already does; expiry, dispel, victim death and origin-caster death (unresolvable or fallen source) each end the credit with zero writes while the tick itself behaves unchanged.
- No registry rows, no dark buff rows, no `state_reactions.yaml` vocabulary change (the carrier decision and its rejected alternative are argued in design.md D1; the `gauge_transfer` boundary in D2).

## Capabilities

### New Capabilities
- `erosion-leech`: the tick-carried HP transfer itself — validated rate-row clause, actual-loss exactly-once attribution to the grant-time origin caster, clamped alive-only credit, extinguishment semantics, and generic (element-agnostic) reuse.

### Modified Capabilities
- `buff-handler-integration`: the rate-modifier definition vocabulary gains the validated `caster_share` transfer clause (strict superset of the rate/bounds/divert/decay definition requirement; all existing scenarios preserved verbatim).

## Impact

`world/rules/buffs.py` (definition validation + `_apply_rate_modifier` credit leg); `world/rules/rulebook/buffs.yaml` untouched by this change (the erosion rows are authored by `dark-spell-catalog`); new focused behavior test module registered in `.github/evennia-shards.json`; `docs/traceability` ledger hygiene stays in the separately authorized main-sync.

`openspec list --json` returned an empty change set at authoring time — all light/water/taxonomy changes are archived, no active-change file conflicts; the dark wave's internal ordering is declared in `dark-spell-catalog/design.md`. This is a bounded one-engineer-day slice; verification is synthetic behavior tests only.

This turn creates planning artifacts only. Do not apply, archive, sync main specs, create feature branches or merge until requested.
