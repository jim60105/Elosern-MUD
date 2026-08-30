# freeform-casting Specification

## Purpose

Proportional ("freeform") casting for element mastery holders: a closed, load-validated scale set multiplies the MP cost and damage/heal magnitude of the element’s scalable spells, gated at the resolver’s ownership step by direct mastery ownership, with preview, WebClient panel, and text-command support.

## Requirements

### Requirement: The freeform scale table is a fixed, load-validated closed set
`world/rules/rulebook/progression.yaml` SHALL define `freeform_cast_scales` as exactly five entries
scaled `0.25`, `0.5`, `1.0`, `2.0`, `4.0` with canonical labels `1/4`, `1/2`, `1`, `2`, `4` (ascending
order). Loading SHALL fail closed with a named validation error when the count, scale values, labels,
or order deviate — a missing or duplicated entry, a non-finite, non-positive, or unsorted scale, a
missing `1.0` entry, an empty label, or a duplicate label SHALL all be rejected before any use. Every
consumer (the resolver gate, the preview, the wire validator, and the text command) SHALL read this
single table; no consumer SHALL hard-code the set.

#### Scenario: The canonical table loads
- **WHEN** the rulebook is loaded with the five documented entries
- **THEN** `freeform_cast_scales` exposes ascending scales 0.25, 0.5, 1.0, 2.0, 4.0 with labels `1/4`,
  `1/2`, `1`, `2`, `4`

#### Scenario: A deviant table is rejected at load
- **WHEN** the table omits `1.0`, duplicates a scale, uses an unsorted order, a non-finite scale, an
  empty label, a count other than five, a non-canonical scale value, or a scale whose label is not
  its canonical pair
- **THEN** loading fails with a named validation error and no consumer reads a partial set

### Requirement: Scaled costs and magnitudes use deterministic round-half-away-from-zero
`world/rules/progression.py` SHALL define `scaled_mp_cost(base: int, scale: float) -> int` and
`scaled_magnitude(base: int, scale: float) -> int`, both returning `floor(base * scale + 0.5)` for
positive base and scale, with `scaled_mp_cost` additionally clamped to a minimum of `1` — a scaled
MP cost SHALL NEVER be zero, so no scale can ever produce a free cast. A non-positive base or a
non-finite or non-positive scale SHALL raise `ValueError`. The two helpers SHALL be the only place
cost and magnitude scaling is computed, so the panel, preview, command echo, and resolution can
never disagree.

#### Scenario: Half-scale of an even cost is exact
- **WHEN** `scaled_mp_cost(14, 0.5)` and `scaled_magnitude(10, 0.5)` are called
- **THEN** they return `7` and `5`

#### Scenario: Fractional results round half away from zero
- **WHEN** `scaled_mp_cost(11, 0.5)`, `scaled_magnitude(5, 0.5)`, and `scaled_mp_cost(150, 0.25)`
  are called
- **THEN** they return `6` (`5.5`), `3` (`2.5`), and `38` (`37.5`), and a second call returns the same
  values

#### Scenario: A scaled MP cost never falls below one
- **WHEN** `scaled_mp_cost(1, 0.25)` and `scaled_mp_cost(2, 0.25)` are called
- **THEN** they return `1` and `1` (`floor(0.75) == 0` is clamped to `1`; `floor(1.0) == 1`), so a
  quarter-scale cast always still costs at least 1 MP and never casts for free

#### Scenario: Whole scales are exact and rejected inputs raise
- **WHEN** `scaled_mp_cost(26, 2.0)` is called, and separately the helpers receive a zero or negative
  base, a NaN/infinite scale, or a zero or negative scale
- **THEN** the first call returns `52`, and each invalid call raises `ValueError`

