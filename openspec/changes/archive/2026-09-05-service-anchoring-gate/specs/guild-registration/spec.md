# Delta spec: guild-registration (service-anchoring-gate)

Registration's "absent or remote staff" rule widens through the resolver: a place-bound staff
traveling off-anchor is refused the way a remote one is. Requirement reproduced in full.

## MODIFIED Requirements

### Requirement: Registration access is local, idempotent, and strict about persisted data
Registration SHALL reject non-player entities, absent or remote staff, and ambiguous multiple
local GuildStaff hosts. Local-host acceptance SHALL flow through
`world/rules/service_gate.py::service_available` for the resolved staff component: `remote` keeps
the existing remote-staff rejection, and an `off_anchor` or `malformed_binding` verdict SHALL
refuse registration with the gate's fixed registry message and no guild field written.
Re-registering a valid member SHALL return the original record without replacing its branch, tick,
or snapshot. A partial or malformed existing record SHALL raise `GuildDataError` without repair or
rank mutation.

#### Scenario: Remote staff cannot register a player
- **WHEN** a player invokes registration while the selected GuildStaff host is in another room
- **THEN** registration is rejected and no guild field changes

#### Scenario: An off-anchor traveling clerk refuses registration
- **WHEN** the guild clerk host stands beside the player in a room other than its anchor and the
  player invokes registration
- **THEN** the gate's fixed message is returned and no guild field changes

#### Scenario: Repeated registration preserves historical values
- **WHEN** a registered player changes disguise and invokes registration again
- **THEN** the original tick and displayed-stat snapshot remain unchanged

#### Scenario: Partial membership data fails closed
- **WHEN** `guild_rank` is F but `guild_registration` lacks its displayed-stat snapshot
- **THEN** registration raises `GuildDataError` and writes nothing
