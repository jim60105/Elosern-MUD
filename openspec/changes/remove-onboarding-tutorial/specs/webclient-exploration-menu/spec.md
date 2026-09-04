# Delta: webclient-exploration-menu

## RENAMED Requirements

- FROM: `### Requirement: explore.look reuses the command appearance path and preserves onboarding look hooks`
- TO: `### Requirement: explore.look reuses the command appearance path`

## MODIFIED Requirements

### Requirement: Exploration affordances are server-authored, never inferred from prose
Every `interact` affordance SHALL be derived from canonical data with the same checks commands use, never from typeclass names, display prose, or other heuristics. `explore.talk_scripted` SHALL be offered only for a present NPC with a resolved dialogue component (`ScriptedDialogue`); the target descriptor then SHALL carry a bounded list of at most 16 scripted keyword descriptors (each exactly `keyword_id` and bounded `label`) derived from the dialogue table registry, and the talk_scripted affordance itself SHALL carry no keyword list (the scripted buttons live on the target so the interact payload stays within the protocol's global JSON-depth bound). `explore.talk_freeform` SHALL be offered only for a present NPC with an eligible free-form dialogue surface (an `LLMNPC`). `explore.party_invite` SHALL be offered only for a present NPC with an eligible free-form dialogue surface (an `LLMNPC`) that is not already a companion of the actor, SHALL be enabled when the actor's party has fewer than 4 companions and disabled with the full-party reason otherwise, and SHALL never be offered for an already-bound companion (the leave affordance covers it). `explore.party_leave` SHALL be offered only for a present NPC that is currently a bound companion of the actor. `explore.engage` SHALL be offered only for a present living hostile `Monster` when the actor has no active combat session. A `navigate`-kind service affordance (`surface` `"guild"` or `"shop"`) SHALL be offered only when the current room has exactly one unambiguous `GuildStaff` or `Merchant` host for a service the actor can use, and it opens the corresponding services submenu rather than inventing a mutation. No affordance SHALL reference a remote, absent, or ambiguous host or target. Every adapter SHALL re-verify at commit time, against the actor's current location and current canonical state, the affordance that produced its descriptor — presence in the actor's location, the exact typeclass/component/eligibility, and the unchanged keyword, party, or host condition — so a target removed from the room, type-changed, or no longer eligible between render and submit is rejected before the display, dialogue, invite, leave, or engage API is called and before any memory, intent, party, session, or time state changes.

#### Scenario: A scripted host exposes its authored keywords
- **WHEN** a present NPC carries a `ScriptedDialogue` component with two authored keywords
- **THEN** its interact descriptor offers `explore.talk_scripted` with exactly those two keyword buttons and no free-form affordance

#### Scenario: A generative NPC offers free-form talk
- **WHEN** a present `LLMNPC` is in the room
- **THEN** its interact descriptor offers `explore.talk_freeform` and, when it also carries a scripted component, the scripted affordance as well

#### Scenario: An unbound generative NPC offers an invite
- **WHEN** a present `LLMNPC` is not a companion of the actor and the party has room
- **THEN** its interact descriptor offers `explore.party_invite` enabled; with four companions already the affordance is disabled with the full-party reason

#### Scenario: A bound companion offers leave instead of invite
- **WHEN** a present NPC is currently a companion of the actor
- **THEN** its interact descriptor offers `explore.party_leave` and never an `explore.party_invite`

#### Scenario: A living hostile monster offers engage
- **WHEN** a present living `Monster` is in the room and the actor has no active session
- **THEN** its interact descriptor offers `explore.engage`; an already-engaged actor receives no engage affordance

#### Scenario: No affordance is fabricated for a plain NPC
- **WHEN** a present NPC carries neither a dialogue component nor an eligible free-form surface nor a party binding
- **THEN** its interact descriptor contains no talk, invite, leave, or service affordance, and the browser renders only the descriptors the server sent

### Requirement: explore.look reuses the command appearance path
The production action registry SHALL register `explore.look`. Its payload SHALL accept exactly one of `room` (the exact boolean true) or `target_id` (a positive integer). The adapter SHALL obtain the actor from the authenticated session, re-resolve `target_id` against the actor's current location's present contents when given — never from a stored, remote, or ambiguous reference — and re-verify presence and ordinary display/access rules, and route the look through the same appearance path the `look` command uses — for the room marker, `PlayerCharacter.at_look(actor.location)`, and for a target, the ordinary target display path. The adapter SHALL present the returned appearance through the escaped text output path, SHALL NOT parse the text to infer state, SHALL NOT mutate traits, knowledge, location, or time, and SHALL publish no panel replacement beyond the ordinary result. A missing, remote, unpermitted, or no-longer-present target SHALL reject with a stable code and message.

#### Scenario: Looking at a present entity uses ordinary display rules
- **WHEN** an actor submits `explore.look` with a present target's `target_id`
- **THEN** the actor receives that entity's ordinary appearance text and no canonical state changes

#### Scenario: A tampered target cannot be inspected
- **WHEN** an actor submits `explore.look` with a `target_id` that is not present or not permitted
- **THEN** the adapter rejects with a stable reason, no appearance is emitted, and no canonical state changes

### Requirement: explore.talk_scripted invokes the deterministic dialogue API with keyword buttons
The production action registry SHALL register `explore.talk_scripted`. Its payload SHALL accept exactly `npc_id` (a positive integer) and `keyword_id` (a 1..64-character non-empty string). The adapter SHALL obtain the actor from the authenticated session, re-resolve the NPC from the actor's current location's present contents — never a stored, remote, or ambiguous reference — and re-verify presence, a resolved dialogue component, and the keyword's presence in the host's dialogue table, and then call the read-only `world.rules.dialogue` response API — the same deterministic seam the `talk` command uses — so a `ScriptedDialogue` host answers through the authored tables with the same state effects as the command path. The adapter SHALL present the authored response through the escaped text path, SHALL NOT invent a response, and SHALL NOT assign dialogue or component state directly. A missing NPC, a no-longer-present NPC, a non-host, an unregistered keyword, or a present-but-unreachable NPC SHALL reject with a stable code and message and SHALL NOT write state.

#### Scenario: Scripted keyword buttons match authored behavior
- **WHEN** an actor submits `explore.talk_scripted` for a present dialogue host with a registered keyword
- **THEN** the player receives the authored response exactly as `talk` would produce it

#### Scenario: An unregistered keyword rejects without writing
- **WHEN** an actor submits a `keyword_id` absent from the host's dialogue table
- **THEN** the adapter rejects with a stable reason, no response is fabricated, and no state is written

#### Scenario: A no-longer-present NPC rejects before any dialogue API
- **WHEN** an actor submits `explore.talk_scripted` for an NPC that was present at render but has since left the room
- **THEN** the adapter re-resolves the NPC from the actor's current location, rejects with a stable reason before calling the dialogue API, and no memory or component state changes

### Requirement: Exploration actions reject stale, duplicate, and tampered input without mutation
Every exploration action SHALL pass the existing dispatcher's epoch, base revision, in-flight, and request-ID checks before adapter invocation; a `presentation_epoch` or `base_revision` mismatch SHALL return the dispatcher's `stale` outcome with a fresh full snapshot and SHALL invoke no adapter. A duplicate live request ID SHALL return its cached result without re-executing. After those checks, commit-time domain revalidation is authoritative: an exit, NPC, monster, keyword, or daypart that changed between render and submit is handled against current canonical state, and a tampered `exit_ref`, `current_node`, `npc_id`, `monster_id`, `keyword_id`, `speech`, `daypart`, or `seconds` that fails current revalidation SHALL be rejected with a stable code and Traditional Chinese message with no location, time, knowledge, dialogue, quest, inventory, combat, or memory change. A transport drop after submit SHALL NOT be auto-retried; reconnect SHALL rebuild the dock from the new-epoch full snapshot and display the uncertain-result notice.

#### Scenario: Stale revision cannot move or talk twice
- **WHEN** an older-revision `explore.move` or `explore.talk_freeform` is submitted after a newer revision is active
- **THEN** the dispatcher returns outcome `stale`, calls no adapter, and emits a full snapshot without changing location, clock, or dialogue

#### Scenario: Tampered exit or NPC references perform nothing
- **WHEN** a tampered `exit_ref`/`current_node` or `npc_id` fails current domain revalidation
- **THEN** the adapter rejects before any traversal, dialogue, or time advance, and canonical state is unchanged

#### Scenario: A target that left the room rejects at commit time
- **WHEN** an NPC, monster, or object referenced by `explore.look`, `explore.talk_scripted`, `explore.talk_freeform`, or `explore.engage` was present at render but has left the actor's location (or changed type/eligibility) by submit
- **THEN** the adapter re-resolves it from the actor's current location's present contents, rejects with a stable reason before the display, dialogue, or engage API is invoked, and no memory, intent, session, or time state changes

#### Scenario: Reconnect rebuilds exploration without replaying intent
- **WHEN** the transport disconnects after sending `explore.talk_freeform` and reconnects without another action
- **THEN** the new-epoch snapshot rebuilds the dock from canonical location, knowledge, and NPC state, the uncertain-result notice is shown, and no dialogue or mutation is automatically replayed

### Requirement: Exploration browser acceptance is keyboard-only and desktop-bounded
The managed localhost Playwright suite SHALL exercise, using keyboard controls only at 1440x900 and 1280x720: grid, wilderness, instance, and interior movement through `explore.move` with matching time and map updates; look at the room and look at present entities; scripted keyword dialogue and free-form dialogue with offline degrade to greeting/silence; engage transitioning to the combat dock; wait/rest daypart and duration acceptance plus safety rejections; stale, duplicate, and tampered rejections; service submenus reachable through Quests/Inventory; and reconnect retention. Tests SHALL use deterministic fixtures, SHALL make no remote, LLM, or image-generation request, SHALL assert that no take/drop control and no remote or ambiguous host control is rendered, and SHALL assert that `portrait_ref: null` produces no portrait card and no focus packet.

#### Scenario: A full exploration journey completes in Chromium
- **WHEN** a seeded actor uses arrows and Enter to move through an exit, look at the room, talk to a scripted host, open Quests, and wait until dawn
- **THEN** each step submits exactly one expected `ui_action`, the narrative and panels refresh together, and no typed command is required

#### Scenario: Offline dialogue still completes in the browser
- **WHEN** the LLM is offline and the player chooses free-form dialogue for an `LLMNPC`
- **THEN** the authored greeting or silence appears, the dock unlocks, and no remote request is made

#### Scenario: No take or drop control is rendered
- **WHEN** the exploration dock is open in any room
- **THEN** no `explore.take`/`explore.drop` affordance or generic object-mutation control exists anywhere in the rendered surface
