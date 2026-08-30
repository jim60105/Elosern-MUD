## MODIFIED Requirements

### Requirement: The combat panel hides freeform casting from non-masters
A skill descriptor SHALL include a `freeform_scales` array only when the skill is
`is_freeform_eligible` and the skill-anchored `freeform_scales_for(actor, skill)` ladder set is
non-empty (mastery entitlement anchored to the CAST skill's own proficiency — the array lists
exactly the rungs the actor's proficiency in that skill unlocks). The array SHALL be strictly
ascending, exactly one entry
per allowed scale, each entry an exact object containing the numeric `scale`, the canonical label of that scale
(`1/4`, `1/2`, `1`, `2`, `4` — a label never pairs with any other scale), and the server-computed
scaled `mp_cost` (via `scaled_mp_cost`, so the browser never performs rounding). Every other
skill — including eligible spells of a non-master — SHALL omit the field
entirely. The feature is deliberately a surprise: a player without the element's mastery SHALL see
no scale selector, no freeform text, and no other indication that scaling exists in any rendered
panel.

#### Scenario: A master's eligible spells advertise their unlocked scales
- **WHEN** a `wind_mastery` holder whose `wind_blade` proficiency reaches level 10 has its combat
  panel built
- **THEN** `wind_blade` carries `freeform_scales` with exactly the five entries in ascending order
  (e.g. `{scale: 0.25, label: "1/4", mp_cost: 4}`, `{scale: 0.5, label: "1/2", mp_cost: 7}`,
  `{scale: 1.0, label: "1", mp_cost: 14}`, `{scale: 2.0, label: "2", mp_cost: 28}`,
  `{scale: 4.0, label: "4", mp_cost: 56}`) and `gale_step` (ineligible) omits it

#### Scenario: A non-master's panel reveals nothing
- **WHEN** an entity without `wind_mastery` (even one with a magic level unlocking the spells) sees
  its combat panel
- **THEN** no skill descriptor contains a `freeform_scales` field, and no rendered text mentions
  scales, magnitudes, or proportional casting

### Requirement: The combat dock offers a scale-choice step only for masters
When the focused skill carries `freeform_scales`, the keyboard dock SHALL insert one 威力-choice
menu between skill selection and target selection, listing exactly the entries the actor's current
ladder unlocks (label plus scaled `mp_cost`) in ascending order with `1` preselected, and SHALL include the chosen numeric `scale` in the
eventual cast payload for every target form (NONE, SELF, SINGLE, and AREA, including shorthands).
Arrow keys SHALL navigate, Enter SHALL confirm the choice and open the target flow, and Escape SHALL
pop back to the skill list. The chosen scale SHALL live in the same client-local selection state the
dock already rebuilds after a panel replacement: a still-valid choice is preserved, and an
invalidation resets deterministically to `1`. A skill without `freeform_scales` SHALL skip the step
entirely, so the flow and payload for every existing skill are byte-identical to today.

#### Scenario: A master picks double power for a single-target spell
- **WHEN** the player focuses `wind_blade`, chooses 威力 `2` in the scale menu, then confirms one
  target
- **THEN** the browser submits `combat.cast` with `skill_key`, `scale: 2.0`, and the chosen
  `target_ids`, and the command echo labels the cast with the chosen magnitude

#### Scenario: A scaled AREA cast keeps the shorthand form
- **WHEN** the player chooses scale `1/2` and then the `all-enemies` shorthand for an eligible AREA
  spell
- **THEN** one request carries `skill_key`, `scale: 0.5`, and `target_shorthand: "all-enemies"` and
  no target-ID field

#### Scenario: Non-masters keep today's exact flow
- **WHEN** any player focuses any skill that lacks `freeform_scales`
- **THEN** no scale step appears, and the emitted payload contains no `scale` field, identical to
  the pre-change payloads
