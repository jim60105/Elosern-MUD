# Spec Delta

## MODIFIED Requirements

### Requirement: The opening cast charges combat time, never command time
A field opening SHALL accumulate as a normal combat round with no command-time charge and SHALL settle once through the unpaid combat interval at terminal outcome or real incapacitated-hostile continuation.

#### Scenario: An opening cast advances no command time
- **WHEN** a field initiation resolves one opening round without ending the fight
- **THEN** no `AdvanceSource.COMMAND` advance occurs for that cast, and the opening round remains unpaid until terminal settlement or an actual incapacitated-hostile continuation pays its prefix

#### Scenario: Combat time settles once at the terminal outcome
- **WHEN** a field initiation's fight concludes
- **THEN** the combat clock charges only the remaining unpaid interval, lifetime combat time totals all completed rounds once and no command-time charge is attributable to the opening cast
