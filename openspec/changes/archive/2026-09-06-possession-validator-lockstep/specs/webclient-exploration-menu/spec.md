# Delta spec: webclient-exploration-menu (possession-validator-lockstep)

The version-1 panel's action enumeration was frozen before the vocabulary gained
`explore.possess` / `explore.possess_release`, so emitting a legal vocabulary entry raised inside
the presenter and degraded the whole panel. The enumeration becomes derived from the shared
allowlist (full requirement reproduced with the widened enumeration and one added scenario).

## MODIFIED Requirements

### Requirement: The exploration panel is an exact read-only version-1 presentation panel
The production presentation registry SHALL register panel name `exploration` at schema version 1.
Its available payload SHALL contain exactly `schema_version`, `available`, `kind`, `move`, `look`,
`interact`, `character`, `quests`, and `inventory`; `available` SHALL be true and `kind` SHALL be
`exploration`. `move` SHALL be a bounded list of at most 12 exit descriptors, each containing
exactly `exit_ref`, `label`, `destination`, `enabled`, and nullable `disabled_reason`, where
`exit_ref` is the same opaque 1..64-ASCII-character identifier the `local_map` move action uses,
`label` is a bounded localized direction/exit label, `destination` is the canonical destination
node ID, and `enabled`/`disabled_reason` reflect a currently present, traversable Exit from the
actor's location (a locked or absent exit is a disabled row, never omitted, so the player learns
it exists). `look` SHALL contain exactly `room`, `entities`, and `objects`: `room` is an exact room
descriptor with a room marker for `explore.look`, `entities` is a bounded list of at most 32
present character/NPC/monster descriptors each carrying an opaque identity, bounded display name,
bounded kind, and nullable opaque `portrait_ref`, and `objects` is a bounded list of at most 32
present object descriptors carrying an opaque identity and bounded display name. `interact` SHALL
be a bounded list of at most 32 present target descriptors, each carrying exactly `identity`,
`display_name`, nullable `portrait_ref`, a bounded `affordances` list of at most 8 descriptors,
and — only for a scripted dialogue host — a bounded `keywords` list of at most 16 scripted
keyword descriptors. An action affordance SHALL contain exactly `kind` (`"action"`), `action_id`
(one of the shared affordance vocabulary's action codes — the panel's accepted-action enumeration
SHALL be derived from the shared `ACTION_CODE_ALLOWLIST` rather than a private duplicate, which
after the possession vocabulary includes `explore.talk_scripted`, `explore.talk_freeform`,
`explore.party_invite`, `explore.party_leave`, `explore.engage`, `explore.possess`, and
`explore.possess_release`), `label`, `enabled`, and nullable `disabled_reason`. A navigation
affordance SHALL contain exactly `kind` (`"navigate"`), `surface` (one of `"guild"` or `"shop"`),
`label`, `enabled`, and nullable `disabled_reason`. Navigation affordances are dock-navigation
descriptors only — they are NOT registered action adapters, never enter a `ui_action` payload,
and only tell the browser to open the corresponding `services` submenu. `character`, `quests`, and
`inventory` SHALL each be availability entries with exactly `available` (boolean): `character`
SHALL be available in exploration mode, and `quests`/`inventory` SHALL be available only when the
`services` panel is registered and available. The presenter SHALL build the payload only from
canonical room, entity, component, object, and service data, SHALL emit no live object or
filesystem reference, SHALL NOT mutate location, traits, knowledge, dialogue, quests, inventory,
or world time, and SHALL use the registered common unavailable form outside exploration mode.
Rendering the panel for a room whose legal vocabulary entries include a possession affordance
SHALL NOT raise inside the presenter: any entry the shared vocabulary may legally emit SHALL be
accepted by the panel's own validation, so a bound companion standing in the room can never
degrade the panel from within.

#### Scenario: Exploration snapshot carries the exploration root
- **WHEN** a puppeted WebClient in exploration mode receives a full snapshot
- **THEN** `exploration` reports `kind == "exploration"`, the current Exits in `move`, the present
  room/entities/objects in `look`, and the present interact targets with their legal affordances,
  while a before/after comparison of canonical game state is unchanged

#### Scenario: A bound companion's possess affordance never degrades the panel
- **WHEN** the room contains a bound companion of the actor and the full `exploration` panel is
  rendered through the production presenter
- **THEN** the panel is available with the companion descriptor carrying the `explore.possess`
  affordance, no presenter exception is logged, and the panel is not internal-unavailable

#### Scenario: Combat and creation do not receive fabricated exploration
- **WHEN** the active puppet is in an active combat session or is creation-pending
- **THEN** `exploration` uses its schema-valid unavailable form and contains no exit, entity,
  object, or affordance row

#### Scenario: A locked exit is disclosed but disabled
- **WHEN** the current room has an exit that exists but the actor cannot traverse
- **THEN** `move` contains that exit as a disabled row with a stable reason and no `explore.move`
  can succeed through it

#### Scenario: Quests and inventory respect the services capability
- **WHEN** the `services` panel is registered and available in exploration mode
- **THEN** `quests` and `inventory` are available; when the services capability is absent, both
  are unavailable and the dock shows no dead functional entry

#### Scenario: Presenter failure remains isolated
- **WHEN** the `exploration` presenter raises while status and narrative remain healthy
- **THEN** only `exploration` becomes correlated unavailable and normal text output remains usable
