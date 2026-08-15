## ADDED Requirements

### Requirement: combat.cast payload carries an optional bounded scale
The `combat.cast` payload validator SHALL accept an optional `scale` field alongside `skill_key`,
`target_ids`, and `target_shorthand`. The value SHALL be a JSON number exactly equal to one member of
the `freeform_cast_scales` table (`0.25`, `0.5`, `1.0`, `2.0`, `4.0`); a boolean, a non-number, or a
non-member number SHALL be rejected as `malformed_payload` without adapter invocation. An absent
field SHALL default to `1.0`. The field MAY accompany every target form (NONE, SELF, SINGLE, and
AREA, including shorthands). The adapter SHALL thread the validated scale into
`revalidate_submission` and `submit_player_action`, so a scale the deterministic gate forbids is
rejected before initiative with the stable `SCALED_CAST_FORBIDDEN` code.

#### Scenario: A member scale is accepted on every target form
- **WHEN** a client submits `combat.cast` with `scale: 2.0` together with an explicit SINGLE
  `target_ids` list, and separately with an AREA `target_shorthand`
- **THEN** both payloads pass validation and the adapter revalidates and resolves the cast at
  `scale == 2.0`

#### Scenario: A non-member scale is rejected as malformed
- **WHEN** a client submits `scale: 3.0`, `scale: "2"`, or `scale: true`
- **THEN** the payload is rejected with `malformed_payload` and no adapter runs

#### Scenario: An absent scale defaults to one
- **WHEN** a client submits a valid `combat.cast` without a `scale` field
- **THEN** the adapter behaves exactly as before this change (`scale == 1.0`)
