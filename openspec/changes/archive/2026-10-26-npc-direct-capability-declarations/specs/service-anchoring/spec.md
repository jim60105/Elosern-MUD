# Spec Delta

## MODIFIED Requirements

### Requirement: Service components carry an authored person-or-place binding
Each bound service capability SHALL persist its own explicit person/place binding and, for place only, the uniquely resolved anchor room. The shared assembly SHALL be the sole configuration writer. Narrative-only dialogue SHALL retain ordinary conversation gates without becoming a service.

#### Scenario: Shipped place-bound hosts persist binding and anchor
- **WHEN** roster synchronization creates or reuses a declared service component
- **THEN** its own authored binding and anchor persist independently of other components

#### Scenario: Binding and anchor survive a save/reload round-trip
- **WHEN** component state is saved and reloaded
- **THEN** the same explicit binding/anchor and availability verdict are observed

#### Scenario: An invalid authored combination is rejected before construction
- **WHEN** person has an anchor or place has no unique room
- **THEN** the complete batch rejects and no component or entity persists

#### Scenario: Reused hosts re-converge their binding at each sync
- **WHEN** an authored binding changes
- **THEN** only its configuration converges; identity, location and runtime state survive

### Requirement: One read-only resolver answers service availability with a stable vocabulary
`world/rules/service_gate.py` SHALL provide `service_available(actor, host, component)` returning a
frozen verdict with `allowed` and a nullable stable reason from exactly
`{remote, off_anchor, malformed_binding}`, evaluated under the reason conditions below in that
order, failing closed and never defaulting open. The resolver SHALL write no state, and each
`malformed_binding` verdict SHALL emit at most one debounced warn event per host carrying the host
and component context.

#### Scenario: Co-location rules first
- **WHEN** a place-bound host in another room is queried
- **THEN** the verdict reason is `remote`, not `off_anchor`

#### Scenario: An off-anchor traveling host is refused by name
- **WHEN** a `place`-bound host stands beside the actor but at a room other than its anchor
- **THEN** the verdict is `off_anchor` and the fixed registry message is available to the caller

#### Scenario: A `person`-bound host serves anywhere co-located
- **WHEN** a `person`-bound host stands beside the actor in any room
- **THEN** the verdict is allowed

#### Scenario: Malformed stored data fails closed once-warned
- **WHEN** a component's stored binding is `portable`, or `place` with an anchor id whose room is
  deleted
- **THEN** the verdict is `malformed_binding`, resolution allowed is false, and repeated queries
  against the same host emit one debounced warn event only

#### Scenario: Remote refusals keep per-surface prose
- **WHEN** the merchant surface and the guild surface each refuse a `remote` host through their
  command paths
- **THEN** each refusal line names its own service and no gate-module constant supplies either line

#### Scenario: The stable reasons have fixed conditions
- **WHEN** the resolver evaluates a verdict
- **THEN** `remote` is returned when actor and host are not co-located; `off_anchor` when the
  component is `place`-bound and the host's location is not the anchor room; and
  `malformed_binding` when the stored binding is unknown, `place` lacks a resolvable anchor room,
  or required binding attributes are missing on any bound service capability

#### Scenario: Refusal message ownership is split between gate and callers
- **WHEN** a caller renders a refusal for an `off_anchor` or `remote` verdict
- **THEN** the fixed Traditional Chinese message for `off_anchor` is a registry-owned constant of
  the gate module consumed by every caller, while `remote` refusals gain no gate-owned message —
  they name the service per surface (merchant, guild staff) and stay in each caller's own message
  table, the gate exposing only the stable reason code