### Requirement: is_freeform_eligible is a pure skill-shape predicate
`world/skills/cost_tiers.py` SHALL define `is_freeform_eligible(skill) -> bool` returning `True`
exactly when the skill is `ACTIVE`, carries an element, declares a positive integer `mp` cost, has a
non-empty `effects` list, and every effect prefix is one of `damage`, `heal`, or `self_heal`. Any
other shape — PASSIVE skills, non-elemental skills, skills without an `mp` cost, skills with an
empty `effects` list, or skills carrying a buff, status, cleanse, movement, or conferral effect —
SHALL return `False`. The predicate SHALL NOT read entity state.

#### Scenario: Pure damage and heal spells are eligible
- **WHEN** `is_freeform_eligible` is called for `wind_blade` (`damage:wind:magic`),
  `tornado_blade`, `sea_of_life` (`heal:area`), and `phoenix_eternal_flame`
  (`damage:fire:magic` + `self_heal`)
- **THEN** each returns `True`

#### Scenario: Buff, status, mixed, and non-spell skills are ineligible
- **WHEN** `is_freeform_eligible` is called for `gale_step` (`self_buff_apply`),
  `haste_domain` (`buff_apply`), `scorching_wave` (`damage` + `buff_apply`),
  `purify` (`cleanse`), `basic_attack` (no `mp` cost), `flight` (`PASSIVE`),
  and `dual_blade_mastery` (`sp` cost, no `mp`)
- **THEN** each returns `False`

#### Scenario: An effect-less elemental skill is ineligible
- **WHEN** `is_freeform_eligible` is called for an ACTIVE elemental skill with an `mp` cost and an
  empty `effects` list
- **THEN** it returns `False`

### Requirement: The resolver gates scaled casts at the ownership step
`ActionResolver.preflight` and `resolve` SHALL reject a cast with `RejectReason.SCALED_CAST_FORBIDDEN`
when `ActionRequest.scale != 1.0` and any of the following holds: the scale is not a member of the
`freeform_cast_scales` table; `is_freeform_eligible(skill)` is `False`; or the requested scale is not
a member of the skill-anchored `freeform_scales_for(actor, skill)` ladder set (see
`element-mastery`; mastery entitlement is anchored to the skill's own proficiency, see
`use-driven-skill-lineage`). The checks
SHALL short-circuit in exactly that order, so `skill.element` is never dereferenced for an
ineligible skill (a non-elemental or cost-less skill can never raise `AttributeError`). A request
with `scale == 1.0` SHALL bypass the check entirely and can never be rejected by it. The check
SHALL run inside the existing step-1 ownership validation, before resources or targets, and SHALL
be side-effect free in preflight.

#### Scenario: A mastery holder can scale an eligible spell
- **WHEN** `preflight` is called for `wind_blade` with `scale == 2.0` by an entity whose
  `owned_keys()` contains `wind_mastery` and whose `wind_blade` proficiency level is >= 6
- **THEN** the freeform check does not reject (other unrelated checks still apply)

#### Scenario: A rung above the current ladder tier is rejected
- **WHEN** `preflight` is called for `wind_blade` with `scale == 2.0` by a `wind_mastery` holder
  whose `wind_blade` proficiency level is 3 (rung tops at 1.0)
- **THEN** it returns `outcome == "rejected"` with `RejectReason.SCALED_CAST_FORBIDDEN`

#### Scenario: Scaling without mastery is rejected
- **WHEN** `preflight` is called for `wind_blade` with `scale == 2.0` by an entity without
  `wind_mastery` (even when its magic level would unlock the spell)
- **THEN** it returns `outcome == "rejected"` with `RejectReason.SCALED_CAST_FORBIDDEN` and no state
  changes

#### Scenario: Mastery entitles scaling of that element only
- **WHEN** `preflight` is called for `light_arrow` (an eligible `damage:light:magic` spell) with
  `scale == 2.0` by an entity owning only `wind_mastery`
- **THEN** it returns `RejectReason.SCALED_CAST_FORBIDDEN` — 風之主宰 never scales another element —
  while the same entity casting `wind_blade` at `scale == 2.0` passes the freeform gate

