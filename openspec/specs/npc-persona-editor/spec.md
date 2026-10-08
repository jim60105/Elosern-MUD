## Purpose

Let the authenticated player, as an author, read and replace the complete compact card of an NPC standing with their active character through two allowlisted, re-authorized, version-checked browser actions, without exposing card data anywhere else.

## Requirements

### Requirement: Author editing admits only a co-located NPC for the session's own active character
The `npc.persona.read` and `npc.persona.update` actions SHALL resolve the actor only from the authenticated session's current, activated, account-owned puppet and SHALL admit it only in exploration or dialogue mode. The `npc_id` SHALL be re-resolved on every request from the actor's current location contents and SHALL be admitted only when it names an NPC-family instance. Author editing SHALL NOT require a conversation, affinity, or schedule slot.

#### Scenario: A co-located NPC is readable in exploration and dialogue
- **WHEN** an activated character standing with an NPC that carries a valid card submits `npc.persona.read` in exploration mode, and again while in a dialogue session with a different NPC
- **THEN** both reads succeed for that NPC without any conversation, affinity, or schedule requirement

#### Scenario: Forbidden targets are rejected without data
- **WHEN** the actor submits either action for a forged id, another account's player character, a monster, an NPC in another room, or an NPC deleted after it was read
- **THEN** the result is rejected with `npc_persona.no_target`, carries no data, and nothing is written

#### Scenario: Forbidden modes are rejected
- **WHEN** the actor is creation-pending, in an active combat session, or a possessed NPC
- **THEN** both actions are rejected with `npc_persona.not_allowed` and nothing is written

#### Scenario: A target that left after the read cannot be saved
- **WHEN** the actor reads an NPC's card, the NPC then moves to another room, and the actor submits an update
- **THEN** the update is rejected with `npc_persona.no_target` and the card is unchanged

#### Scenario: Forbidden actor states are rejected with not_allowed
- **WHEN** the actor is creation-pending, an actor in an active combat session, or a possessed NPC acting as the puppet
- **THEN** the action is rejected with `npc_persona.not_allowed`

