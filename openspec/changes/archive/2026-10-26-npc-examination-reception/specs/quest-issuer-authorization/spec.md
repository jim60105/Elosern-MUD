# Spec Delta

## MODIFIED Requirements

### Requirement: The QuestIssuer component mirrors the existing service-host component shape

`QuestIssuer` SHALL be a component named `quest_issuer` carrying `service_id`, `issuer_key`,
`service_binding`, and `anchor_room_id` — the same four-field shape `GuildStaff`, `GuildExamReception`,
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