#### Scenario: Scaling an ineligible spell is rejected even with mastery
- **WHEN** `preflight` is called for `gale_step` with `scale == 2.0` by an entity owning
  `wind_mastery`
- **THEN** it returns `RejectReason.SCALED_CAST_FORBIDDEN`

#### Scenario: A non-elemental skill with an MP cost never crashes the gate
- **WHEN** `preflight` is called for `concentration` (`mp == 5`, `element is None`) with
  `scale == 2.0` by any entity
- **THEN** it returns `RejectReason.SCALED_CAST_FORBIDDEN` without dereferencing a missing element,
  and no exception escapes

#### Scenario: An SP-only elemental skill is not scalable
- **WHEN** `preflight` is called for `dual_blade_mastery` (element `dark`, `sp` cost only, no `mp`)
  with `scale == 2.0` by a `dark_mastery` holder
- **THEN** it returns `RejectReason.SCALED_CAST_FORBIDDEN` and SP is never deducted

#### Scenario: A non-member scale is rejected
- **WHEN** `preflight` is called for an eligible spell with `scale == 3.0` (not in the table) by a
  mastery holder
- **THEN** it returns `RejectReason.SCALED_CAST_FORBIDDEN`

#### Scenario: Scale one is always permitted
- **WHEN** `preflight` is called with `scale == 1.0` for any owned skill, including non-elemental,
  buff, and mixed-effect spells, by any entity
- **THEN** the freeform check never rejects (other unrelated checks still apply)

### Requirement: A scaled cast deducts scaled MP and applies scaled magnitudes atomically
For a successful cast with `scale != 1.0`, the resource steps SHALL compute the scaled cost in one
shared read: `_adjusted_costs(actor, skill, scale)` applies the ordinary bundle cost adjustments to
the unscaled base amounts first, then replaces the `mp` amount with `scaled_mp_cost(base, scale)`
(other resource keys keep their unscaled amounts), and both step 2 and step 6 SHALL consume that
same function with the request's scale so preflight and deduction can never drift. The `damage`,
`heal`, and `self_heal` handlers SHALL stage magnitudes computed as
`scaled_magnitude(base_amount, scale)`, with `damage` clamped to at least the existing
`combat.yaml` damage floor (the floor itself SHALL NOT be scaled). The scaled `mp` cost SHALL
satisfy the same minimum as the helper contract — never below `1` MP, so no scale combination can
produce a free cast. A scaled cost that exceeds the
actor's current MP SHALL reject with the ordinary `RejectReason.INSUFFICIENT_RESOURCE` in both
preflight and final resolution. Scaled amounts SHALL appear in the ordinary `resource_spend`,
`damage`, and `heal` EventLog entries — no log schema change. Defeat, knockout, kill-XP, and
practice staging SHALL observe the scaled amounts exactly as they observe unscaled ones.

#### Scenario: Half-scale wind blade deducts half MP and deals half damage
- **WHEN** `resolve()` succeeds for `wind_blade` (`mp == 14`) at `scale == 0.5` against a living
  target and the damage roll computes an unscaled amount of `12`
- **THEN** the actor's MP decreases by exactly `7`, the `damage` entry reports `6`, and the target's
  HP decreases by `6`

#### Scenario: Double-scale cast deducts double MP
- **WHEN** `resolve()` succeeds for `tornado_blade` (`mp == 26`) at `scale == 2.0`
- **THEN** the actor's MP decreases by exactly `52`

#### Scenario: An unaffordable scaled cost rejects without any effect
- **WHEN** `resolve()` is called for a 150-MP 主宰 spell at `scale == 4.0` by an actor with a 200-MP
  pool (scaled cost 600)
- **THEN** it returns `RejectReason.INSUFFICIENT_RESOURCE`, and HP, MP, buffs, and logs are unchanged

#### Scenario: Scaled damage obeys the floor and defeat rules
- **WHEN** a scaled hit's `scaled_magnitude` result is below the `combat.yaml` damage floor, and
  separately a scaled lethal hit crosses a living monster from positive HP to zero
