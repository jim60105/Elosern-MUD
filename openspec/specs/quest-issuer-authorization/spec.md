# quest-issuer-authorization Specification

## Purpose
Defines who may issue a private commission: the authority is carried exclusively by the `QuestIssuer` component, is authored — never inferred — and reaches NPCs only through the import pipeline. The capability pins the component's four-field service-host shape, the loader-level row-anchor invariant, the exactly-two-forms issuer-key resolution, batch-wide uniqueness of authored issuer keys, and the convergence-survival guarantee for person-bound commissioners.

## Requirements

### Requirement: Authority to issue a private commission is authored, never inferred

Private commission authority SHALL reside exclusively in the registered `QuestIssuer` component; only an authored import declaration or an explicitly validated generated package issuer declaration MAY provision it, through rules-owned helpers. No other property SHALL confer that authority. Provisioning SHALL grant only the validated scope to the exact bound actor, keep the component shape and two-form key grammar, and register strictly only after actual authorization.

#### Scenario: Ordinary NPC has no authority
- **WHEN** an NPC without QuestIssuer, including a merchant or scripted host, is resolved or asks to offer a commission
- **THEN** no issuer key or commission authority is granted by its other properties

#### Scenario: Generated issuer receives only declared scope
- **WHEN** activation provisions an explicitly validated issuer role and registers its commission
- **THEN** the exact bound actor receives the declared scope through deterministic helpers and its existing grammar-valid actual key is used for strict registration

#### Scenario: Undeclared commission is refused
- **WHEN** a generated issuer attempts an effect outside its validated commission scope or a forged symbolic role is submitted as runtime authority
- **THEN** authorization rejects it and no quest is accepted or registered

#### Scenario: Provisioning and registration roll back together
- **WHEN** activation fails after provisioning or registration
- **THEN** reload and process-local views expose neither partial authority nor a stale commission

#### Scenario: An ordinary NPC cannot issue a commission
- **WHEN** issuer resolution is attempted for an NPC carrying no `QuestIssuer` component
- **THEN** it resolves to nothing, and no issuer key is produced for that entity

#### Scenario: A merchant without the component is still not a commissioner
- **WHEN** issuer resolution is attempted for an NPC carrying `Merchant` and `ScriptedDialogue` but
  not `QuestIssuer`
- **THEN** it resolves to nothing; carrying other service components confers no issuing authority

#### Scenario: No property short of the component confers authority
- **WHEN** an entity's display name, typeclass, other components, location, schedule, dialogue
  authorship, or mere database identity is examined as a candidate source of commission authority
- **THEN** none of them confers that authority

#### Scenario: A component-less entity resolves to no issuer key
- **WHEN** an entity without the `QuestIssuer` component is asked to resolve an issuer key
- **THEN** it SHALL NOT resolve to any issuer key

### Requirement: The QuestIssuer component mirrors the existing service-host component shape
The quest-issuer capability SHALL retain its service_id, optional issuer_key, binding and anchor fields as deterministic authority/configuration only. Host reuse SHALL depend on canonical host provenance, independently of these fields or declaration order.

#### Scenario: The component is a marker and identity holder only
- **WHEN** a commission mutation is requested
- **THEN** the capability delegates to the deterministic owner and performs no quest/reward writes itself

#### Scenario: A commissioner blueprint survives repeated roster synchronization
- **WHEN** the commissioner is reordered or its service_id changes
- **THEN** the same canonical host dbref is reused without duplicates

#### Scenario: The generic host resolver finds a co-located commissioner
- **WHEN** an implicit command has exactly one local commissioner
- **THEN** it resolves that host; zero or multiple remain implicit-command refusal cases

#### Scenario: A missing service_id would break the roster-sync reuse path
- **WHEN** host identity is resolved for a commissioner
- **THEN** lookup does not read service_id and cannot fail due to its absence

#### Scenario: Mutations delegate to the deterministic core
- **WHEN** a quest, reward or record mutation is requested through a commissioner
- **THEN** the component delegates to its deterministic owner and performs no business writes

#### Scenario: The component resolves through the existing generic resolver
- **WHEN** implicit discovery resolves a commissioner
- **THEN** the existing generic component resolver retains its local zero/one/multiple-host behavior

### Requirement: Every profession row anchors on a component that carries a service identity
Authored host reuse SHALL use canonical host provenance and SHALL NOT require any first capability or component-level service identity.

