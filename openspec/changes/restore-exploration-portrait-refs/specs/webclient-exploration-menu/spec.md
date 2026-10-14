# Spec Delta

## RENAMED Requirements

- FROM: `The exploration panel is an exact read-only version-3 presentation panel`
- TO: `The exploration panel is an exact read-only version-4 presentation panel`

## MODIFIED Requirements

### Requirement: The exploration panel is an exact read-only version-4 presentation panel
The production presentation registry SHALL register panel name `exploration` at schema version 4 with `available` true and `kind` `exploration`, and its available payload SHALL contain exactly `schema_version`, `available`, `kind`, `move`, `look`, `interact`, `character`, `quests`, and `inventory`.

#### Scenario: Exploration snapshot carries the exploration root
- **WHEN** a puppeted WebClient in exploration mode receives a full snapshot
- **THEN** `exploration` reports schema version 4 and `kind == "exploration"`, the current Exits in `move`, the present room/entities/objects in `look`, and the present interact targets with their legal affordances, while a before/after comparison of canonical game state is unchanged

#### Scenario: A bound companion's possess affordance never degrades the panel
- **WHEN** the room contains a bound companion of the actor and the full `exploration` panel is
  rendered through the production presenter
- **THEN** the panel is available with the companion descriptor carrying the `explore.possess`
  affordance, no presenter exception is logged, and the panel is not internal-unavailable

#### Scenario: Combat and creation do not receive fabricated exploration
- **WHEN** the active puppet is in an active combat session or is creation-pending
- **THEN** `exploration` uses its schema-valid unavailable form and contains no exit, entity, object, or affordance row

#### Scenario: A locked exit is disclosed but disabled
- **WHEN** the current room has an exit that exists but the actor cannot traverse
- **THEN** `move` contains that exit as a disabled row with a stable reason and no `explore.move` can succeed through it

#### Scenario: Quests and inventory respect the services capability
- **WHEN** the `services` panel is registered and available in exploration mode
- **THEN** `quests` and `inventory` are available; when the services capability is absent, both are unavailable and the dock shows no dead functional entry

#### Scenario: Presenter failure remains isolated
- **WHEN** the `exploration` presenter raises while status and narrative remain healthy
- **THEN** only `exploration` becomes correlated unavailable and normal text output remains usable

#### Scenario: A delivery affordance carries its normalized dispatch payload
- **WHEN** the room contains a co-located bound delivery recipient and the full `exploration` panel is rendered through the production presenter
- **THEN** the target descriptor carries the `explore.deliver` affordance with exactly the normalized `params` (`npc_id` and `item_key`), and no other action affordance carries a `params` field

#### Scenario: In-conversation codes and keyword lists are rejected
- **WHEN** the server validator or the client mirror receives an exploration payload whose target carries a `keywords` list, or an affordance naming `explore.talk_scripted` or `explore.talk_freeform`, or whose `schema_version` is 2 or 3
- **THEN** the payload is rejected as a protocol error and is never adopted

#### Scenario: The author-editor navigation descriptor is accepted and carries no card
- **WHEN** the server validator or the client mirror receives an exploration payload whose NPC target carries a `navigate` affordance with surface `npc_persona`
- **THEN** the payload is accepted, and a descriptor carrying any field beyond the five navigation fields is rejected as a protocol error

#### Scenario: Move rows are bounded exit descriptors
- **WHEN** the presenter builds `move` for a room with current Exits
- **THEN** `move` is a bounded list of at most 12 exit descriptors, each containing exactly `exit_ref`, `label`, `destination`, `enabled`, and nullable `disabled_reason`
- **AND** `exit_ref` is the same opaque 1..64-ASCII-character identifier the `local_map` move action uses, `label` is a bounded localized direction/exit label, and `destination` is the canonical destination node ID
- **AND** `enabled`/`disabled_reason` reflect a currently present, traversable Exit from the actor's location, so a locked or absent exit is a disabled row, never omitted, and the player learns it exists

#### Scenario: Look carries exactly room, entities, and objects
- **WHEN** the presenter builds the `look` section
- **THEN** it contains exactly `room`, `entities`, and `objects`: `room` is an exact room descriptor with a room marker for `explore.look`, `entities` is a bounded list of at most 32 present character/NPC/monster descriptors each carrying an opaque identity, bounded display name, bounded kind, and nullable opaque `portrait_ref`, and `objects` is a bounded list of at most 32 present object descriptors carrying an opaque identity and bounded display name

#### Scenario: Interact targets carry exactly their four fields and a bounded affordance list
- **WHEN** the presenter builds `interact`
- **THEN** it is a bounded list of at most 32 present target descriptors, each carrying exactly `identity`, `display_name`, nullable `portrait_ref`, and a bounded `affordances` list of at most 8 descriptors
- **AND** a target descriptor carries no keyword list and no other field, because a conversation's topics reach the browser only through the `dialogue` panel's `choices` once the conversation is open

#### Scenario: An action affordance carries exactly its five fields
- **WHEN** the presenter serializes an action affordance
- **THEN** it contains exactly `kind` (`"action"`), `action_id`, `label`, `enabled`, and nullable `disabled_reason`

