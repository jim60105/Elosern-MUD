# stateful-spell-casting Specification

## Purpose
Define reusable state-conditioned and contact-interaction spell behavior, sharing existing state readers, resistance outcomes and atomic action settlement.

## Requirements

### Requirement: Subject-scoped cast conditions are pure and authoritative
Spells SHALL declare validated state conditions for the actor and selected targets, with optional distinct-participant contact and target-capability requirements. Both preflight and final execution SHALL evaluate current authoritative state without materializing state handlers, random rolls or mutations. An unmet condition SHALL reject before MP, time, practice or effects. Contact SHALL use the current co-location and engagement/range model, not client attestations.

#### Scenario: A threshold failure has no effects
- **WHEN** one participant is below a configured state threshold
- **THEN** the cast rejects with no resource, time, practice, random-state or lazy-attribute changes

#### Scenario: A stale preflight cannot authorize a changed state
- **WHEN** preflight passes and state falls below threshold before execution
- **THEN** final execution rejects

#### Scenario: Contact cannot be spoofed
- **WHEN** a caller claims a ritual was completed for a self, absent, out-of-range or capability-blocked target
- **THEN** the authoritative contact policy rejects the cast

### Requirement: State-dependent effect magnitudes use canonical pre-effect inputs
A spell SHALL support bounded state-derived magnitude from an explicitly declared subject and canonical field. The magnitude SHALL replace the configured base coefficient where declared and be evaluated before this cast changes that state. Equipment-adjusted exposure SHALL be used for exposure fields. Unsupported or malformed curves SHALL fail authoring. Different elemental spells SHALL be able to reuse the same curve behavior.

#### Scenario: State is sampled before the spell changes it
- **WHEN** a synthetic alternate-element spell heals according to actor arousal and then raises arousal
- **THEN** healing uses the pre-stimulus ordinal with no repeated coefficient multiplication

#### Scenario: Equipment contributes to exposure magnitude
- **WHEN** a target stimulus bonus is configured from caster effective exposure
- **THEN** worn exposure bias affects the bonus once within the vocabulary bounds

### Requirement: Interaction stimulus and resistance settle as one action
A declared stimulus SHALL use the existing standard stimulus interval and equipment policy, with optional authored state bonus, and advance recipients through the canonical pleasure path. Random gains SHALL be selected before commit. A resisted generic contact spell SHALL charge normal MP/time but apply no healing, cleansing or stimulus to either participant and award no successful practice. A force-through outcome SHALL retain ordinary structured coercion consequences in every settlement mode. This SHALL NOT change standard sexual-act participant-credit semantics.

#### Scenario: Resisted interaction has one paid outcome
- **WHEN** a synthetic contact spell is resisted
- **THEN** one resistance outcome is recorded and one MP/time cost occurs, but participant HP, debuffs and stimulus state are unchanged

#### Scenario: Successful interaction applies once to each participant
- **WHEN** a configured both-participant stimulus succeeds
- **THEN** each distinct recipient receives one staged gain and the same cast applies its declared recovery

#### Scenario: Late error rolls back coupled state
- **WHEN** a later commit or clock operation fails after stimulus changes phase
- **THEN** HP, MP, pleasure, wetness, phase, counters and reaction buffs restore