#### Scenario: Every non-NPC identity is rejected with no_target
- **WHEN** `npc_id` names an unknown, forged, remote, departed, or deleted identity, a player character (including another account's), a `Monster`, or any other object
- **THEN** the action is rejected with `npc_persona.no_target`

### Requirement: npc.persona.read returns a private editor snapshot with the offline greeting
`npc.persona.read` SHALL accept a payload of exactly `npc_id`. On success it SHALL return a result whose `data` holds exactly `npc_id`, `display_name`, `npc_title`, `persona_version`, `persona`, `offline_greeting`, and `default_greeting`, where `persona` is the complete normalized seven-field card with `identity` holding `public` and `hidden`. Reading SHALL never initialize or repair a card, and SHALL change no game state, clock, currency, quest knowledge, relationship, or party state.

#### Scenario: A read returns the seven-key snapshot
- **WHEN** the actor reads a co-located table-backed NPC whose card is at version 3, whose offline-greeting field holds an authored line, and whose dialogue table authors a greeting
- **THEN** the success data has exactly the seven fields with `persona_version` 3, `persona.identity.hidden` the stored hidden identity, `offline_greeting` the stored field text, and `default_greeting` the table greeting

#### Scenario: A profile-backed NPC previews its profile greeting
- **WHEN** the actor reads an NPC with no dialogue table whose profile provenance names a profile authoring a greeting, and whose field is empty
- **THEN** `offline_greeting` is `""`, `default_greeting` is the profile greeting, and nothing is written

#### Scenario: Both greetings are empty for an unseeded free-form NPC
- **WHEN** the actor reads a free-form NPC with no dialogue table, no profile greeting, and no offline-greeting field
- **THEN** the success data has `offline_greeting` and `default_greeting` both `""` and nothing is written

#### Scenario: An uninitialized NPC is unavailable
- **WHEN** the actor reads a co-located NPC with no persona metadata
- **THEN** the result is rejected with `npc_persona.unavailable`, carries no data, and nothing is written

#### Scenario: The payload id is a positive safe integer
- **WHEN** a `npc.persona.read` payload is validated
- **THEN** `npc_id` must be a positive integer within the protocol safe-integer range and never a boolean

#### Scenario: offline_greeting echoes the stored field verbatim
- **WHEN** a read succeeds
- **THEN** `offline_greeting` is the NPC's stored offline-greeting field verbatim (`""` when unset, never initialized or repaired)

#### Scenario: default_greeting follows the resolver's authored precedence
- **WHEN** a read resolves `default_greeting`
- **THEN** it is the read-only authored presentation default resolved at read time through the same precedence the no-keyword greeting resolver applies below the instance field — the scripted dialogue-table greeting when the NPC has a table authoring one, else the authored profile greeting named by the NPC's profile provenance, else `""`

#### Scenario: The default preview is presentation-only
- **WHEN** a read returns `default_greeting`
- **THEN** it is presentation data and is not copied into the stored field, so an authored table or profile line stays live for every NPC whose field is empty

#### Scenario: The result stays inside protocol limits
- **WHEN** a read result is serialized
- **THEN** the seven-key result stays within the protocol's result-data field maximum of eight, and every valid payload including CJK and escape-heavy text stays within the protocol's per-string and envelope byte limits

#### Scenario: An invalid card is unavailable, never repaired
- **WHEN** the actor reads an NPC whose card or persona metadata is missing or invalid
- **THEN** the read is rejected with `npc_persona.unavailable` and the card is never initialized or repaired

#### Scenario: Greeting keys follow the editor privacy rule
- **WHEN** a read returns either greeting key
- **THEN** both greeting keys are editor data under the existing privacy rule: only the requesting session's result carries them, ordinary snapshots do not, and no card or greeting prose enters logs or narrative output

### Requirement: npc.persona.update replaces the card and offline greeting under a version check
`npc.persona.update` SHALL accept a payload of exactly `npc_id`, `expected_persona_version`, `persona`, and the optional `offline_greeting`. It SHALL submit card and greeting as one atomic version-checked replacement through the deterministic NPC persona service and SHALL NOT assign entity attributes itself or call any player-persona editing API. A changed card, a changed greeting, or both SHALL return success with the seven-field read data at a version advanced exactly once.

#### Scenario: A save changes only the selected NPC
- **WHEN** two NPCs were initialized from the same profile and the actor saves a changed card or greeting for one of them
- **THEN** only that NPC's card, greeting field, and version change, and the world clock, wallet, quests, relationships, and party are byte-identical

#### Scenario: Two sessions cannot overwrite each other
- **WHEN** two sessions read the same card at version 4, the first saves a change, and the second saves its own change with expected version 4
- **THEN** the second is rejected with `npc_persona.version_conflict` naming version 5 and the first session's card remains stored

#### Scenario: A field violation names the leaf
- **WHEN** the actor saves a card whose `speech_style` is empty
- **THEN** the result is rejected with `npc_persona.required_empty.speech_style`, carries no data, and the stored card is unchanged

#### Scenario: A malformed payload never reaches the adapter
- **WHEN** a client submits an update whose persona lacks `habit`, carries an extra key, whose offline greeting is a number, or whose expected version is `true`
- **THEN** the dispatcher rejects it as `malformed_payload` without invoking the adapter

#### Scenario: A greeting-only save advances the version once
- **WHEN** the actor saves the identical card with one changed offline greeting at the expected version
- **THEN** the success data shows the new greeting and a version advanced by exactly one, and only that NPC changed

#### Scenario: Clearing the field restores the authored default
- **WHEN** the actor saves the identical card with an empty `offline_greeting` over a non-empty stored field
- **THEN** the success data shows `offline_greeting` `""`, the version advanced by one, the NPC's authored table/profile default is untouched, and the no-keyword greeting resolver answers that default again

#### Scenario: An invalid greeting is rejected without writing
- **WHEN** the actor submits an `offline_greeting` over 300 code points or containing a newline after normalization
- **THEN** the result is rejected with `npc_persona.greeting_invalid`, carries no data, and neither card nor field changed

#### Scenario: An in-flight exchange sees a greeting-only edit as stale
- **WHEN** an asynchronous dialogue exchange captured version N and the actor saves a greeting-only change before settlement
- **THEN** the stale-persona completion gate rejects the exchange's settlement through the existing stale-persona outcome

#### Scenario: The update payload shape is exact
- **WHEN** an `npc.persona.update` payload is validated
- **THEN** `expected_persona_version` is a positive safe integer, never a boolean; `persona` is an object with exactly the seven card keys, `identity` with exactly `public` and `hidden`, every leaf a string; and the optional `offline_greeting` is a string

#### Scenario: The greeting bound and empty-clear are enforced at intake
- **WHEN** an `offline_greeting` passes the card contract's text normalization
- **THEN** it must hold at most 300 code points and no newline, and an absent or empty value stores the field empty, clearing any override

#### Scenario: An identical save is a versioned no-op
- **WHEN** the submitted payload is identical in both card and greeting
- **THEN** the result is success at the unchanged version

#### Scenario: Rejections name their cause and write nothing
- **WHEN** an update is rejected
- **THEN** a version mismatch is rejected with `npc_persona.version_conflict` and a message naming the current version; a card contract violation with a field-specific code `npc_persona.<reason>[.<leaf>]` and a message naming the field label; an over-bound or multi-line `offline_greeting` with `npc_persona.greeting_invalid` and a message naming the 離線問候語 field; an unavailable or uninitialized NPC with `npc_persona.unavailable`; and every rejection carries no data and writes nothing

#### Scenario: A greeting change shares the card's version gate
- **WHEN** an offline-greeting change is stored
- **THEN** it advances the same `persona_version` as the card, so the stale-persona completion gate invalidates an in-flight dialogue exchange on a greeting-only edit

#### Scenario: A greeting change never writes back to authored sources
- **WHEN** an offline-greeting change is stored
- **THEN** it affects only the selected NPC and does not write back to any preset, profile, or dialogue table

#### Scenario: Mutations are single-flight and idempotent per request ID
- **WHEN** a session has an in-flight mutation or retries a request ID
- **THEN** in-flight mutations stay single-flight per session and a retried request ID returns the cached result

### Requirement: Card data reaches only the requesting session
Only the success result of `npc.persona.read` or `npc.persona.update` SHALL carry the private editor card and offline/default greeting fields, and only to the requesting session. No editor action message, narrative output, operational event, or analytics record SHALL include card or greeting-field text; error results SHALL carry no `data`.

#### Scenario: Snapshots never carry the card
- **WHEN** a full snapshot is published for an actor standing with an NPC whose hidden identity is set
- **THEN** no panel contains any card leaf text

#### Scenario: Logs never carry the card
- **WHEN** a read and an update succeed and a third request is rejected for a field violation
- **THEN** no captured operational event context or editor action message contains any card leaf or greeting-field text

#### Scenario: Maximal valid cards fit the protocol
- **WHEN** valid cards at the total budget, together with a 300-code-point offline greeting and a default greeting, built from CJK text, astral characters, and JSON-escape-heavy characters are returned as success data
- **THEN** both the server result validator and the browser protocol mirror accept the envelope

#### Scenario: Intentional public greeting does not disclose the editor snapshot
- **WHEN** an NPC with private hidden identity and an edited greeting opens or degrades a conversation
- **THEN** its selected greeting is intentionally presented publicly as speech/session text without any card leaf, editor greeting key, default preview, or private author payload

#### Scenario: Presentation panels never carry card data
- **WHEN** exploration, dialogue, or any other presentation panel renders
- **THEN** it carries no card text, hidden identity, or the editor's greeting keys

#### Scenario: The public greeting is the narrow disclosure exception
- **WHEN** the no-keyword/degraded greeting resolver selects a greeting for intentional public speech
- **THEN** speech output and the dialogue-session/panel line carry the selected greeting only, rendered as literal text when sourced from the editable instance field, never the full editor payload or other card text

#### Scenario: Result data keys and limits are fixed
- **WHEN** an editor success result is serialized
- **THEN** it uses only fixed lowercase keys, uses `persona_version` rather than any reserved state key, and fits the protocol's result-data field, string, and byte limits for every valid payload, including maximal cards and maximal 300-code-point greetings of CJK text, astral characters, and JSON-escaped characters

### Requirement: The browser mirrors the card contract exactly
The browser SHALL carry a DOM-independent mirror of the compact card contract and of the bounded offline-greeting rule, and SHALL produce the same accept or reject decision and reason, and the same rendered card total, as the server contract for every case of the shared boundary fixtures. The mirror SHALL NOT relax any global protocol limit.

#### Scenario: Shared boundary cases agree across languages
- **WHEN** the shared card and offline-greeting boundary fixtures are evaluated by the server contract tests and by the browser mirror's Node tests
- **THEN** every case yields the same decision, reason code, leaf, and (for valid cards that declare one) rendered total in both

#### Scenario: The greeting bound is exact
- **WHEN** an offline greeting of exactly 300 code points, one of 301 code points, and one whose normalized text still contains a newline are evaluated by both contracts
- **THEN** the first is accepted and the other two are rejected as `greeting_invalid` in both

#### Scenario: The mirror covers every contract dimension
- **WHEN** the browser mirror is inspected
- **THEN** it covers the compact card contract's field set, normalization, code-point counting, per-leaf, identity-section, and total bounds, the exact rendering labels and separators the server counts, and stable reason codes

#### Scenario: The mirrored greeting rule is the bounded one
- **WHEN** the browser mirror evaluates an offline greeting
- **THEN** it applies the bounded rule of 300 code points after normalization, no newline, empty allowed

### Requirement: Persona target admission revalidates current room visibility
Both persona actions SHALL resolve the target from the actor's currently visible co-located NPC-family candidates on every request. Visibility SHALL follow the same existing room visibility policy as ordinary room appearance. A target denied either check SHALL be treated as absent with `npc_persona.no_target`, the ordinary generic missing-target message, and no result data or private target details.

#### Scenario: View-denied NPC cannot expose its card
- **WHEN** an ordinary authenticated activated actor submits read or update for a co-located NPC whose view access denies that actor
- **THEN** both requests reject as `npc_persona.no_target` without card, hidden identity, greeting, target name or version data and with no persisted change

#### Scenario: Search denial also blocks author access
- **WHEN** a co-located NPC allows view but denies search to the actor
- **THEN** read and update reject with the same non-disclosing missing-target outcome

#### Scenario: Visibility lost after opening invalidates save
- **WHEN** an actor reads a visible NPC and view or search access becomes denied before update
- **THEN** update rejects as absent without changing persona, greeting or version

#### Scenario: Visible sleeping NPC remains author-editable
- **WHEN** ordinary view access permits a co-located NPC, its search lock is absent under the standard permissive search default, and its schedule blocks talking
- **THEN** persona read and valid version-checked update succeed for the authorized actor without requiring a conversation or schedule permission

#### Scenario: Visibility spans view and search authorization
- **WHEN** persona target visibility is evaluated
- **THEN** it includes view and search authorization and the policy's default semantics and overrides

#### Scenario: Visibility is additive, never a replacement
- **WHEN** visibility is applied to a persona request
- **THEN** it does not replace authenticated active account-owned character admission, NPC-family validation, possession/mode gates, or revalidation on update, and does not introduce a talk-schedule requirement

### Requirement: NPC editor mirror equality includes normalized card and greeting text
Browser and server SHALL produce exactly the same normalized strings, acceptance/rejection reason and offending leaf, code-point counts, and valid labeled-card totals under the NPC contract's explicit finite boundary-whitespace and CRLF normalization policy. Complete normalized card plus offline greeting equality SHALL define a no-op. The server SHALL check the submitted expected version before accepting even an equal submission.

#### Scenario: Astral and boundary characters agree at limits
- **WHEN** shared fixtures combine enumerated boundary characters, astral characters, and preserved interior/excluded characters at 600-leaf, 600-identity, 2000-card or 300-greeting limits and just beyond them
- **THEN** both runtimes produce identical normalized values, counts and accept/reject field reasons

#### Scenario: Boundary-only resave is a no-op
- **WHEN** a current-version submission differs from stored card/greeting only by outer members of the explicit boundary set or CRLF versus LF card line endings
- **THEN** normalized equality succeeds unchanged and persona version does not advance

#### Scenario: Clear advances once and stale equality still rejects
- **WHEN** optional hidden/social/greeting content is cleared using only boundary whitespace and that normalized empty submission is repeated
- **THEN** the first actual clear advances once, the current-version repeat is unchanged, and a stale-version repeat rejects as version conflict without writing

#### Scenario: Equality covers both identity leaves and optional clears
- **WHEN** a submission's normalized card plus offline greeting equals the stored state and differs only in identity leaves or optional-clear content
- **THEN** the equality no-op rule still defines it as a no-op

#### Scenario: Mirrors touch neither persona rules nor protocol limits
- **WHEN** either mirror enforces the NPC editor contract
- **THEN** it alters no generic player persona rules and relaxes no protocol limit
