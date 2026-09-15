# mp-state-feedback Specification

## Purpose
Define the canonical MP-change writer, its exactly-once mp_zero outcome reaction dispatch with source attribution on positive-to-zero decrease crossings, shared-source routing across cast costs, buff rate ticks and transfers, and rule-layer source filtering.

## Requirements

### Requirement: Every authored MP decrease flows through one canonical writer returning the actual change
The rules layer SHALL provide one canonical MP-change writer that every authored MP mutation — spell-effect drain/restore, buff rate ticks, cast-cost payment and all future MP transfer effects — routes through rather than writing the gauge directly. The writer SHALL clamp to the gauge's own bounds, return the actual signed change applied, and treat a clamped no-op as an actual change of zero. No production MP-decrease site may bypass it; adding an MP writer beside it SHALL be treated as a contract violation found by the enumeration the implementation performs over every gauge-mp write site.

#### Scenario: Diverse sources share the writer
- **WHEN** a synthetic cast effect, a buff rate tick with an mp-target and a routed cast cost each decrease MP
- **THEN** each produces its clamped actual delta through the writer and no site mutates the stored gauge outside it

#### Scenario: Clamped decrease reports the real amount
- **WHEN** a decrease larger than the stored MP is applied through the writer
- **THEN** MP lands at its floor, the returned actual change equals only the previously available amount, and the depletion outcome below sees a positive actual loss

#### Scenario: Increases route without depletion semantics
- **WHEN** a positive change is applied through the writer near or above the gauge maximum
- **THEN** MP clamps at its maximum and no depletion outcome event is dispatched

### Requirement: MP reaching zero via a decrease dispatches one attributed outcome event exactly once
The canonical writer SHALL dispatch exactly one `mp_zero` outcome reaction each time stored MP crosses from positive to zero **via a decrease**, carrying the event's source skill (when authored) and source tier, falling back to the configured first tier for unattributed sources. A change that finds MP already at zero, an increase, a clamped zero-actual decrease, and an hp-target change SHALL never dispatch it. The event SHALL ride the existing outcome-reaction dispatch path so all rules sharing the event vocabulary see it.

#### Scenario: Crossing fires once with attribution
- **WHEN** an attributed decrease takes stored MP from a positive value to exactly zero
- **THEN** one `mp_zero` event is dispatched carrying the authored source skill and tier

#### Scenario: Already zero and healed-then-zero are distinct
- **WHEN** a decrease fires against MP already at zero, and separately MP is restored and later drained to zero again
- **THEN** the already-zero decrease dispatches nothing, while the later renewed crossing dispatches exactly one event

#### Scenario: Tier fallback matches the hp-loss convention
- **WHEN** an unattributed MP decrease (e.g. an environment-style writer) causes the crossing
- **THEN** the event carries the configured first-tier fallback rather than no tier

### Requirement: Depletion rules filter the event's source at the rule layer, never by suppressing dispatch
The state-reaction vocabulary SHALL gain exactly one closed `when` key qualifying which authored source skill an outcome event must name for the rule to match, evaluated fail-closed (missing source, unknown skill, unloaded entity skills, or non-string value never match) and load-time rejected on rules without an event condition. Rules SHALL share this key with the outcome event vocabulary. Suppression of the event itself by the writer based on listeners, sources, or element SHALL be impossible: every qualified rule — including synthetic alternate-element ones — reacts to the same dispatched fact.

#### Scenario: Qualified rule reacts and unqualified sources do not
- **WHEN** a synthetic depletion event names the skill one reaction rule qualifies and, separately, a different source drains MP to zero
- **THEN** the qualified rule's then-action applies once, and the unqualified crossing dispatches the same event but changes no buff

#### Scenario: Unknown or missing event sources fail closed
- **WHEN** the qualifying rule evaluates against an event with no source or an unknown skill key
- **THEN** the rule does not match and loading a rule row that names a malformed qualifier fails closed

#### Scenario: Reaction cascades stay in the initiating transaction
- **WHEN** a matching reaction applies its marker inside a cast, buff tick, or clock advance whose transaction later fails
- **THEN** MP, the reaction-applied marker and every transitive surface restore with the initiating settlement

### Requirement: Cast-cost payment is a routed write on the staged deduction
The resource-deduction step SHALL route the `mp` resource through the canonical writer inside its already-staged pending effect, carrying the cast skill as the event source, while hp and sp deduction behavior stays unchanged. The staged check/deduction amount agreement (preflight, recheck, commit) SHALL be preserved, and an MP crossing caused by paying a cast cost SHALL dispatch the same attributed event as any other decrease.

#### Scenario: A final cast payment to zero is an ordinary attributed crossing
- **WHEN** a paid cast consumes the caster's entire remaining MP
- **THEN** the deduction commits through the writer and one `mp_zero` event with the cast skill as source is visible to qualifying rules

#### Scenario: Rejection leaves no partial payment and no event
- **WHEN** the deduction recheck fails after preflight passed
- **THEN** no MP changed, no event dispatched, and the whole action rolls back atomically

### Requirement: Buff engine mp-target ticks route through the writer with persisted attribution
The buff engine's rate-tick path SHALL apply an mp-target delta through the canonical writer, persisting the grant-time source attribution (source identity and source tier already carried in the buff cache) into the dispatched event, and SHALL keep the hp-target `hp_loss` dispatch, the documented no-op pull target, and recovery-profile behavior byte-for-byte unchanged. A refresh of an existing damaging MP buff SHALL not create a new-instance or new-crossing event beyond the actual crossing.

#### Scenario: A tiered MP drain ticks, attributes, and can deplete
- **WHEN** a synthetic mp-target DoT buff applied by a source-bearing cast ticks MP from positive to zero across successive intervals
- **THEN** each tick routes through the writer with the persisted grant-time source skill and tier, and the crossing tick alone dispatches `mp_zero`

#### Scenario: HP DoT behavior is untouched
- **WHEN** an hp-target damaging buff ticks
- **THEN** it still dispatches `hp_loss` exactly as before and never an mp event

#### Scenario: Immune targets never accumulate the drain
- **WHEN** a worn-equipment-immune target would receive a new mp-target damaging buff instance
- **THEN** the grant is neutralized as with any debuff and no writer call occurs from a nonexistent tick
