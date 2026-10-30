## MODIFIED Requirements

### Requirement: The exploration panel is an exact read-only version-4 presentation panel
The production exploration panel SHALL use exact schema6 fields and read-only canonical data, retaining bounded move rows whose wilderness destination can be null when disclosure is withheld while known destinations remain canonical.

#### Scenario: Exploration snapshot carries the exploration root
- **WHEN** a puppeted WebClient in exploration mode receives a full snapshot; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** `exploration` reports schema version 6 and `kind == "exploration"`, the current Exits in `move`, the present room/entities/objects in `look`, and the present interact targets with their legal affordances, while a before/after comparison of canonical game state is unchanged

#### Scenario: A bound companion's possess affordance never degrades the panel
- **WHEN** the room contains a bound companion of the actor and the full `exploration` panel is; any asserted wilderness destination facts are revealed and location-identity permitted
  rendered through the production presenter
- **THEN** the panel is available with the companion descriptor carrying the `explore.possess`
  affordance, no presenter exception is logged, and the panel is not internal-unavailable

#### Scenario: Combat and creation do not receive fabricated exploration
- **WHEN** the active puppet is in an active combat session or is creation-pending; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** `exploration` uses its schema-valid unavailable form and contains no exit, entity, object, or affordance row

#### Scenario: A locked exit is disclosed but disabled
- **WHEN** the current room has an exit that exists but the actor cannot traverse; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** `move` contains that exit as a disabled row with a stable reason and no `explore.move` can succeed through it

#### Scenario: Quests and inventory respect the services capability
- **WHEN** the `services` panel is registered and available in exploration mode; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** `quests` and `inventory` are available; when the services capability is absent, both are unavailable and the dock shows no dead functional entry

#### Scenario: Presenter failure remains isolated
- **WHEN** the `exploration` presenter raises while status and narrative remain healthy; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** only `exploration` becomes correlated unavailable and normal text output remains usable

#### Scenario: A delivery affordance carries its normalized dispatch payload
- **WHEN** the room contains a co-located bound delivery recipient and the full `exploration` panel is rendered through the production presenter; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the target descriptor carries the `explore.deliver` affordance with exactly the normalized `params` (`npc_id` and `item_key`), and no other ordinary action affordance carries a params field

#### Scenario: In-conversation codes and keyword lists are rejected
- **WHEN** the server validator or the client mirror receives an exploration payload whose target carries a `keywords` list, or an affordance naming `explore.talk_scripted` or `explore.talk_freeform`, or whose `schema_version` is 2 or 3; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the payload is rejected as a protocol error and is never adopted

#### Scenario: The author-editor navigation descriptor is accepted and carries no card
- **WHEN** the server validator or the client mirror receives an exploration payload whose NPC target carries a `navigate` affordance with surface `npc_persona`; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the payload is accepted, and a descriptor carrying any field beyond the five navigation fields is rejected as a protocol error

#### Scenario: Move rows are bounded exit descriptors
- **WHEN** the presenter builds `move` for a room with current Exits; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** `move` is a bounded list of at most 12 exit descriptors, each containing exactly `exit_ref`, `label`, `destination`, `enabled`, and nullable `disabled_reason`
- **AND** `exit_ref` is the same opaque 1..64-ASCII-character identifier the `local_map` move action uses, `label` is a bounded localized direction/exit label, and `destination` is the canonical destination node ID for disclosed targets, or null for a withheld wilderness direction
- **AND** `enabled`/`disabled_reason` reflect a currently present, traversable Exit from the actor's location, so a locked or absent exit is a disabled row, never omitted, and the player learns it exists

#### Scenario: Look carries exactly room, entities, and objects
- **WHEN** the presenter builds the `look` section; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** it contains exactly `room`, `entities`, and `objects`: `room` is an exact room descriptor with a room marker for `explore.look`, `entities` is a bounded list of at most 32 present character/NPC/monster descriptors each carrying an opaque identity, bounded display name, bounded kind, and nullable opaque `portrait_ref`, and `objects` is a bounded list of at most 32 present object descriptors carrying an opaque identity and bounded display name

#### Scenario: Interact targets carry exactly their four fields and a bounded affordance list
- **WHEN** the presenter builds `interact`; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** it is a bounded list of at most 32 present target descriptors, each carrying exactly `identity`, `display_name`, nullable `portrait_ref`, services, and a bounded `affordances` list of at most 8 descriptors
- **AND** a target descriptor carries no keyword list beyond its declared services routes, because a conversation's topics reach the browser only through the `dialogue` panel's `choices` once the conversation is open

