## Why

Two dark capstone nodes carry a battlefield self-recovery clause — `void_annihilation` 「命中回復施法者已損 HP 的 10%」 and `abyssal_apotheosis` 「…15%」 — and the investigation verdict is that the shipped `self_heal` effect cannot express it. `_handle_self_heal` (`world/rules/combat.py`) computes its amount exclusively through `_heal_magnitude`: `round(magic_power × heal.multiplier × coefficient)` with the merged `heal_gain` percent — a caster-stat coefficient basis with NO missing-HP-fraction mode (`_restored_amount`/`_apply_heal` only clamp the result to the HP gap). The shipped self-heal content confirms the gap: the only real registry row pairing damage with self-heal is `sacrificial_flame` (`world/skills/registry.py`, 燔祭焰) using the bare stat-basis `self_heal`, and the lore table's `phoenix_eternal_flame` (不滅鳳凰焰, 「極高傷害+自我治療」) never landed as a registry row at all — it exists only in the frozen 2026-08-12 design doc, so no shipped node ever needed a missing-fraction basis. Dark.md's note 掠取與自癒是兩回事 makes the split normative: this recovery's magnitude basis is the CASTER's missing HP — a different quantity from both the stat basis and the erosion leech's enemy-basis transfer — so the nodes cannot be folded into existing data. This change is the small magnitude-mode extension that makes the clause authorable as data.

User-ratified givens recorded: declarative vocabulary extension to an existing surface (no second heal verb, no dark-key branch); clean cut, zero users — the bare `self_heal` form keeps its current grammar and behavior unchanged; NON-GOAL: no data-catalog tests.

## What Changes

- Extend the closed `self_heal` effect grammar with one magnitude mode, mirroring `gauge_transfer`'s magnitude design: `self_heal:missing_fraction:<f>` with `<f>` a finite number in (0, 1], parsed into a typed `SelfHealEffect(basis="missing_fraction", fraction=f)`; the existing bare `self_heal` parses to `basis="stat"` and is bit-identical. All other payloads keep failing closed.
- Handler semantics: the missing-fraction leg computes `round(missing_hp × fraction)` from the caster's OWN HP gap (maximum minus current, read at staging time like the stat basis), still routes through the existing `_restored_amount`/`_apply_heal` clamps — never above maximum, zero for a dead caster (no revival), commit-time alive guard unchanged — and multiplies by the freeform cast `scale` through the existing `scaled_magnitude` leg exactly as the stat basis does. A non-identity potency coefficient on a missing-fraction declaration is rejected at construction (the fraction IS the magnitude; no second scale).
- No buffs.yaml / combat_modifiers.yaml / state_reactions.yaml change, no registry rows (the catalog change authors the nodes), no change to `heal` (target-audience restoration keeps its stat basis — only the actor-bound `self_heal` gains the mode).

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `skill-effect-model`: the `parse_effect` closed-set requirement — `self_heal` accepts exactly two grammar forms (bare stat basis; `missing_fraction:<f>` with validated fraction), strict superset, all existing scenarios preserved verbatim.
- `heal-effect-handler`: the `self_heal` actor-binding requirement and the no-revival requirement — each extended with the missing-fraction basis semantics (clamps, no-revival, scale composition), strict superset preserving every existing scenario name.

## Impact

`world/skills/effects.py` (`SelfHealEffect` fields + `parse_effect` self_heal branch); `world/rules/combat.py` (`_handle_self_heal` magnitude leg); `world/skills/registry.py` construction validation (coefficient rule for the new basis, inside the existing per-effect potency checks); focused tests in the existing `test_heal_effect_handler.py`/`test_effects.py` modules plus synthetic settlement; `.github/evennia-shards.json` only if a new module is needed (prefer extending the existing registered ones).

`openspec list --json` returned an empty change set at authoring time — no active-change conflicts; this change is independent of `dark-erosion-leech` (no shared files) and precedes `dark-spell-catalog`. One engineer-day; behavior-test-only verification.

This turn creates planning artifacts only. Do not apply, archive, sync main specs, create feature branches or merge until requested.
