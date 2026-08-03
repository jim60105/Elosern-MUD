## Purpose

Exact combat context actions panel, keyboard menu, allowlisted combat adapters, shared side-effect-free availability, EventLog delivery, and active-combat reconnect for the browser WebClient, with full Telnet parity.

## Requirements

### Requirement: Combat context actions are an exact read-only panel
The production presentation registry SHALL register `context_actions` schema version 1. For a valid active combat session, its available payload SHALL contain exactly `schema_version`, `available`, `kind`, `session`, `participants`, `root_actions`, `secondary_actions`, and `skills`; `available` SHALL be true and `kind` SHALL be `combat`. `session` SHALL contain exactly `session_id`, `mode`, `round`, `state`, and `reason`: session ID SHALL be bounded, mode SHALL be `hostile` or `guild_exam`, round SHALL be a non-negative safe integer, state SHALL be `ready` or `recovery`, and reason SHALL be null or an exact object containing stable code and safe Traditional Chinese message. A ready session SHALL have a null reason; a recovery session SHALL have a non-null reason, no cast/flee action, and one confirmed Forfeit descriptor when its record is strictly parsed. The presenter SHALL strictly read and reconstruct the authenticated puppet's current `CombatSessionRecord`, SHALL preserve persisted participant order, SHALL emit no live object or filesystem reference, and SHALL NOT mutate traits, resources, buffs, sexual state, battlefield state, session state, quests, location, or world time. Outside combat it SHALL use the registered common unavailable form rather than fabricate exploration actions.

#### Scenario: Active session produces canonical combat presentation
- **WHEN** a puppeted WebClient in a valid persistent combat session receives a full snapshot
- **THEN** `context_actions` reports that session's ID, mode, round, ordered participants, and current actions while a before/after comparison of canonical game state is unchanged

#### Scenario: Exploration does not receive fake combat actions
- **WHEN** the active puppet has no combat session
- **THEN** `context_actions` uses its schema-valid unavailable form and contains no Attack, skill, target, Flee, or Forfeit descriptor

#### Scenario: Presenter failure remains isolated
- **WHEN** combat presentation raises while status and narrative remain healthy
- **THEN** only `context_actions` becomes correlated unavailable, status still renders, and normal text output remains usable

### Requirement: Combat presentation enumerates complete deterministic choices
The combat panel SHALL list each unique owned active `SkillDef` in `SkillHandler.owned_keys()` order after passive filtering, including innate skills, without alphabetical reordering. Each skill descriptor SHALL contain its stable key, registry label and description, exact resource cost, target specification, nullable element key, enabled state, nullable stable disabled reason, ordered valid participant IDs, and applicable approved AREA shorthands. Participants SHALL be ordered from `player_ids` then `enemy_ids` and SHALL contain a positive opaque identity, stable session token, bounded display name, team, living/fled/knocked-out state, current/maximum HP, and nullable server-authored portrait reference. Lists and strings SHALL have explicit bounds and the serialized envelope SHALL remain within the OOB protocol limit.

#### Scenario: Stored skill order and passive exclusion are preserved
- **WHEN** a player owns active skills in the stored order `wind_blade`, `fire_ball` and also owns a passive skill
- **THEN** the panel lists those active skills in that order, excludes the passive, and retains innate active skills in their deterministic handler order

#### Scenario: Unavailable skill remains visible
- **WHEN** an owned active skill lacks resources, has no valid target, has an unavailable effect handler, or the actor cannot act
- **THEN** its descriptor remains focusable with `enabled: false`, one stable code, and a Traditional Chinese explanation derived from the rules preview

#### Scenario: Participant presentation does not anticipate art
- **WHEN** combat presentation is built before the art-panel change exists
- **THEN** every participant has `portrait_ref: null`, and neither the server nor browser constructs a portrait subject key or URL

### Requirement: Availability uses shared side-effect-free rules preview
The combat presenter, Telnet action listing, and combat adapters SHALL consume the same deterministic preview boundary. Availability SHALL include ownership and active kind, resources, exact target shape, presence/alive/range/faction candidate checks, action capability including `actions_per_turn == 0`, effect-handler availability, and time metadata. Preview state is advisory; every submitted action SHALL repeat authoritative validation against current canonical state before initiative.

