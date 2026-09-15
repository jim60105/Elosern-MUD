## Batch order (water wave)

1. `water-mp-depletion-reaction` — predecessor (canonical writer, 潮退 rows, cast-condition vocabulary). MUST land first.
2. `water-mana-transfer` (this change) — the 回流 team marker is folded in here (design D5); no separate evidence-ledger change.
3. `water-damage-redirect-shield` — independent of this change; both depend on 1.
4. `water-spell-catalog` — data-only final integration, depends on all.

## 1. Typed family and policy

- [x] 1.1 Inspect current source and exported references (codegraph/LSP) for `parse_effect`, `EffectPolicy`, `_resolve_effect_context`, `_handle_divine_drain` and the audience planner before editing; confirm the predecessor's writer API and 潮退 keys match ../water-spell-catalog/design.md.
- [x] 1.2 Implement `GaugeTransferEffect` parsing (closed gauge set {mp,hp} with `sp` rejected at parse; closed directions; `fixed:<positive int>`, `fraction:` finite (0,1], `all`; hp drain-only — an hp restore fails construction since HP restoration is the heal effect's exclusive verb) and `GaugeTransferPolicy` on `EffectPolicy` with DamagePolicy-posture fail-closed validation (share range, existing-buff marker keys, bonus-only-on-restore, coefficient rejection) per design D1, plus the validated `audience_condition` field (design D4) and the unconditional execution-tier bypass relaxation (`bypass_defense=True` with an empty predicate validates; multiplier-with-empty-predicate stays invalid).
- [x] 1.3 Register the generic `gauge_transfer` handler (`surfaces={"traits"}`): drain/restore legs stage one PendingEffect per mutated entity; per-gauge canonical routing per design D2b — mp drains through `remove_mp`/`apply_mp_change` with cast-skill attribution, hp drains through the existing attributed hp-loss write path buffs rate-tick uses (`hp_loss` dispatch with source attribution, no new `hp_zero` fact, death settlement left to the combat/death pipeline); caster share = round(actual drain × (authored share + gauge-agnostic bundle `recovery_share_bonus`)) capped at the actual drain, paid in the same gauge; restore (mp only) = authored base + per-key active-stack counts read on the CASTER via the buffs.py count helper; commit-time magnitude reads per design D2.

## 2. Markers and clock

- [ ] 2.1 Add `mp_regen_lock` (60 s, debuff, empty modifiers) and `mana_reflux` (60 s, buff, refresh, empty modifiers) rows to `buffs.yaml`; `combat_modifiers.yaml` rows `mp_regen_lock_freeze` (`mp_regen_scale: 0`) and `mana_reflux_share_bonus` (`recovery_share_bonus: 0.1`); matching `status_display.yaml` entries; one unit test per new rule ID.
- [ ] 2.2 Extend `_settle_gauge_regen` to multiply each gauge rate by the bundle's `{gauge}_regen_scale` (absent 1.0) inside the existing closed form without touching `regen_remainder` while zero (design D3); verify unlocked arithmetic is unchanged.
- [ ] 2.3 Implement `EffectPolicy.audience_condition` (closed gauge-state fields `mp_max_zero`/`mp_positive`, construction-time fail-closed validation) and apply it in `plan_effect_audiences` with the same evaluation in preflight and final resolution; ship the synthetic disjoint-subset proof (ungated component to all + zero-max rider to the matching subset) demonstrating 溺潮's redirect is expressible as pure catalog data (design D4).

## 3. Behavioral evidence and integration

- [ ] 3.1 Implement synthetic behavior tests for every delta scenario: mode parsing/fail-closed authoring (including `sp`/unknown-gauge parse rejection and hp-restore construction rejection); share-on-actual (clamped drain); fraction rounding; whole-pool drain dispatching one attributed depletion event; hp drain with share paying on the ACTUAL drained HP with attributed `hp_loss`; hp drain-to-zero producing exactly one death settlement (combat/death pipeline's single settlement, no second kill path, knockout projection honored); half-applied-leg rollback; restore stack-count from the caster (never recipient) with per-target clamping; regen lock freeze/remainder/expiry and item-grant bypass; closed-form single-step with scale; share-bonus window open/closed, cap at one whole, restore immunity; disjoint-subset cast settlement. Each test must fail on a plausible behavioral error. No water data-contract tests (ratified NON-GOAL).
- [ ] 3.2 Register new non-browser test modules in exactly one `.github/evennia-shards.json` shard and verify the ownership optimization contract test.
- [ ] 3.3 Disposable offline scenario: drain an MP-holding synthetic entity through a fraction transfer with share, observe both gauge legs + depletion marker; advance clock through a regen lock; delete only after proof.
- [ ] 3.4 Run the focused labels below after editing stops; `tools.observability_lint check` same batch (event/state paths change); `tools.test_data_lint check`; `tools.spec_traceability check`; `openspec validate water-mana-transfer --strict`. Canonical IDs come from `tools.spec_traceability list` at the separately authorized main-sync.

### Focused invocation

```sh
uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_gauge_transfer world.skills.tests.test_effects world.rules.tests.test_clock world.rules.tests.test_combat_modifiers world.rules.tests.test_conditional_damage
uv run --locked python -m tools.observability_lint check
uv run --locked python -m tools.test_data_lint check
uv run --locked python -m tools.spec_traceability check
openspec validate water-mana-transfer --strict
```

Pass `MUD_TEST_SETTINGS=1` through the tool environment, never a shell prefix. No full local suite/browser/aggregate-coverage run; no command above ten minutes. No apply, archive, main-spec sync or merge in the proposal turn.
