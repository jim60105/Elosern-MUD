# Delta spec: service-anchoring (possession-rules-residue)

The synced requirement claims registry-owned fixed messages for `remote` AND `off_anchor`; the
gate only ever owned the `off_anchor` line, because `remote` refusals name their service per
surface (merchant vs guild staff) and live in caller message tables. The requirement is corrected
to the actual, better ownership — no code change, no behavior change.

## MODIFIED Requirements

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
