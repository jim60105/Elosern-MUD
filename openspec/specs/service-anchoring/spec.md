# service-anchoring Specification

## Purpose

The authored availability axis for services: every service component persists
a `person | place` binding (copied by profession assembly from the blueprint
row), `place` components additionally persist their anchor room, and one
read-only resolver answers every service gate's availability question with a
stable reason vocabulary (`remote | off_anchor | malformed_binding`) and a
fail-closed posture.

## Requirements

### Requirement: Service components carry an authored person-or-place binding
Each service component created through profession assembly SHALL persist `service_binding` (`person`
or `place`, copied from the profession row's `default_binding`) and — only for `place` —
`anchor_room_id` (the dbid of the resolved anchor room) as persistent component fields (Evennia
contrib-components `DBField`s — not plain instance attributes), surviving a save/reload round-trip.
The values SHALL be written only by the
shared assembly (single writer), SHALL be re-converged from the roster for reused hosts at each
sync (binding is authored config, not runtime identity — the never-rename/never-retitle contract is
untouched), and an authored invalid combination (`place` without an anchor room, `person` carrying
an anchor) SHALL be rejected at config/schema validation time for roster and import records alike.

#### Scenario: Shipped place-bound hosts persist binding and anchor
- **WHEN** the roster sync creates or reuses the guild master and merchant
- **THEN** each service component carries `service_binding: "place"` and the anchor room's dbid,
  and a `person`-bound test component carries no anchor attribute value

#### Scenario: Binding and anchor survive a save/reload round-trip
- **WHEN** an assembled host's components are saved and re-read without the assembly having run
  in the current process
- **THEN** `service_binding` and `anchor_room_id` read back exactly as written and the resolver
  reaches the same verdicts

#### Scenario: An invalid authored combination is rejected before construction
- **WHEN** a roster row or import record declares a `person`-bound component with an anchor (or a
  `place`-bound component whose authored sources supply no anchor)
- **THEN** config/schema validation rejects it with a named error and no component is created

### Requirement: One read-only resolver answers service availability with a stable vocabulary
`world/rules/service_gate.py` SHALL provide `service_available(actor, host, component)` returning a
frozen verdict with `allowed` and a nullable stable reason from exactly
`{remote, off_anchor, malformed_binding}`: `remote` when actor and host are not co-located (checked
first); `off_anchor` when the component is `place`-bound and the host's location is not the anchor
room; `malformed_binding` when the stored binding is unknown, `place` lacks a resolvable anchor
room, or the attributes are missing on a component this change's sync has re-converged — the
resolver SHALL fail closed, never default open. The resolver SHALL write no state, and each
`malformed_binding` verdict SHALL emit at most one debounced warn event per host carrying the host
and component context. The fixed Traditional Chinese message for `off_anchor` SHALL be a
registry-owned constant of the gate module consumed by every caller; `remote` refusals SHALL NOT
gain a gate-owned message — they name the service per surface (merchant, guild staff) and stay in
each caller's own message table, the gate exposing only the stable reason code.

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
