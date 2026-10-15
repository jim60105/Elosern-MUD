# Spec Delta

## MODIFIED Requirements

### Requirement: Action identity comes only from the authenticated session
The dispatcher SHALL accept actions only from authenticated WebSocket sessions with an active puppet and SHALL pass only session.puppet as the commander. Only the exact guarded combat schemas SHALL accept subordinate actor_id and active session_id references, reauthorized through the deterministic party boundary; they SHALL NOT select account, puppet or transport identity. All other unknown actor/account/session/puppet identity fields SHALL reject, and no error response SHALL disclose another actor's state.

#### Scenario: Payload cannot select a different actor
- **WHEN** a client includes an actor-like unknown field in the envelope or outside an exact guarded combat payload
- **THEN** exact-schema validation rejects the request without adapter invocation

#### Scenario: Unpuppeted action is rejected
- **WHEN** an anonymous or logged-in but unpuppeted session submits `ui_action`
- **THEN** no adapter runs and no character state is returned

#### Scenario: Guarded party actor reference is subordinate authorization
- **WHEN** combat.command names an actor_id and active session_id under the authenticated commander
- **THEN** the dispatcher passes only the puppet commander and rules reauthorize the referenced allied actor; enemies/other sessions reject without leaking state


### Requirement: Action registries are allowlisted and duplicate-safe

The action registry SHALL bind each stable action ID to one exact payload validator and one adapter, SHALL reject duplicate registration, and SHALL reject unknown action IDs. The production registry SHALL contain exactly the action-ID groups enumerated in the scenarios below, each action ID with its own exact validator and deterministic adapter.

#### Scenario: Unknown action cannot become a command

- **WHEN** a client submits an unregistered action ID or a string resembling an Evennia command
- **THEN** the dispatcher rejects it with a schema-valid `ui_action_result` (outcome `rejected`, stable code `unknown_action`) carrying the request ID, and it is not routed through the text command parser

#### Scenario: Malformed action payload rejects without a protocol error

- **WHEN** a client submits a globally valid `ui_action` envelope whose registered action payload fails its exact schema
- **THEN** the dispatcher sends a schema-valid `ui_action_result` (outcome `rejected`, stable code `malformed_payload`) without invoking the adapter and without emitting a `ui_protocol_error`

#### Scenario: Duplicate action registration fails

- **WHEN** two adapters attempt to register the same action ID
- **THEN** registry construction fails rather than selecting one by registration order

#### Scenario: Production registry exposes only specified combat, service, inventory, creation, exploration, dismiss, title, and persona mutations

- **WHEN** the production registry is loaded after the practice-webclient, gallery management, personal official-art preference, correspondence, NPC author-editor, dream-sleep-surface and SkillBook casting changes
- **THEN** its action IDs are exactly `account.character.create`, `account.character.switch`, `combat.actor_choices`, `combat.command`, `combat.exit_prompt`, `combat.exit_confirm`, `guild.register`, `guild.quest_accept`, `guild.quest_abandon`, `guild.quest_turnin`, `guild.quest_track`, `guild.exam_request`, `shop.buy`, `shop.sell`, `inventory.use`, `inventory.toggle_equip`, `creation.preset`, `creation.custom`, `creation.concept`, `creation.roll_name`, `creation.activate`, `creation.reset`, `explore.move`, `explore.look`, `explore.talk_open`, `explore.talk_scripted`, `explore.talk_freeform`, `explore.dialogue_leave`, `explore.party_invite`, `explore.party_leave`, `explore.engage`, `explore.wait`, `explore.practice`, `explore.possess`, `explore.possess_release`, `explore.deliver`, `explore.skill_preview`, `explore.cast`, `options.dismiss`, `title.accept`, `title.decline`, `title.equip`, `title.remove`, `character.persona.update`, `npc.persona.read`, `npc.persona.update`,
`gallery.subject.select`, `gallery.generate`, `gallery.default.set`, `gallery.card.delete`, `gallery.face_rect.update`, `gallery.binding.save`, `gallery.stage.update`,
`gallery.official.select`, `gallery.official.clear_selection`, `gallery.official.geometry.set`, `gallery.official.geometry.clear`,
`letters.list`, `letters.collect`, `letters.read`, `letters.send`, `dream.say`,
`dream.draft`, `dream.confirm`, and `dream.awaken`, each with its own exact
validator and deterministic adapter