- **THEN** the first stages at least the floor amount, and the second emits exactly one
  `target_defeated` entry and one kill-XP award, exactly as an unscaled lethal hit would

#### Scenario: Scaled healing respects the maximum and knockout rules
- **WHEN** `sea_of_life` is cast at `scale == 2.0` and its doubled magnitude would exceed a target's
  maximum HP
- **THEN** the target is restored to its maximum only, the `heal` entry reports the actually applied
  amount, and an entity at zero HP is not revived

### Requirement: Preview and the combat facade accept and revalidate scale
`preview_skill(actor, skill_key, context, candidates, scale=1.0)` and
`revalidate_submission(actor, skill_key, context, targets, scale=1.0)` SHALL apply the same
step-1 scale gate and the scaled resource check, (the ladder set re-derived from the actor's current proficiency) so a disabled or
tampered scaled submission reports the matching stable reason before initiative. `submit_player_action(actor, skill_key,
targets_or_shorthand, scale=1.0)` SHALL thread the scale into the preview, preflight, and the
`ActionRequest` of the resolved round. All three SHALL treat `scale == 1.0` as the current behavior.

#### Scenario: Preview reports scaled resource availability
- **WHEN** `preview_skill` is called for `wind_blade` at `scale == 4.0` by a mastery holder with
  `14 * 4 == 56` MP available but less than the unscaled check would require
- **THEN** the preview is enabled when the actor has at least 56 MP and disabled with
  `INSUFFICIENT_RESOURCE` when it has fewer

#### Scenario: The facade resolves a scaled combat cast
- **WHEN** `submit_player_action(actor, "wind_blade", "all-enemies", scale=2.0)` is called in an
  active session by a `wind_mastery` holder
- **THEN** one ordinary round resolves with the scaled MP deduction and scaled damage
- **AND** a modified client submitting `scale=3.0` is rejected before initiative with
  `SCALED_CAST_FORBIDDEN` and no round or world time is consumed

### Requirement: The text cast command accepts a scale token
`cast` SHALL accept the syntax `cast <skill_key>[@<scale>][=<target_key>]` in and out of combat,
where `<scale>` is one of the canonical table labels (`1/4`, `1/2`, `1`, `2`, `4`) and defaults to
`1`. The scale SHALL be threaded into the combat-session facade and the out-of-combat settlement
path. A non-label token or a token applied to a spell the actor cannot scale (no mastery
entitlement, or a rung above the skill's proficiency ladder) SHALL reject with the stable
`SCALED_CAST_FORBIDDEN` rejection message (a Traditional Chinese explanation), with no MP change
and no world-time advance.

#### Scenario: A scaled combat cast via the text command
- **WHEN** a `wind_mastery` holder types `cast wind_blade@2=wolf` in an active session
- **THEN** the round resolves `wind_blade` at `scale == 2.0` (28 MP deducted)

#### Scenario: A scaled out-of-combat cast via the text command
- **WHEN** a `wind_mastery` holder types `cast wind_blade@1/2=<target>` out of combat (skill keys are
  the registry keys; labels are never accepted as skill keys), with the skill's
  `usable_out_of_combat` flag set by the test fixture (no catalog spell usable out of combat is
  magnitude-scalable today, so the fixture supplies the flag deterministically without changing
  the registry)
- **THEN** the cast resolves at `scale == 0.5` (7 MP deducted) and the ordinary command-time charge
  applies

#### Scenario: An invalid scale token or unauthorized scale rejects cleanly
- **WHEN** a player types `cast wind_blade@3`, or `cast wind_blade@2` without `wind_mastery` or at a
  proficiency level whose rung tops below 2.0, or `cast gale_step@2` with `wind_mastery`
- **THEN** each is rejected with the `SCALED_CAST_FORBIDDEN` message, no MP is deducted, no effect
  applies, and no world time advances
