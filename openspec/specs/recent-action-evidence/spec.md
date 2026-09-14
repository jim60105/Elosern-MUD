# recent-action-evidence Specification

## Purpose
Expose bounded recent committed action evidence for deterministic conditional spells, independent of prose, affinity and settlement mode.

## Requirements

### Requirement: Recent evidence is committed on the actor and expires in world time
The system SHALL record a bounded forced-interaction evidence entry on the acting perpetrator only for a committed resistance outcome whose resisted and auto_comply fields are both false. Direct, NPC, combat and field action paths SHALL agree. The light duration SHALL be 60 world seconds with an exclusive expiry boundary; repeated incidents SHALL refresh expiry rather than multiply severity. Queries SHALL not mutate state, and rollback SHALL restore evidence along with the action.

#### Scenario: Qualifying outcome belongs to the perpetrator
- **WHEN** a forced outcome commits against a target
- **THEN** the actor qualifies during the window, not the target; no affinity record is required

#### Scenario: Nonqualifying and aborted outcomes do not mark
- **WHEN** the outcome is resisted, automatic compliance, or the action rolls back
- **THEN** no new evidence survives

#### Scenario: Exact expiry and refresh
- **WHEN** a later incident refreshes a stored entry and world time reaches its new expiry
- **THEN** the entry is inactive exactly at expiry and never increases strike count

#### Scenario: No narrative authority
- **WHEN** a narrative or client context accuses a target of wrongdoing
- **THEN** no evidence is created

#### Scenario: A force-through contact spell marks its caster
- **WHEN** a generic contact spell with a resistible interaction policy (for example a sacramental kiss or milk cast) commits a force-through outcome against a non-actor target
- **THEN** the cast's standard coercion outcome records forced-interaction evidence on the caster exactly like a catalog sexual act's force-through, making the caster a penance-eligible target within the window
