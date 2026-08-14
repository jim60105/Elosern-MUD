## Context

`dual_wield_style` is the remaining half-migrated skill from the run-2 audit finding "18 inert ACTIVE
skills". The archived `weapon-style-stance-split` change shipped the rule-table half of design doc
§3.3's ruling — `combat_modifiers.yaml` row `dual_wield_style_atk_phys_bonus` (`skill_owned` +
`dual_wielding` conditions, granting `atk_phys: 5`) plus the typed `WeaponStyleEffect` — but never
reclassified the skill itself: `world/skills/registry.py:572-580` still declares `SkillKind.ACTIVE`,
`TargetSpec.SELF`, `cost={"sp": 8}`, `effects=["weapon_style:dual_wield"]`.

`weapon_style` has no entry in `action.py`'s `_EFFECT_HANDLERS` (the registered prefixes are
`confer_skill_partial`, `set_disguise`, `buff_apply`, `self_buff_apply`, `confer_growth_rate`,
`sexual_event`, `cleanse`, `divine_mystery`), so `_step5_effect_resolution`
(`action.py:541-569`) raises `UNKNOWN_EFFECT_ID` on every in-combat cast (out-of-combat attempts
are rejected earlier as `SKILL_NOT_USABLE_OUT_OF_COMBAT` at `action.py:224-228`, since the skill
is not `usable_out_of_combat`). The same dead shape was already
eliminated for `body_enhancement*` (`stat_multiply` had no handler) and `flight`/`flash_step`
(`movement` had no handler) by reclassifying to `PASSIVE`; `dual_wield_style` is the straggler.

Consumers of skill kind/cost/target were verified against the actual code:

| Consumer | Location | Effect of reclassification |
|---|---|---|
| `_step1_ownership` | `action.py:217-242` | Already raises `SKILL_NOT_ACTIVE` for non-ACTIVE — becomes the new rejection point |
| `_skill_wide_failure` | `action_preview.py:74-119` | Already returns `SKILL_NOT_ACTIVE` before any cost/target check |
| Monster/NPC AI policy | `combat.py:503-519`, `monster_behaviour.py:172-178` | Requires ACTIVE + `damage:` effect; stance is never selected — unchanged, correct |
| `spell_tier_for` | `cost_tiers.py:41-75` | Returns `None` for non-ACTIVE; `dual_wield_style` has no `mp`/element anyway |
| Preset kit validation | `player_presets.py:149-178` | Active keys must be ACTIVE — forces the preset bucket move |
| Import validation | `imports/validate.py:286-295` | Checks key existence only — unaffected |
| Typed effect model | `effects.py:252-253` | `weapon_style` already declared; docstring already names the stance-only consumer |
| Combat modifiers / status | `combat_modifiers.py:97,118,200`, `status_query.py:257` | Read the `skill_owned`/`dual_wielding` facts, not the kind — unaffected |
| Skill ownership | `skills/handler.py:39-45` | `owned_keys()` spans both buckets — a stale active-bucket entry still counts as owned |

## Goals / Non-Goals

**Goals:**
- `dual_wield_style` declares `PASSIVE` / `TargetSpec.NONE` / empty `cost`, matching every other
  ownership-triggered skill, so ownership alone drives the already-landed rule-table bonus.
- A cast attempt rejects `SKILL_NOT_ACTIVE` at the ownership step — never reaches `UNKNOWN_EFFECT_ID`.
- The `yuka_darknight` preset kit stays valid: `dual_wield_style` moves to the passive bucket while
  `dual_blade_mastery` and `shadow_slash` remain castable actives.
- The `dual_wield_style_atk_phys_bonus` adjustment and its status-display row are byte-unchanged.

**Non-Goals:**
- No `weapon_style` cast handler and no change to `light_sword_style`/`dual_blade_mastery`/other
  ACTIVE skills.
- No change to `effects=["weapon_style:dual_wield"]` or to `world/skills/effects.py`.
- No change to other dead-cost leftovers (e.g. `flash_step`'s `cost={"sp": 12}` on a PASSIVE
  movement waiver) — same class of smell, different finding; out of scope here.
- No player-command, schema, or docs changes.

## Decisions

