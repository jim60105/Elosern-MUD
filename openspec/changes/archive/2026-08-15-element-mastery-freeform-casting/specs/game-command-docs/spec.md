## ADDED Requirements

### Requirement: The cast command reference documents the optional scale token
The reference entry for `cast` SHALL document the syntax `cast <skill_key>[@<scale>][=<target_key>]`
where `<scale>` is one of `1/4`, `1/2`, `1`, `2`, `4` (default `1`) and SHALL state that the token
adjusts the spell's MP cost and damage/heal magnitude proportionally, available only to holders of
the matching element's mastery skill (all other uses are rejected). The curated manifest in
`tests/test_command_docs.py` SHALL carry the same syntax, and `docs/game/commands.md` SHALL describe
the capability in its cast row.

#### Scenario: The reference matches the manifest
- **WHEN** the drift contract test inspects the `cast` entry
- **THEN** the reference syntax row equals the manifest syntax
  `cast <skill_key>[@<scale>][=<target_key>]` and the description mentions the proportional
  magnitude adjustment and the mastery requirement

#### Scenario: The overview describes scaled casting
- **WHEN** a player opens `docs/game/commands.md`
- **THEN** the cast row states that a mastery holder may adjust a spell's power and MP cost with the
  `@<scale>` token
