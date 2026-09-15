## Context

Small magnitude-mode extension for the two dark nodes whose recovery clause is keyed to the caster's missing HP (`docs/lore/skill-trees/dark.md`: `void_annihilation` 10%, `abyssal_apotheosis` 15%; design note 掠取與自癒是兩回事 pins that these cast-time self-recoveries are NOT the erosion-tick leech — different magnitude basis, never double-priced). Wave contract lives in `../dark-spell-catalog/design.md`.

**Investigation verdict (mandated, with evidence):**

- The shipped `self_heal` basis is caster-stat, NOT missing-fraction. `_handle_self_heal` (`world/rules/combat.py:645`) stages `amount = scaled_magnitude(_heal_magnitude(actor, coefficient), scale)`; `_heal_magnitude` (`world/rules/combat.py:547`) computes `max(round(magic_power × COMBAT_YAML heal.multiplier × coefficient), floor)` then applies the merged `heal_gain` percent. `_restored_amount`/`_apply_heal` only clamp the computed amount to the living HP gap. No read of the caster's missing HP exists anywhere on the self-heal path.
- The shipped self-heal content is stat-basis only: the sole real registry row carrying `self_heal` is `sacrificial_flame` (`world/skills/registry.py:779`, 燔祭焰, effects `("damage:fire:magic", "self_heal")` — bare form). `phoenix_eternal_flame` never landed: it appears ONLY in the frozen `docs/superpowers/specs/2026-08-12-skill-system-redesign-design.md` catalog table (and a title-system doc's flavor reference); no `world/skills/registry.py` row, no requirement ID, no test. The self-heal flavor that shipped was the bare stat-basis form.
- Verdict: the magnitude-mode extension IS needed — folding the nodes into the catalog change would silently drop the 10%/15% clauses (a stat-basis self-heal is a different quantity, not an approximation the lore sanctions).

## Goals / Non-Goals

**Goals:** One typed magnitude mode on `self_heal` mirroring `gauge_transfer`'s magnitude-mode design; missing-HP-fraction magnitude with the existing clamps/no-revival/scale composition; bare form untouched; authoring mistakes fail before any cast.

**Non-Goals:** No change to `heal` (target restoration stays stat-basis — light's exclusive verb needs nothing here); no buff/reaction/modifier rows; no registry rows (catalog change); no new event or reaction; no data-contract tests; no second heal prefix (`self_heal:<mode>` grammar, not a new verb).

## Decisions

### D1 — Mode lives in the effect ID, not in EffectPolicy
`gauge_transfer` carries its magnitude mode in the effect string (`gauge_transfer:<gauge>:<direction>:<mode>:<arg>`) and reserves `EffectPolicy`/`GaugeTransferPolicy` for per-occurrence bonuses. `self_heal` mirrors exactly that split: `self_heal` (bare → `SelfHealEffect(basis="stat")`) and `self_heal:missing_fraction:<f>` (→ `SelfHealEffect(basis="missing_fraction", fraction=f)`, `f` finite in (0, 1], everything else `ValueError` at parse → registry-load failure). Rejected: a policy-only declaration — it would leave the typed effect unable to state its own basis, splitting one verb's grammar across two surfaces for no gain.

### D2 — Basis reads the caster's own HP gap at staging time
`amount = round((max_hp − current_hp) × fraction)` read from the caster's stored gauge at staging time, the same moment the stat basis reads its stats; the staged description carries the computed amount exactly as today, and `_apply_heal`'s commit-time alive guard + maximum clamp stay the only commit-time re-checks. Deliberate: this is a MAGNITUDE of one effect occurrence in one cast — the stateful-spell-casting canonical-pre-effect-inputs convention applies unchanged (no new snapshot machinery, unlike the buff-side leech whose origin must survive between casts). A dead or full caster yields 0 at staging, so the event log reports the real increase.

### D3 — Potency, scale, and heal_gain composition
- Potency: the fraction IS the magnitude, so a coefficient ≠ 1.0 attached to a `missing_fraction` occurrence is rejected at `SkillDef` construction through the existing per-effect validation surface (registry.py's coefficient gate already whitelists `SelfHealEffect`; this change narrows the whitelist to the stat basis for coefficients). The bare form keeps coefficient behavior verbatim.
- Freeform scale: `self_heal` is already in `_FREEFORM_SCALABLE_PREFIXES` (prefix-level), so a scaled missing-fraction cast multiplies the computed amount through the existing `scaled_magnitude` leg — same determinism, same rounding, no cost_tiers change.
- `heal_gain`: NOT applied. `heal_gain` is defined in the shipped contract as amplification of the stat-derived base (`_heal_magnitude`'s normative formula); the missing-fraction base is caster-state-derived, not stat-derived. Pinned by test so a later edit doesn't fold it in silently.

### D4 — Interface ownership (opened by this change)

| Interface | Owner | Consumers |
|---|---|---|
| `SelfHealEffect(basis, fraction)` + `self_heal:missing_fraction:<f>` grammar + handler leg | this change | `dark-spell-catalog` authors `void_annihilation`/`abyssal_apotheosis` effect data |

## Risks / Trade-offs

- **15% of missing HP on a near-dead caster can exceed the stat basis** — that is the design (the node is stronger the worse the caster is doing); the cap is the caster's own gap, so it can never overshoot maximum. No band check needed: this clause is the node, not a stat number.
- **Two bases on one prefix** keeps the grammar closed and the typed dataclass one — a future third basis extends the same closed set; nothing dark-named is read by the handler.
- **Bare-form regression risk** is zero by construction (parse default `basis="stat"`, handler branch guarded on basis) and pinned by the existing `test_heal_effect_handler.py`/`test_freeform_casting.py` suites staying green unchanged.

## Migration Plan

No migrations: the bare grammar and all shipped rows/behaviors are untouched; the new form has zero existing users until the catalog change authors it. Parse → dataclass → handler leg → authoring validation → synthetic proof, one slice.

## Verification contract

Shared wave contract (`../dark-spell-catalog/design.md`). Synthetic skills/entities through real settlement; tests MUST fail on: fraction read from the TARGET's gap instead of the caster's, amount escaping the maximum clamp, a dead caster revived or credited, scale/rounding drift from the existing scaled-heal contract, `heal_gain` silently amplifying a missing-fraction amount, coefficient accepted on the new basis, malformed fraction (`0`, `1.5`, `-0.1`, `abc`, bare extra segments) reaching a castable registry row.
