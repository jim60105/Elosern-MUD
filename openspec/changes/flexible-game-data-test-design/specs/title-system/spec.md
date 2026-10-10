# Spec Delta

## MODIFIED Requirements

### Requirement: The clergy title ladder unlocks by redeemed count and never displays 聖女
The fixed-title registry SHALL carry a five-row clergy ladder in the 聖職 category, one row per rung (虔信者／修女／神官／主教／樞機), each row's predicate a `church_skills_redeemed` integer threshold. The five thresholds are tuning placeholders (strictly ascending authored values without a duplicate threshold table). NO other system may use these titles as a prerequisite.

#### Scenario: Each rung unlocks exactly at its count
- **WHEN** a character's redeemed count crosses each ladder threshold (exactly at, and one below)
- **THEN** the matching title is banked with the fixed slot auto-equipped at the threshold and remains locked one below it

#### Scenario: The 聖女 display ban is a global registry gate
- **WHEN** a planted fixed-title row of any category contains 聖女 in its display name, key, flavor, or hint
- **THEN** registry validation rejects it, and every shipped fixed-title row ;  ladder or otherwise ;  passes the gate with non-聖女 text

#### Scenario: The ladder is display-only
- **WHEN** the codebase is searched for title state consumed as a prerequisite
- **THEN** no system gates anything on a clergy title key or display

#### Scenario: Threshold finals are recorded by the tuning task
- **WHEN** an author adjusts valid strictly ascending ladder thresholds
- **THEN** the registry alone records the values; generic ordering/reference checks and independent synthetic boundary tests pass without a duplicate scenario or expected-value table

#### Scenario: Ladder grants ride the existing machinery verbatim
- **WHEN** a clergy ladder title is earned
- **THEN** the existing fixed-title machinery applies verbatim ;  declarative predicate families, auto-unlock and auto-equip of an empty slot, and display-only value

#### Scenario: The 聖女 office stays prose
- **WHEN** the shipped registry is audited for any naming of the 聖女 office
- **THEN** no fixed-title row of ANY category displays or otherwise names it ;  the office stays prose per the saintess-vessel spec (reaffirmed, design §9)
