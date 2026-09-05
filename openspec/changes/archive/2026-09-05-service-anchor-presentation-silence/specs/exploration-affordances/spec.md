# Delta spec: exploration-affordances (service-anchor-presentation-silence)

Adds the honest disabled state for a co-located but off-anchor service host. The emission key
("exact local host") is unchanged — this requirement fixes only the entry's enabled-state, so it
ADDS rather than rewrites the vocabulary requirement.

## ADDED Requirements

### Requirement: Navigation entries render off-anchor service hosts honestly
A `guild` or `shop` navigation entry for a co-located host whose corresponding service component
is verdicted `off_anchor` or `malformed_binding` by `world/rules/service_gate.py` SHALL be emitted
`enabled: false` with the gate's fixed registry message as its `disabled_reason.message` — the
entry keeps the unchanged navigation shape (no `action_id`, no `params`). A `remote` host changes
nothing (absence is still the norm), and an `allowed` host behaves exactly as before. The
anchor-room side of the contract is absence: a room containing the anchor but no host SHALL emit
no navigation entry for that service (pinned test; no ghost storefront).

#### Scenario: The traveling merchant shows disabled beside the player
- **WHEN** the place-bound merchant stands with the party in the town square and the snapshot
  presents exploration affordances
- **THEN** the shop navigation entry appears disabled carrying the gate's fixed message, and the
  Vue and text presenters render the same disabled entry from the shared emitter

#### Scenario: The darkened anchor room shows nothing
- **WHEN** the merchant has left the general store with the party and the player looks at the
  empty store through another character
- **THEN** the store's affordances carry no shop navigation entry at all

#### Scenario: At-anchor emission is untouched
- **WHEN** the merchant is at his anchor room beside the player
- **THEN** the shop navigation entry is enabled exactly as before this requirement