#### Scenario: An action affordance carries exactly its five fields
- **WHEN** the presenter serializes an action affordance; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** it contains exactly `kind` (`"action"`), `action_id`, `label`, `enabled`, and nullable `disabled_reason`

#### Scenario: Accepted actions derive from the shared allowlist minus in-conversation codes
- **WHEN** the panel's accepted-action enumeration is assembled; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** it is derived from the shared `ACTION_CODE_ALLOWLIST` rather than a private duplicate, minus the two in-conversation codes `explore.talk_scripted` and `explore.talk_freeform`, which never appear on any target descriptor
- **AND** the target affordances the presenter emits are drawn from `explore.talk_open`, `explore.party_invite`, `explore.party_leave`, `explore.engage`, `explore.possess`, `explore.possess_release`, and `explore.deliver`, which is exactly the client mirror's target-scoped action list

#### Scenario: Only the deliver affordance carries params
- **WHEN** the presenter emits target action affordances; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** exactly the `explore.deliver` action affordance additionally carries `params`, the shared delivery validator's normalized dispatch payload (`npc_id` and the bounded ASCII `item_key`), and every other action affordance carries no `params`, its dispatch payload being re-derived from the target identity at the dock

#### Scenario: A navigation affordance carries exactly its five fields and opens only a drawer
- **WHEN** the presenter serializes a navigation affordance; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** it contains exactly `kind` (`"navigate"`), `surface` (only npc_persona for an ordinary NPC editor), `label`, `enabled`, and nullable `disabled_reason`
- **AND** navigation affordances are dock-navigation descriptors only; they are NOT registered action adapters, never enter a `ui_action` payload, and only open the ordinary author editor; supported services use the separate exact target-bound route union

#### Scenario: Availability entries carry only the available boolean
- **WHEN** the presenter builds `character`, `quests`, and `inventory`; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** each is an availability entry with exactly `available` (boolean): `character` is available in exploration mode, and `quests`/`inventory` are available only when the `services` panel is registered and available

#### Scenario: A vocabulary-emitted possession entry never raises in the presenter
- **WHEN** the panel is rendered for a room whose legal vocabulary entries include a possession affordance; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the presenter does not raise: the entry is either serialized as an accepted target affordance or folded into the target's single conversation affordance, so a bound companion standing in the room can never degrade the panel from within

#### Scenario: The presenter stays read-only over canonical data
- **WHEN** the `exploration` presenter builds its payload; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** it is built only from canonical room, entity, component, object, and service data, emits no live object or filesystem reference, does not mutate location, traits, knowledge, dialogue, quests, inventory, or world time, and uses the registered common unavailable form outside exploration mode

#### Scenario: Available schema versions cut over together
- **WHEN** either validator receives an available exploration panel with schema version 6, and then otherwise identical panels with version 4 or another unsupported version; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** only version 6 is accepted, including its non-null reference fields and its nullable wilderness move-row destination, and no dual-version conversion is performed

#### Scenario: Bounded independent services field
- **WHEN** an NPC interact descriptor is serialized; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** services has exact state none/ready/unreadable and at most 16 stable-key label/enabled/reason/route entries, independent of the eight general-affordance limit; Python and browser accept only schema 6



#### Scenario: Undisclosed directional target
- **WHEN** a synthetic unvisited wilderness neighbour remains outside reveal
- **THEN** it has no local-map node or identifying exit metadata, while its enabled opaque direction can still submit exit_ref/current_node without a fabricated minimap highlight

### Requirement: Exploration move rows advertise canonical destinations
The exploration menu's wilderness move rows SHALL use the canonical destination resolver so a disclosed row's advertised destination equals the node the player actually arrives at, while a withheld wilderness direction keeps its row with a null destination and the server's generic direction word.

#### Scenario: Move row destination matches actual arrival
- **WHEN** the exploration menu lists a wilderness move row whose destination is revealed or whose gateway identity is disclosed; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** that row's destination is the canonical arrival node, including the gateway south row that returns to the grid

#### Scenario: A withheld move row publishes no arrival identity
- **WHEN** a wilderness direction resolves to an unrevealed cell or to an unvisited hidden entry; the reveal state is a synthetic record fixed by the test
- **THEN** the row keeps its exact five keys, `enabled`, and any server-authored `disabled_reason`, publishes `destination: null` and the generic direction word as its label, and still submits exactly `{exit_ref, current_node}` so the step arrives at the canonical real cell