**D1. Reclassify `kind` to `SkillKind.PASSIVE`.** Design doc §3.3 (§7: "保留為初階架式（改走
`skill_owned` 規則表）") mandates the ownership path; the precedent reclassifications
(`body_enhancement family is PASSIVE, not ACTIVE`, `flight and flash_step are PASSIVE`) define the
exact house shape. *Alternative considered:* register a `weapon_style` cast handler — rejected: a
stance has no cast-time effect (a standing posture, not a repeatable action), a handler would serve
exactly one skill, and it would duplicate the rule-table path that already exists and is tested
(`test_combat_modifiers.py:121-136`, `test_status_query.py:120-143`).

**D2. Change `target_spec` from `SELF` to `NONE`.** Target specs exist to drive cast-time targeting
(preview `_valid_candidates`, `revalidate_submission`, resolver step 3), all unreachable for a
PASSIVE skill. `NONE` is the declared shape of the rule-table passives (`reincarnation_boon*`
requirement: "all PASSIVE, `TargetSpec.NONE`", plus the mastery and instinct skills) and removes
the misleading "self-cast" affordance. (The `body_enhancement*`/`flight`/`flash_step` passives
still carry `SELF`, a vestigial carry-over of the same pre-redesign shape; a stance gets no
self-cast either, so `NONE` stays the correct target for this reclassification.) This explicitly
amends design doc §3.3's literal "a stance: `SELF` target" description, which described the
pre-reclassification declaration; §3.3's operative ruling — the stance is an ownership-triggered
rule-table skill, not a castable ACTIVE skill — is unchanged.
*Alternative considered:* keep `SELF` — rejected: it implies a cast path that must not exist.

**D3. Remove the dead `cost={"sp": 8}`.** No code path can spend SP on a PASSIVE skill: step 1
rejects before step 6's deduction, the AI affordability filters only consider ACTIVE damage skills,
and preview checks cost after the kind gate. Empty cost is the established passive contract
(mastery/boon skills, `spec.md:646` "empty cost") and prevents content authors from budgeting SP
against a skill that can never be cast. The design doc §7 SP-tier calibration table still lists the
8 SP as a pre-§3.3 reference; this change treats §3.3's stance ruling as superseding it. The
castable 架式 costs that remain (6/18/30) are untouched.

**D4. Keep `effects=["weapon_style:dual_wield"]`.** The rule row matches on `skill_owned`, never on
the effect string; `WeaponStyleEffect` is already typed and its docstring already documents the
stance-only rule-table consumer. *Alternative considered:* re-key to `passive_buff:dual_wield` to
unify with other rule-table skills — rejected: pure churn, and `_conferred_rule_scale`
(`combat_modifiers.py:141-163`) would then treat the stance as conferrable-scalable, a behavior
change with no feature behind it.

**D5. Move `dual_wield_style` to `yuka_darknight`'s `passive_skills`.** Required by the existing
load-time validation (`player_presets.py:159-171` raises on an active key whose kind is not ACTIVE).
The preset keeps its offensive kit: `dual_blade_mastery` (sp 30) and `shadow_slash` (sp 18) remain
active. `dual_wield_style`'s bonus then applies on preset activation whenever 悠花 equips two
weapons — the intended stance behavior.

**D6. Zero production changes outside the two registries.** Every consumer listed in Context
already keys on `SkillKind` and either handles PASSIVE correctly (resolver/preview) or requires
ACTIVE (AI). No resolver, preview, combat, tier, validation, or effect-model edits are needed; the
change is registry data plus tests. This keeps the change reviewable and matches how the precedent
reclassifications landed.

## Risks / Trade-offs

- [Risk] A dev database may hold a preset-created character with `dual_wield_style` in the *active*
  bucket. → Mitigation: `owned_keys()` spans both buckets (`handler.py:39-45`), so the rule-table
  bonus still applies and a cast still rejects `SKILL_NOT_ACTIVE`; no migration or repair script is
  needed (no released users).
- [Risk] The `skill-registry` main spec's `dual_blade_mastery` requirement says the sibling change
  "SHALL NOT replace or modify `dual_wield_style`". → The reclassification modifies *kind/target/
  cost*, not the skill's existence, effect string, or its independence from `dual_blade_mastery`;
  the archived change's intent (don't fold the stance into the mastery skill) is preserved. The
  delta spec is ADDED, and the sync step will add it as a new requirement alongside the existing
  ones without altering `dual-blade-mastery-exists-as-a-higher-tier-sibling-to-dual-wield-style`.
- [Risk] Some presentation surface might render a PASSIVE skill's target/cost. → Verified: no
  `web/` code reads `SkillKind`; the combat-session menu asserts the listed skill is ACTIVE
  (`test_combat_session.py:95`); status display renders rule-table conditions, not skill cost.

## Migration Plan

None. Registry data is mirrored idempotently at startup; stored `skills` attributes are
bucket-agnostic for ownership reads and the cast gate rejects on kind regardless of bucket. No
schema, command, or doc changes; no released users.

## Open Questions

None.
