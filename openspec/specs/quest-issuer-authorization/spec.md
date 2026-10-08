# quest-issuer-authorization Specification

## Purpose
Defines who may issue a private commission: the authority is carried exclusively by the `QuestIssuer` component, is authored — never inferred — and reaches NPCs only through the import pipeline. The capability pins the component's four-field service-host shape, the loader-level row-anchor invariant, the exactly-two-forms issuer-key resolution, batch-wide uniqueness of authored issuer keys, and the convergence-survival guarantee for person-bound commissioners.

## Requirements

### Requirement: Authority to issue a private commission is authored, never inferred

The right to issue a private commission SHALL be carried exclusively by the `QuestIssuer` component
declared in `typeclasses/components.py` and registered in the closed profession component
vocabulary. No other property of an entity — its display name, its typeclass, its other components,
its location, its schedule, its dialogue authorship, or the mere fact that it has a database
identity — SHALL confer that authority.

#### Scenario: An ordinary NPC cannot issue a commission
- **WHEN** issuer resolution is attempted for an NPC carrying no `QuestIssuer` component
- **THEN** it resolves to nothing, and no issuer key is produced for that entity

#### Scenario: A merchant without the component is still not a commissioner
- **WHEN** issuer resolution is attempted for an NPC carrying `Merchant` and `ScriptedDialogue` but
  not `QuestIssuer`
- **THEN** it resolves to nothing — carrying other service components confers no issuing authority

#### Scenario: No property short of the component confers authority
- **WHEN** an entity's display name, typeclass, other components, location, schedule, dialogue
  authorship, or mere database identity is examined as a candidate source of commission authority
- **THEN** none of them confers that authority

#### Scenario: A component-less entity resolves to no issuer key
- **WHEN** an entity without the `QuestIssuer` component is asked to resolve an issuer key
- **THEN** it SHALL NOT resolve to any issuer key

### Requirement: The QuestIssuer component mirrors the existing service-host component shape

`QuestIssuer` SHALL be a component named `quest_issuer` carrying `service_id`, `issuer_key`,
`service_binding`, and `anchor_room_id` — the same four-field shape `GuildStaff`, `GuildExaminer`,
and `Merchant` carry, with `issuer_key` in the place of `branch_key`. `service_id` SHALL be present
because the roster-sync reuse path reads it unconditionally on whichever component class anchors a
profession row.

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

#### Scenario: A missing service_id would break the roster-sync reuse path
- **WHEN** a commissioner blueprint's anchor component lacked `service_id`
- **THEN** the roster-sync reuse path would raise `AttributeError` inside the guild-economy startup
  sync, which is why the field is required

#### Scenario: Mutations delegate to the deterministic core
- **WHEN** a quest, reward, or quest record mutation is requested through a commissioner
- **THEN** the component itself never registers, mutates, or settles it; every such mutation delegates
  to the deterministic core exactly as the other service components do

#### Scenario: The component resolves through the existing generic resolver
- **WHEN** a commissioner host is resolved
- **THEN** it is resolvable through the existing generic
  `resolve_local_service_host(actor, component_class)` with no change to that function

### Requirement: Every profession row anchors on a component that carries a service identity

The profession loader SHALL enforce that the FIRST component of every profession row names a
component class defining `service_id`, and a contract test SHALL fail naming the offending row
otherwise.

#### Scenario: A row anchored on an identity-less component fails the contract
- **WHEN** a profession row is authored whose first component names a class that does not define
  `service_id`
- **THEN** the contract test fails naming that row, before any server synchronization runs

#### Scenario: Every existing row satisfies the invariant
- **WHEN** the contract test runs against the shipped profession rulebook
- **THEN** every row's first component class defines `service_id`

#### Scenario: Without enforcement the failure lands at startup, not authoring
- **WHEN** a row is anchored on a class without `service_id` and no loader check exists
- **THEN** the roster-sync reuse path, which resolves a row's host by reading `service_id` on the
  class anchoring that row, would raise inside startup synchronization rather than at authoring time

#### Scenario: The invariant is promoted from convention to enforcement
- **WHEN** the state before this capability is inspected
- **THEN** the invariant held only by convention — `scripted_dialogue` also lacks the field and is
  never placed first — and this capability makes it explicit and enforced

### Requirement: An issuer key resolves in exactly two authored forms

`resolve_issuer_key(host)` SHALL resolve a host carrying `QuestIssuer` to exactly one issuer key: a
non-empty authored `issuer_key` field SHALL resolve to `npc:<authored key>`, and an absent or empty
`issuer_key` field SHALL resolve to `npc:#<host primary key>`.

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

#### Scenario: The authored form is grammar-validated
- **WHEN** `resolve_issuer_key` resolves a non-empty authored `issuer_key`
- **THEN** the authored form is validated against the shared issuer-key grammar and rejects rather
  than being coerced when malformed

#### Scenario: A host without the component resolves to nothing
- **WHEN** `resolve_issuer_key` is called on a host with no `QuestIssuer` component
- **THEN** it resolves to nothing

#### Scenario: Resolution is a pure read
- **WHEN** `resolve_issuer_key` runs
- **THEN** it is read-only and performs no registry lookup, so a host resolves to a key whether or not
  any commission is registered for it

### Requirement: Commissioner authority is authorable through the import pipeline

The import pipeline SHALL accept `quest_issuer` as an explicit per-record component entry whose
`kwargs` carry the authored `issuer_key`, exactly as it accepts `branch_key` for `guild_staff` and
`shop_key` for `merchant`. The loader SHALL never invent an `issuer_key`. `issuer_key` SHALL NOT join
the closed set of REQUIRED identity kwargs the assembly helper enforces.

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

#### Scenario: The rulebook carries a commissioner blueprint
- **WHEN** the profession rulebook is inspected
- **THEN** it carries a commissioner blueprint row, and an explicit per-record entry is combinable
  with another profession so one NPC can be both a merchant and a commissioner

#### Scenario: An absent issuer_key is a valid identity, not a missing requirement
- **WHEN** the meaning of the closed REQUIRED identity kwargs set is applied to `issuer_key`
- **THEN** the set's "must be authored and non-empty" does not fit `issuer_key`: an absent value is
  the valid identity form that resolves to the carrier's database identity

#### Scenario: The roster/import split is explicit and accepted
- **WHEN** authority is authored through each path
- **THEN** a roster-created commissioner receives no authored `issuer_key` and resolves to its
  identity form, while the import path, which passes authored kwargs through verbatim, is where an
  authored content key is supplied

#### Scenario: Batch uniqueness guards against a shared commission list
- **WHEN** two carriers would share one authored content key, since the grammar validates shape and
  not uniqueness
- **THEN** the entity-key contract style rejects the batch naming the colliding key, because the two
  carriers would share one commission list

#### Scenario: The roster can never claim an imported commissioner's anchor
- **WHEN** an imported commissioner carries a service anchor, because a person-bound component can
  never anchor a roster row
- **THEN** the roster can never claim or re-create that anchor, and the startup service-host
  convergence SHALL NOT treat such a host as shrunken-away roster residue and SHALL NOT delete it