#### Scenario: Test proof action remains isolated

- **WHEN** a dispatcher test installs a synthetic proof adapter
- **THEN** that adapter exists only in the test-owned registry and does not appear in the production registry

#### Scenario: Skill preview is not a cast

- **WHEN** the two SkillBook action IDs are resolved through the production registry
- **THEN** each has its own exact validator/adapter, preview selection makes no canonical gameplay mutation, and field casting executes only through its deterministic entry

#### Scenario: Production registry composition is fixed

- **WHEN** the production registry is built
- **THEN** it contains the two account adapters `account.character.create` and `account.character.switch`, the four combat adapters `combat.actor_choices`, `combat.command`, `combat.exit_prompt`, and `combat.exit_confirm`, the eight service adapters `guild.register`, `guild.quest_accept`, `guild.quest_abandon`, `guild.quest_turnin`, `guild.quest_track`, `guild.exam_request`, `shop.buy`, and `shop.sell`, the two inventory adapters `inventory.use` and `inventory.toggle_equip`, the six creation adapters `creation.preset`, `creation.custom`, `creation.concept`, `creation.roll_name`, `creation.activate`, and `creation.reset`, the sixteen exploration adapters `explore.move`, `explore.look`, `explore.talk_open`, `explore.talk_scripted`, `explore.talk_freeform`, `explore.dialogue_leave`, `explore.party_invite`, `explore.party_leave`, `explore.engage`, `explore.wait`, `explore.practice`, `explore.possess`, `explore.possess_release`, `explore.deliver`, `explore.skill_preview`, and `explore.cast`, the two title ballot adapters `title.accept` and `title.decline`, the two title codex adapters `title.equip` and `title.remove`, the persona adapter `character.persona.update`, the two NPC author-editor adapters `npc.persona.read` and `npc.persona.update`, the `options.dismiss` action, the four correspondence adapters `letters.list`, `letters.collect`, `letters.read`, and `letters.send`, the seven gallery management adapters `gallery.subject.select`, `gallery.generate`, `gallery.default.set`, `gallery.card.delete`, `gallery.face_rect.update`, `gallery.binding.save`, and `gallery.stage.update`, the four personal official-art preference adapters `gallery.official.select`, `gallery.official.clear_selection`, `gallery.official.geometry.set`, and `gallery.official.geometry.clear`, and the four dream collaboration adapters `dream.say`, `dream.draft`, `dream.confirm`, and `dream.awaken`

#### Scenario: Skill preview and cast bypass the text parser

- **WHEN** `explore.skill_preview` or `explore.cast` is admitted
- **THEN** `explore.skill_preview` performs only epoch-scoped presentation selection and `explore.cast` performs field use through the deterministic core, and neither routes through the text command parser

## REMOVED Requirements

### Requirement: combat.cast payload carries an optional bounded scale
**Reason**: The approved party-combat design replaces this conflicting behavior.
**Migration**: Use the guarded skill command payload with the same TargetSpec and finite scale set, and remove combat.cast registration entirely. No compatibility route or data migration.


## ADDED Requirements

### Requirement: Guarded party skill commands retain exact scale validation
The skill payload inside combat.command SHALL accept optional scale exactly0.25,0.5,1,2,4 with absent default1 for every existing target form. Boolean, nonnumeric and nonmember scales SHALL reject malformed_payload. Current actor mastery/capability SHALL revalidate before any complete round starts.

#### Scenario: Scale parity and forbidden capability
- **WHEN** a companion submits scale2 on SINGLE or AREA and a different actor lacks the mastery
- **THEN** valid shapes preserve scale2 in the draft while the unauthorized scale rejects before initiative without resource/time change