#### Scenario: Accepted actions derive from the shared allowlist minus in-conversation codes
- **WHEN** the panel's accepted-action enumeration is assembled
- **THEN** it is derived from the shared `ACTION_CODE_ALLOWLIST` rather than a private duplicate, minus the two in-conversation codes `explore.talk_scripted` and `explore.talk_freeform`, which never appear on any target descriptor
- **AND** the target affordances the presenter emits are drawn from `explore.talk_open`, `explore.party_invite`, `explore.party_leave`, `explore.engage`, `explore.possess`, `explore.possess_release`, and `explore.deliver`, which is exactly the client mirror's target-scoped action list

#### Scenario: Only the deliver affordance carries params
- **WHEN** the presenter emits target action affordances
- **THEN** exactly the `explore.deliver` action affordance additionally carries `params` — the shared delivery validator's normalized dispatch payload (`npc_id` and the bounded ASCII `item_key`) — and every other action affordance carries no `params`, its dispatch payload being re-derived from the target identity at the dock

#### Scenario: A navigation affordance carries exactly its five fields and opens only a drawer
- **WHEN** the presenter serializes a navigation affordance
- **THEN** it contains exactly `kind` (`"navigate"`), `surface` (one of `"guild"` or `"shop"`), `label`, `enabled`, and nullable `disabled_reason`
- **AND** navigation affordances are dock-navigation descriptors only — they are NOT registered action adapters, never enter a `ui_action` payload, and only tell the browser to open the corresponding service drawer

#### Scenario: Availability entries carry only the available boolean
- **WHEN** the presenter builds `character`, `quests`, and `inventory`
- **THEN** each is an availability entry with exactly `available` (boolean): `character` is available in exploration mode, and `quests`/`inventory` are available only when the `services` panel is registered and available

#### Scenario: A vocabulary-emitted possession entry never raises in the presenter
- **WHEN** the panel is rendered for a room whose legal vocabulary entries include a possession affordance
- **THEN** the presenter does not raise: the entry is either serialized as an accepted target affordance or folded into the target's single conversation affordance, so a bound companion standing in the room can never degrade the panel from within

#### Scenario: The presenter stays read-only over canonical data
- **WHEN** the `exploration` presenter builds its payload
- **THEN** it is built only from canonical room, entity, component, object, and service data, emits no live object or filesystem reference, does not mutate location, traits, knowledge, dialogue, quests, inventory, or world time, and uses the registered common unavailable form outside exploration mode

#### Scenario: Available schema versions cut over together
- **WHEN** either validator receives an available exploration panel with schema version 4, and then otherwise identical panels with version 3 or another unsupported version
- **THEN** only version 4 is accepted, including its non-null reference fields, and no dual-version conversion is performed

### Requirement: Portrait focus stays client-local against the art catalog seam
Exploration interact and look-entity descriptors SHALL carry null or a 1..32-character ASCII-decimal `portrait_ref`. Non-null refs SHALL name an entry in the current bounded server art view whose canonical resolution supplies its own runtime or official image. The browser SHALL use supplied catalog values without constructing subject keys or URLs or sending focus messages.

#### Scenario: Absence of art never blocks exploration
- **WHEN** the art catalog is absent or a descriptor carries `portrait_ref: null`
- **THEN** look, interact, and dialogue operate normally, and no portrait card or focus packet is produced

#### Scenario: Catalog-driven focus is verified
- **WHEN** the server supplies a `portrait_catalog` and an exploration descriptor references a catalog identity
- **THEN** client-local focus switches only to that server-verified value and no subject key or URL is constructed by the browser

#### Scenario: Missing art is never a failure
- **WHEN** a descriptor carries `portrait_ref: null` or the catalog is absent
- **THEN** it is not treated as a failure; look, interact, and dialogue proceed normally with no portrait card

#### Scenario: Both descriptor paths join the same current image
- **WHEN** a present interact target also has a look-entity row, belongs to the current capped art view and resolves to an eligible real official or runtime portrait
- **THEN** both rows carry the same server-authored catalog ref, and the normally rendered art catalog entry at that ref carries that resolved image

#### Scenario: A non-interact entity can carry an admitted portrait
- **WHEN** a present named-policy character is catalogued with real imagery and appears only in the look-entity list
- **THEN** its entity row carries the catalog reference while its existing look payload and bystander eligibility remain unchanged

#### Scenario: Catalog exclusion remains a truthful null
- **WHEN** an entity is excluded from the existing art membership or dropped by its 32-entry cap, including a non-catalogued monster with otherwise resolvable art
- **THEN** its exploration reference is null and no catalog expansion or browser-generated key occurs

#### Scenario: Missing and ineligible imagery never becomes a real reference
- **WHEN** a catalogued entity resolves to missing, pending, failed, malformed-policy, age-ineligible or silhouette-only art without its own runtime/official media URL
- **THEN** its descriptor carries null, no generation or gameplay mutation occurs, and exploration remains usable

#### Scenario: Exact validators preserve admitted reference values
- **WHEN** either descriptor carries null or an ASCII-decimal reference of length 1 or 32, and then an empty, overlong, numeric, Unicode-digit, subject-key or URL-like value
- **THEN** both validators accept and preserve the first values and reject the latter values without coercion; exact fields and envelope bounds still apply

#### Scenario: Available exploration survives unavailable art
- **WHEN** the art capability cannot supply its view or the client receives an unavailable art panel
- **THEN** exploration actions remain available, refs without a supplied view are null and unresolved client refs use the established fallback without a focus request
