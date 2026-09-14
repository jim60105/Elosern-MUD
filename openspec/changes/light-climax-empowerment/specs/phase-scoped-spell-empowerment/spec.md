## Purpose

Define reusable actor-bound peak effects and qualified phase-scoped spell benefits without replacing canonical transitions, action locks or transaction boundaries.

## ADDED Requirements

### Requirement: Peak effects bind declared recipients and retain action locks
A declared peak effect SHALL advance its configured recipients through the canonical positive-gain then zero-gain path to the in-progress phase, without directly assigning phase or creating an artificial extension. An actor already action-locked SHALL remain unable to cast. An actor-bound peak combined with selected-target healing SHALL affect the caster once independently of selected recipients. Existing target-only divine effects SHALL keep excluding the actor.

#### Scenario: Emergency recovery locks only its caster
- **WHEN** an action-capable caster uses a synthetic selected-heal plus self-peak spell
- **THEN** selected targets recover HP, the caster enters in-progress and its subsequent action is locked

#### Scenario: Approaching phase does not gain a fabricated extension
- **WHEN** the caster starts at the approaching phase and peak resolves
- **THEN** it enters in-progress once without counting the following zero-gain call as extension stimulus

#### Scenario: Already locked cannot cast
- **WHEN** an in-progress caster attempts the emergency spell
- **THEN** the ordinary action gate rejects before MP or healing changes

### Requirement: Qualified phase entry grants a persistent cycle-scoped benefit
An authored reaction SHALL activate a marker only when its owner is already qualified by ownership and prerequisites at a successful configured phase entry. It SHALL not fire on invalid/no-op edges or retroactively on mid-cycle acquisition. The marker SHALL survive the afterglow phase and reload, end on return to the neutral phase, and cease conferring benefits immediately if qualification is lost. All canonical transition sources SHALL share this behavior.

#### Scenario: Canonical sources agree
- **WHEN** a qualified actor enters in-progress through a rule event or a canonical pleasure gain
- **THEN** the same marker is activated once

#### Scenario: Afterglow retains benefit without retaining action lock
- **WHEN** the actor transitions from in-progress to afterglow and then neutral
- **THEN** ordinary afterglow actions resume while the marker remains, and neutral removes it

#### Scenario: Acquisition is not retroactive
- **WHEN** ownership is acquired after the phase entry
- **THEN** no marker appears until a later qualifying entry

### Requirement: Empowerment selects configured maxima without bypassing conditions
A marker-qualified state magnitude SHALL select its declared maximum rather than adding another multiplier. Fixed magnitudes and ordinary costs SHALL remain fixed. Cast conditions, resistance and action locks SHALL remain independent. Failure anywhere in the initiating transaction SHALL restore phase, markers, effects and all indirect state.

#### Scenario: Max state magnitude is bounded
- **WHEN** an empowered synthetic spell uses a state curve and a separate fixed heal component
- **THEN** only the curve selects its configured maximum and the fixed magnitude stays unchanged

#### Scenario: Empowerment does not satisfy cast prerequisites
- **WHEN** the marker is active but a target condition or action capability is unmet
- **THEN** the action is rejected normally

#### Scenario: Rollback includes reactions
- **WHEN** a later action/clock operation fails after a transition applies a marker
- **THEN** the marker, phase, counters, HP and resources are restored
