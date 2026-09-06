# quest-issuer-authorization Specification

## Purpose
Defines who may issue a private commission: the authority is carried exclusively by the `QuestIssuer` component, is authored — never inferred — and reaches NPCs only through the import pipeline. The capability pins the component's four-field service-host shape, the loader-level row-anchor invariant, the exactly-two-forms issuer-key resolution, batch-wide uniqueness of authored issuer keys, and the convergence-survival guarantee for person-bound commissioners.

## Requirements

### Requirement: Authority to issue a private commission is authored, never inferred

The right to issue a private commission SHALL be carried exclusively by the `QuestIssuer` component
declared in `typeclasses/components.py` and registered in the closed profession component
vocabulary. No other property of an entity — its display name, its typeclass, its other components,
its location, its schedule, its dialogue authorship, or the mere fact that it has a database
identity — SHALL confer that authority. An entity without the component SHALL NOT be able to issue,
and SHALL NOT resolve to, any issuer key.

#### Scenario: An ordinary NPC cannot issue a commission
- **WHEN** issuer resolution is attempted for an NPC carrying no `QuestIssuer` component
- **THEN** it resolves to nothing, and no issuer key is produced for that entity

#### Scenario: A merchant without the component is still not a commissioner
- **WHEN** issuer resolution is attempted for an NPC carrying `Merchant` and `ScriptedDialogue` but
  not `QuestIssuer`
- **THEN** it resolves to nothing — carrying other service components confers no issuing authority

### Requirement: The QuestIssuer component mirrors the existing service-host component shape

`QuestIssuer` SHALL be a component named `quest_issuer` carrying `service_id`, `issuer_key`,
`service_binding`, and `anchor_room_id` — the same four-field shape `GuildStaff`, `GuildExaminer`,
and `Merchant` carry, with `issuer_key` in the place of `branch_key`. `service_id` SHALL be present
because the roster-sync reuse path reads it unconditionally on whichever component class anchors a
profession row; a commissioner blueprint whose anchor lacked the field would raise `AttributeError`
inside the guild-economy startup sync.

It SHALL be a capability marker and identity holder only: it SHALL NOT register, mutate, or settle a
quest, a reward, or a quest record itself, and every such mutation SHALL delegate to the
deterministic core exactly as the other service components do. It SHALL be resolvable through the
existing generic `resolve_local_service_host(actor, component_class)` with no change to that
function.

#### Scenario: The component is a marker and identity holder only
- **WHEN** the component class is inspected
- **THEN** it declares exactly `service_id`, `issuer_key`, `service_binding`, and `anchor_room_id`
  and contains no quest, reward, or record mutation

#### Scenario: A commissioner blueprint survives repeated roster synchronization
- **WHEN** the guild-economy roster sync runs twice with a profession row anchored on
  `quest_issuer`
- **THEN** the second run reuses the existing host through its `service_id` anchor without raising,
  and creates no duplicate host

#### Scenario: The generic host resolver finds a co-located commissioner
- **WHEN** `resolve_local_service_host` is called for the `QuestIssuer` class with exactly one
  co-located carrier
- **THEN** it returns that carrier, and with zero or several carriers it reports the same
  no-host and ambiguous-host outcomes it reports for every other service component

### Requirement: Every profession row anchors on a component that carries a service identity

The profession loader SHALL enforce that the FIRST component of every profession row names a
component class defining `service_id`, and a contract test SHALL fail naming the offending row
otherwise. The roster-sync reuse path resolves a row's host by reading `service_id` on the class
anchoring that row, so a row anchored on a class without the field would raise inside startup
synchronization rather than at authoring time. This invariant holds today only by convention —
`scripted_dialogue` also lacks the field and is never placed first — and this capability makes it
explicit and enforced.

#### Scenario: A row anchored on an identity-less component fails the contract
- **WHEN** a profession row is authored whose first component names a class that does not define
  `service_id`
- **THEN** the contract test fails naming that row, before any server synchronization runs

#### Scenario: Every existing row satisfies the invariant
- **WHEN** the contract test runs against the shipped profession rulebook
- **THEN** every row's first component class defines `service_id`

### Requirement: An issuer key resolves in exactly two authored forms

