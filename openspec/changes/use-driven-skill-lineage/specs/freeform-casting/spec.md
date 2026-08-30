## MODIFIED Requirements

### Requirement: The resolver gates scaled casts at the ownership step
`ActionResolver.preflight` and `resolve` SHALL reject a cast with `RejectReason.SCALED_CAST_FORBIDDEN`
when `ActionRequest.scale != 1.0` and any of the following holds: the scale is not a member of the
`freeform_cast_scales` table; `is_freeform_eligible(skill)` is `False`; or the requested scale is not a member of the actor's ladder-derived
`freeform_scales_for(actor, skill.element.key)` set (mastery entitlement anchored to the
skill's own proficiency; see `use-driven-skill-lineage`). The checks
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
