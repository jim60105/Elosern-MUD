## MODIFIED Requirements

### Requirement: The possession controls complete the action round-trip
`explore.possess` SHALL resolve through the deterministic entry gates of
`world/rules/possession.py`, surfacing each gate reason as outcome `rejected` with the gate's
stable code and fixed line, and `explore.possess_release` SHALL call the rules release; success
results SHALL be followed by the full presentation update that carries the re-pointed actor and
banner.

#### Scenario: A gated possess attempt round-trips the gate
- **WHEN** a client dispatches `explore.possess` for a companion failing the co-location gate
- **THEN** the result is rejected with the gate's code and line and no state changes

#### Scenario: Success pushes the new keying
- **WHEN** a possess dispatch succeeds
- **THEN** the client receives the action result followed by a snapshot carrying the banner and
  the possessed actor's panels

#### Scenario: Possession controls never suggested
- **WHEN** the exploration vocabulary or any card surface is computed
- **THEN** `explore.possess`/`explore.possess_release` appear only as the companion's own interact affordances and never in a proposal list, and no suggestion eligibility set exists to consult
