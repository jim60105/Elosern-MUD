# Spec Delta

## MODIFIED Requirements

### Requirement: The cast command reference documents the optional scale token
The reference entry for `cast` SHALL document the syntax `cast <skill_key>[@<scale>][=<target_key>] [由 <成員>]`
where `<scale>` is one of `1/4`, `1/2`, `1`, `2`, `4` (default `1`) and SHALL state that the token
adjusts the spell's MP cost and damage/heal magnitude proportionally, available only to holders of
the matching element's mastery skill (all other uses are rejected).

#### Scenario: The reference matches the manifest
- **WHEN** the drift contract test inspects the `cast` entry
- **THEN** the reference syntax row equals the manifest syntax
  `cast <skill_key>[@<scale>][=<target_key>] [由 <成員>]` and the description mentions the proportional
  magnitude adjustment, the mastery requirement, and that `由 <成員>` names the caster

#### Scenario: The overview describes scaled casting
- **WHEN** a player opens `docs/game/commands.md`
- **THEN** the cast row states that a mastery holder may adjust a spell's power and MP cost with the
  `@<scale>` token

#### Scenario: The manifest and overview carry the scale token

- **WHEN** the scale-token capability is documented
- **THEN** the curated manifest in `tests/test_command_docs.py` SHALL carry the same syntax
- **AND** `docs/game/commands.md` SHALL describe the capability in its cast row