`resolve_issuer_key(host)` SHALL resolve a host carrying `QuestIssuer` to exactly one issuer key: a
non-empty authored `issuer_key` field SHALL resolve to `npc:<authored key>`, and an absent or empty
`issuer_key` field SHALL resolve to `npc:#<host primary key>`. The authored form SHALL be validated
against the shared issuer-key grammar and SHALL reject rather than being coerced when malformed. A
host with no `QuestIssuer` component SHALL resolve to nothing. The function SHALL be read-only and
SHALL perform no registry lookup, so a host resolves to a key whether or not any commission is
registered for it.

#### Scenario: An authored key resolves to the content form
- **WHEN** a host carries `QuestIssuer` with `issuer_key` set to a valid authored key
- **THEN** it resolves to `npc:<that key>`

#### Scenario: An unauthored key resolves to the identity form
- **WHEN** a host carries `QuestIssuer` with an absent or empty `issuer_key`
- **THEN** it resolves to `npc:#<the host's primary key>`

#### Scenario: A malformed authored key rejects
- **WHEN** a host carries `QuestIssuer` with an `issuer_key` that does not parse under the shared
  grammar
- **THEN** resolution raises the named grammar error rather than falling back to the identity form

#### Scenario: Resolution needs no registered commission
- **WHEN** a host carrying `QuestIssuer` is resolved while no issuance is registered for it
- **THEN** the key still resolves, and no registry is consulted

### Requirement: Commissioner authority is authorable through the import pipeline

The import pipeline SHALL accept `quest_issuer` as an explicit per-record component entry whose
`kwargs` carry the authored `issuer_key`, exactly as it accepts `branch_key` for `guild_staff` and
`shop_key` for `merchant`. The profession rulebook SHALL carry a commissioner blueprint row, and an
explicit per-record entry SHALL be combinable with another profession so one NPC can be both a
merchant and a commissioner. The loader SHALL never invent an `issuer_key`.

`issuer_key` SHALL NOT join the closed set of REQUIRED identity kwargs the assembly helper enforces.
That set means "must be authored and non-empty", which is false for `issuer_key`: an absent value is
the valid identity form that resolves to the carrier's database identity. The consequence is
explicit and accepted — a roster-created commissioner receives no authored `issuer_key` and resolves
to its identity form, while the import path, which passes authored kwargs through verbatim, is where
an authored content key is supplied.

The loader SHALL apply the entity-key contract style to authored issuer keys: a batch in which two
records author the same non-empty `issuer_key` SHALL be rejected naming the colliding key, because
the grammar validates shape and not uniqueness, and two carriers sharing one authored content key
would share one commission list.

Because a person-bound component can never anchor a roster row, an imported commissioner carries a
service anchor the roster can never claim or re-create; the startup service-host convergence SHALL
NOT treat such a host as shrunken-away roster residue and SHALL NOT delete it.

#### Scenario: An authored record gains the component with its identity
- **WHEN** a character record declares an explicit `quest_issuer` component entry with an
  `issuer_key`
- **THEN** the loaded NPC carries `QuestIssuer` with exactly that authored identity

#### Scenario: A merchant can also be a commissioner
- **WHEN** a record declares the `merchant` profession plus an explicit `quest_issuer` component
  entry
- **THEN** the loaded NPC carries both `Merchant` and `QuestIssuer`, each with its own authored
  identity

#### Scenario: A roster-created commissioner resolves to its identity form
- **WHEN** a commissioner host is created through the profession roster, which projects only the
  required identity kwargs onto each component
- **THEN** its `issuer_key` field is empty and it resolves to the identity form

#### Scenario: No existing NPC gains issuing authority
- **WHEN** the world is synchronized after this capability lands with no content authoring the
  component
- **THEN** no NPC carries `QuestIssuer` and no entity's behavior changes

#### Scenario: Two records cannot author the same commission identity
- **WHEN** one batch declares two records whose explicit `quest_issuer` entries carry the same
  non-empty `issuer_key`
- **THEN** the batch is rejected naming the duplicate key, and no record of it is instantiated

#### Scenario: An imported commissioner survives the startup service sync
- **WHEN** the guild-economy roster synchronization runs after a person-bound commissioner was
  assembled through the import path with a service anchor the roster does not list
- **THEN** the commissioner is not converged away, and its component and resolved key are intact