#### Scenario: A row anchored on an identity-less component fails the contract
- **WHEN** a host declares narrative dialogue first or no capabilities
- **THEN** host lookup remains valid through canonical provenance

#### Scenario: Every existing row satisfies the invariant
- **WHEN** all shipped host declarations synchronize twice
- **THEN** every canonical identity selects exactly one host independently of capability order

#### Scenario: Without enforcement the failure lands at startup, not authoring
- **WHEN** a duplicate canonical host identity exists
- **THEN** full-batch preflight rejects before mutations

#### Scenario: The invariant is promoted from convention to enforcement
- **WHEN** a source-managed host plan is validated
- **THEN** canonical provenance uniqueness is enforced, with no first-component service-id invariant

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

NPC imports and source-host declarations SHALL accept direct quest-issuer configuration without a profession. issuer_key SHALL remain optional: nonempty authored keys use existing grammar and duplicate rejection, absent/empty keys use canonical NPC identity. No component is inferred or authority granted automatically.

#### Scenario: An authored record gains the component with its identity
- **WHEN** an NPC declares quest_issuer with valid issuer_key and binding
- **THEN** exactly that authority is installed

#### Scenario: A merchant can also be a commissioner
- **WHEN** an NPC directly declares merchant and person-bound quest_issuer
- **THEN** both function independently with their own configured bindings

#### Scenario: A roster-created commissioner resolves to its identity form
- **WHEN** its explicit issuer_key is absent/empty
- **THEN** the current npc:#dbid identity is retained

#### Scenario: No existing NPC gains issuing authority
- **WHEN** a source record declares no quest_issuer
- **THEN** sync does not infer or attach it

#### Scenario: Two records cannot author the same commission identity
- **WHEN** two direct declarations claim the same nonempty issuer_key
- **THEN** the complete batch rejects before writes

#### Scenario: An imported commissioner survives the startup service sync
- **WHEN** an unmanaged imported commissioner carries a service ID absent from roster
- **THEN** source sync does not claim or delete it

#### Scenario: The rulebook carries a commissioner blueprint
- **WHEN** commission authority is authored
- **THEN** it uses direct quest_issuer configuration and no profession rulebook remains

#### Scenario: An absent issuer_key is a valid identity, not a missing requirement
- **WHEN** issuer_key is absent or empty on a valid direct declaration
- **THEN** the existing npc:#dbid identity form remains valid

#### Scenario: The roster/import split is explicit and accepted
- **WHEN** either roster or import supplies or omits issuer_key
- **THEN** the same validator preserves its authored-key or canonical identity-form semantics

#### Scenario: Batch uniqueness guards against a shared commission list
- **WHEN** two carriers claim one nonempty authored issuer_key
- **THEN** the complete batch rejects the collision before persistence

#### Scenario: The roster can never claim an imported commissioner's anchor
- **WHEN** an unmanaged imported commissioner has component IDs matching or differing from roster rows
- **THEN** sync does not claim/delete it by those IDs; explicit canonical source ownership controls host lifecycle

### Requirement: Escort issuer scope authorizes each distinct current commission
Validated QuestIssuer scope SHALL name each distinct commission and group explicitly. Offer/acceptance SHALL revalidate the exact issuer, registered issuance, current phase and group availability. Protected/meeting roles, familial relation and prose SHALL grant no authority. Acceptance SHALL create no alternative record.

#### Scenario: Each role authorizes its own alternative
- **WHEN** two authorized roles offer distinct escorts in both encounter orders
- **THEN** each offer names its own actual issuer and registered issuance, and accepting either creates only that commission's record

#### Scenario: Scope and stale-phase violations refuse
- **WHEN** an issuer offers an undeclared commission or a stale phase/group capability is accepted
- **THEN** the named authority/freshness refusal changes no quest, group or membership state

#### Scenario: Complete escort issuer scope authorizes each distinct current commission contract
- **WHEN** the operation is exercised through its deterministic owner with valid and rejecting inputs
- **THEN** The upstream validated QuestIssuer scope SHALL support several explicitly declared distinct commission references and exclusive-group references. Every offer/acceptance SHALL revalidate the exact authorized issuer actor, definition/issuance reference, current role phase and group availability. A meeting/protected role, familial relation, story prose or shared group SHALL never grant issuer authority. Accepting a commission SHALL not accept its alternatives. Runtime issuer keys SHALL retain the existing grammar and component authority.
