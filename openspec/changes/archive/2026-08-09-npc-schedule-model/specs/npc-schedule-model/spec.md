# NPC Schedule Model

## Purpose

Define the deterministic NPC schedule data contract: immutable role templates,
per-NPC storage shapes, validation, and startup synchronization. This capability
covers the data only — settlement, movement, and interaction gating are owned by
the `npc-schedule-runtime` capability.

## ADDED Requirements

### Requirement: Role templates are immutable rulebook data with a fixed entry shape

`world/rules/rulebook/npc_schedules.yaml` SHALL declare `schema_version: 1` and a
`templates:` mapping of role templates. Each template SHALL be a mapping carrying an `entries`
list of exactly `{tick_offset, kind}` entries plus per-kind required fields: a `move` entry SHALL
carry a `target` and SHALL NOT carry `state`; a `state` entry SHALL carry a `state` value and
SHALL NOT carry a `target`. `tick_offset` SHALL be a non-negative integer strictly below the
world day's seconds (resolved through the existing clock day math), and entries SHALL repeat
every world day. A template MAY declare an optional `default_state` from the bounded state
vocabulary; a successful `move` settlement writes that value, and `default_state` SHALL NOT be
settable on individual entries. The declared state vocabulary for `state` SHALL be bounded and
documented in the rulebook.

#### Scenario: The shipped rulebook loads and validates
- **WHEN** the `npc_schedules.yaml` rulebook is loaded by the validator
- **THEN** it declares `schema_version: 1`, contains at least one role template, and every entry
  validates under the entry shape rules

#### Scenario: A move entry requires a target and forbids state
- **WHEN** a template entry has `kind: move` and a `state` field, or lacks `target`
- **THEN** validation rejects it with a named error

#### Scenario: A state entry requires a state and forbids target
- **WHEN** a template entry has `kind: state` and a `target` field, or lacks `state`
- **THEN** validation rejects it with a named error

#### Scenario: A template default_state validates against the vocabulary
- **WHEN** a template declares `default_state` inside the bounded vocabulary
- **THEN** validation accepts it as the value a successful `move` settlement writes

#### Scenario: An out-of-vocabulary default_state is rejected
- **WHEN** a template declares a `default_state` outside the bounded vocabulary
- **THEN** validation rejects the template with a named error

#### Scenario: An out-of-day tick_offset is rejected
- **WHEN** an entry's `tick_offset` equals or exceeds the world day's seconds, or is negative
- **THEN** validation rejects it with a named error

#### Scenario: Unknown template keys are rejected
- **WHEN** an NPC references a template key absent from the rulebook
- **THEN** validation rejects the reference with a named error

### Requirement: Per-NPC schedules are assigned through one validated API and stored in exactly
two validated shapes

`world/rules/npc_schedules.py` SHALL provide `set_npc_schedule(npc, schedule)` as the sole writer
of `npc.db.schedule`. The API SHALL accept exactly two shapes: a template reference
(`{"schema_version": 1, "template": <key>, "overrides": {...}}`) or a full custom list
(`{"schema_version": 1, "entries": [...]}`). A `None` value SHALL mean "no schedule". Any other
shape — missing schema_version, both `template` and `entries` present, non-dict storage,
entry counts beyond the bound — SHALL be rejected with a named error. The API SHALL
record `effective_from_tick` (the current world tick at assignment) and SHALL maintain a
persistent `schedule` tag on the NPC so settlement can find it regardless of when it was spawned
or reassigned. Consumers reading a stored `db.schedule` SHALL validate it with the same parser;
a malformed stored value resolves to "no schedule".

#### Scenario: A template reference with valid overrides parses
- **WHEN** an NPC is assigned `{"schema_version": 1, "template": "guard", "overrides": {"1": {...}}}`
  and the template and overrides validate
- **THEN** the parsed schedule resolves the template's entries with the override applied, the
  schedule tag is present on the NPC, and `effective_from_tick` equals the assignment tick

#### Scenario: A full custom list parses
- **WHEN** an NPC is assigned `{"schema_version": 1, "entries": [...]}` and every entry validates
- **THEN** the parsed schedule returns exactly those entries and the NPC carries the schedule tag

#### Scenario: A malformed storage shape is rejected as no-schedule
- **WHEN** an NPC's `db.schedule` is a non-dict, has both `template` and `entries`, has an unknown
  `schema_version`, or references an unknown template
- **THEN** validation reports a named error and the schedule resolves to "no schedule"

#### Scenario: An override referencing a missing entry index is rejected
- **WHEN** an override key does not correspond to an entry index of the referenced template
- **THEN** validation rejects the reference with a named error

#### Scenario: A stored schedule missing its recorded effective tick is malformed
- **WHEN** an NPC's `db.schedule` is a valid template reference or custom list but
  `db.schedule_effective_from_tick` is missing or not an integer
- **THEN** the consumer parser resolves the schedule to "no schedule" and startup sync degrades
  it like any other malformed stored value

#### Scenario: Clearing a schedule removes the tag
- **WHEN** `set_npc_schedule(npc, None)` is called on a previously scheduled NPC
- **THEN** `db.schedule` is `None` and the schedule tag is removed

### Requirement: Schedule state is a declared attribute contract

`npc.db.schedule_state` SHALL be the single runtime-state attribute holding the NPC's current
schedule state value or `None` when no state is active. This change SHALL declare the contract and
SHALL NOT write it; the `npc-schedule-runtime` capability owns every write.

#### Scenario: The attribute contract is declared without a writer
- **WHEN** the model's public surface is inspected
- **THEN** it documents `npc.db.schedule_state` (value or `None`) and contains no code path that
  assigns it

### Requirement: Startup synchronization is idempotent and degrades safely

A startup pass SHALL load and validate the rulebook, confirm every NPC's stored schedule shape,
and confirm the persistent `schedule` tag on every schedule-bearing NPC so settlement finds them.
A validation failure for one NPC SHALL log a bounded diagnostic and treat that NPC as having no
schedule; the pass SHALL NOT block startup and SHALL be safe to re-run (idempotent — repeated
runs produce no duplicate state or errors).

#### Scenario: Startup sync validates and confirms schedules
- **WHEN** the startup pass runs over NPCs with valid template references and valid custom lists
- **THEN** their parsed schedules are confirmed, every schedule-bearing NPC carries the schedule
  tag, and no errors are reported

#### Scenario: A broken NPC schedule degrades without blocking startup
- **WHEN** one NPC's stored schedule is malformed and another's is valid
- **THEN** the pass logs a bounded diagnostic for the broken NPC, treats it as having no schedule,
  and completes startup with the valid NPC's schedule available

#### Scenario: Re-running sync is a no-op for already-valid schedules
- **WHEN** the startup pass runs twice over the same valid data
- **THEN** the second run produces no new errors and the schedules remain identical