#### Scenario: Preview and adapter agree on a disabled skill
- **WHEN** a skill is displayed as disabled because SP is insufficient and a modified client nevertheless submits it at the current presentation revision
- **THEN** the adapter rejects with the matching stable rule reason before initiative, no NPC acts, and round count and world time remain unchanged

#### Scenario: State can change after a valid preview
- **WHEN** a skill was enabled in revision N but canonical target state changes before its revision-N submission is admitted
- **THEN** current domain validation rejects or filters it according to target rules without trusting the earlier descriptor

### Requirement: The combat action dock follows the approved keyboard hierarchy
In combat mode the action root SHALL present Attack, Skills, Items, Defend, and Flee in that stable order, with confirmed Forfeit under a secondary menu. Attack SHALL select targets for innate `basic_attack`; Skills SHALL open the complete active-skill list; Items and Defend SHALL remain focusable but disabled with code `not_implemented`; Flee SHALL invoke the innate flee path; and Forfeit SHALL require an explicit confirmation screen. Arrow keys SHALL navigate, Enter SHALL open or submit, Escape SHALL pop one level, and disabled entries SHALL send no packet.

#### Scenario: Basic attack completes without typed input
- **WHEN** a player uses only arrows and Enter to choose Attack and one valid enemy
- **THEN** the browser submits `combat.cast` for `basic_attack` exactly once and the ordinary combat-session path resolves the result

#### Scenario: Placeholder mechanics cannot be invoked
- **WHEN** the player focuses Items or Defend and presses Enter
- **THEN** its `not_implemented` explanation remains readable and no `ui_action` message is emitted

#### Scenario: Forfeit requires confirmation
- **WHEN** the player opens the secondary Forfeit entry but has not confirmed
- **THEN** no mutation is sent, and Escape returns exactly one menu level without ending combat

### Requirement: Combat target selection sends one shape per TargetSpec
The browser SHALL derive target controls only from the validated skill descriptor. NONE SHALL submit no target field. SELF SHALL display the authenticated actor binding but submit no target field. SINGLE SHALL submit `target_ids` containing exactly one server-provided identity. AREA SHALL let Space toggle unique server-provided candidates and Enter submit either a nonempty explicit `target_ids` list or one mutually exclusive approved `target_shorthand`. Focus and selection SHALL remain client-local until submission, and a panel replacement SHALL remove vanished selections and restore the nearest surviving focus in deterministic order.

#### Scenario: SELF binds without an actor field
- **WHEN** the player submits an enabled SELF skill
- **THEN** the payload contains `skill_key` and no actor, participant, target ID, or shorthand field, and the server binds the authenticated puppet

#### Scenario: AREA multi-selection is explicit and unique
- **WHEN** the player toggles two valid AREA candidates with Space and confirms
- **THEN** one request carries those two distinct server-provided IDs in presenter order and carries no shorthand

#### Scenario: AREA shorthand is mutually exclusive
- **WHEN** the player chooses the server-authored `all-enemies` descriptor
- **THEN** one request carries that shorthand and no target-ID field

### Requirement: Production combat actions are narrow and server-authoritative
The production action registry SHALL register exactly `combat.cast`, `combat.flee`, and `combat.forfeit` for this delivery unit in addition to no unrelated gameplay adapter. `combat.cast` SHALL accept only the TargetSpec-dependent exact payload forms and SHALL reject the reserved `flee` skill key; `combat.flee` SHALL accept exactly an empty object; and `combat.forfeit` SHALL accept exactly the current bounded session ID as a stale-selection guard. Every adapter SHALL obtain the actor from the authenticated session, re-read the active session, re-resolve referenced IDs from its participants, invoke a public combat-session API, and SHALL NOT assign `.db`, traits, buffs, sexual state, location, quests, wallet, inventory, or battlefield members directly.

#### Scenario: Tampered remote target cannot enter combat resolution
- **WHEN** `combat.cast` carries a valid ObjectDB ID that is not a participant in the authenticated actor's current session
- **THEN** the adapter rejects before preflight or initiative and no state changes

#### Scenario: Flee cannot select another actor
- **WHEN** a client submits `combat.flee`
- **THEN** the adapter builds the innate SELF request for the session puppet and accepts no actor or target field

#### Scenario: Flee has only one graphical action path
- **WHEN** a modified client submits `combat.cast` with `skill_key` equal to `flee`
- **THEN** the cast adapter rejects before session submission and only the exact empty `combat.flee` action can request the innate flee path

#### Scenario: Stale Forfeit confirmation cannot end a replacement session
- **WHEN** a Forfeit payload names a session ID that no longer equals the actor's active record
- **THEN** the adapter rejects without settling or clearing the current session

### Requirement: Combat results update canonical panels and preserve narrative logs
After an admitted combat action settles, the server SHALL emit every returned EventLog and terminal message through Evennia's ordinary escaped text output path. The dispatcher SHALL then publish canonical `status` and `context_actions` replacements at one newer revision before sending the matching safe `ui_action_result`. The browser SHALL keep submission locked until that declared presentation revision is accepted. It SHALL NOT parse narrative prose to update resources, participants, round, or menu state.

#### Scenario: One combat round updates text and panels
- **WHEN** an accepted cast completes a nonterminal round
- **THEN** every committed EventLog appears in narrative, status and combat choices reflect committed state at one newer revision, and the dock unlocks only after that revision is accepted

#### Scenario: Rejected preflight emits no fabricated combat prose
- **WHEN** current deterministic validation rejects before initiative
- **THEN** no combat EventLog is fabricated, the result contains a stable safe reason, and refreshed panel state permits another legal choice

#### Scenario: Duplicate request does not repeat a round or prose
- **WHEN** one live request ID is delivered twice
- **THEN** the adapter and combat round execute once, EventLog text is emitted once, and the duplicate receives the cached result

### Requirement: Reconnect rebuilds combat without replaying intent
WebSocket loss SHALL preserve the last rendered combat view under the foundation offline overlay and lock every combat mutation. After reconnect, the first valid new-epoch snapshot SHALL rebuild the current session ID, mode, round, participants, status, skills, targets, and root menu from canonical persistence even when its revision is lower than the retired epoch. The browser SHALL discard old-epoch packets, SHALL NOT restore an unsubmitted target selection as authority, and SHALL NOT resubmit an uncertain prior mutation.

#### Scenario: Active combat reconnect resumes the same round boundary
- **WHEN** transport disconnects after a valid nonterminal round and reconnects without another game action
- **THEN** the new snapshot shows the same persisted session and round, starts at the combat root, and no additional round or world time is consumed

#### Scenario: Disconnect after submit never retries
- **WHEN** transport closes after sending a cast but before its result is observed
- **THEN** reconnect synchronizes canonical combat state, displays the uncertain-result notice, and sends no automatic replacement cast

#### Scenario: Unreconstructable participant offers safe recovery
- **WHEN** a strictly parsed active record references a participant that can no longer be reconstructed
- **THEN** combat presentation exposes a bounded recovery state with no cast or flee action, retains confirmed Forfeit and ordinary text access, and performs no mutation while rendering

### Requirement: Combat browser acceptance is keyboard-only and desktop-bounded
The managed localhost Playwright suite SHALL exercise basic attack, active skill selection, NONE, SELF, SINGLE, AREA explicit and shorthand targeting, Flee, Forfeit confirmation, disabled reasons, stale and duplicate submission behavior, EventLog narrative delivery, and active-session reconnect. At 1440x900 and 1280x720, narrative, true HP/MP/SP status, applied modifier text, and the active action controls SHALL remain visible and usable. Tests SHALL use deterministic fixtures and SHALL make no remote, LLM, or image-generation request.

#### Scenario: Complete target matrix passes in Chromium
- **WHEN** the required browser entry point runs against deterministic skills covering all four TargetSpec values
- **THEN** every flow completes using keyboard controls and each emitted action has its exact expected payload shape

#### Scenario: Minimum viewport retains combat essentials
- **WHEN** combat renders at 1280x720 with a disabled skill focused
- **THEN** the player can read narrative, numeric resources, applied modifiers, the disabled reason, and action controls without overlap preventing operation
