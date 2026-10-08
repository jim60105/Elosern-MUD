# webclient-character-roster Specification

## Purpose
The committed account-level roster read model — which characters an account owns, which one is live, each row's portrait resolution, the capacity facts, and the switch-lock state.

## Requirements

### Requirement: The account roster is a committed presentation panel available in every mode
The system SHALL register a `roster` presentation panel whose subject is the account owning the
rendered puppet, rather than the puppet itself, and SHALL render it in every full snapshot. The
panel SHALL be available in creation, exploration, combat, and dialogue mode alike and SHALL NOT
gate its availability on the actor's `creation_pending` marker.

#### Scenario: The roster rides every snapshot
- **WHEN** a full snapshot is built for a puppeted session
- **THEN** the snapshot carries a `roster` panel alongside the existing panels

#### Scenario: The roster is available during character creation
- **WHEN** a snapshot is built for an actor whose `creation_pending` marker is set
- **THEN** the snapshot's mode is `creation` and the `roster` panel is still available with the
  account's full character list

#### Scenario: The roster is available in combat
- **WHEN** a snapshot is built for an actor in an active combat session
- **THEN** the snapshot's mode is `combat` and the `roster` panel is still available

#### Scenario: An unreadable account degrades rather than emptying
- **WHEN** the rendering actor has no resolvable owning account
- **THEN** the `roster` panel carries the common unavailable form with a stable non-internal
  reason and no correlation ID, and carries no character rows

#### Scenario: An abandoned creation wizard still shows the returnable characters
- **WHEN** a player abandoned a creation wizard and a snapshot is built for them
- **THEN** the roster is available and names the characters they can return to, because availability is never gated on the actor's `creation_pending` marker

#### Scenario: A character list unreadable without mutation degrades rather than emptying
- **WHEN** the account's character list cannot be read without mutation
- **THEN** the `roster` panel reports the common non-internal unavailable form rather than an empty roster

#### Scenario: An unreadable account is never presented as an empty account
- **WHEN** the rendering actor's owning account cannot be read
- **THEN** the panel reports the common unavailable form, so an unreadable account is never presented as an account with no characters

### Requirement: Each roster row reports only canonical, owned character facts
Each row of the `roster` panel SHALL correspond to exactly one character in the authenticated
session puppet's owning account's character list, and SHALL carry that character's stable numeric
identity, current object key, current marker, creation-pending marker and portrait resolution.
Normally `current` SHALL identify the live owned puppet. Rows SHALL be ordered by ascending
numeric identity.

#### Scenario: Rows name the account's characters in identity order
- **WHEN** an account owns three characters and a snapshot is built for one of them
- **THEN** the roster carries three identity-ordered rows and exactly one current owned character

#### Scenario: A pending sibling appears as a pending row
- **WHEN** an account owns one activated character and one character pending creation
- **THEN** both appear, and only the pending character carries the pending marker

#### Scenario: The roster states nothing about a character's condition
- **WHEN** a row's character has low health, another location or a status condition
- **THEN** the row carries no resource, location or condition field

#### Scenario: A foreign character never appears
- **WHEN** a character outside the authenticated session's account exists
- **THEN** it appears in no roster row, including through a possessed NPC's owner back-reference

#### Scenario: Possession preserves A's current roster portrait
- **WHEN** A possesses bound companion B and the session puppet changes to B
- **THEN** the roster stays available from that session's account, A remains its sole current row with byte-identical portrait and pending fields, B is not a roster row, and release restores the same roster

#### Scenario: Identity order never depends on handler iteration order
- **WHEN** the account's character list is presented
- **THEN** the presented order is fixed by ascending numeric identity and never depends on handler iteration order

#### Scenario: The current character is not reordered to the front
- **WHEN** the current owned character's numeric identity is not the smallest
- **THEN** it keeps its identity-ordered position and is identified as current by its own field rather than by position

#### Scenario: Possession keeps the owning character A current, not the NPC B
- **WHEN** A possesses bound companion B
- **THEN** `current` identifies the owning player character A whose body/portrait remains in the lineup, not the controlled NPC B, and B is not added to the account roster

#### Scenario: The possession owner must agree with the canonical binding
- **WHEN** the roster resolves a possessed session's owner
- **THEN** the live party owner and the canonical `possessed_by` binding agree, and A is still verified against that same account's character list

#### Scenario: A broken possession owner degrades the panel
- **WHEN** the possession owner is missing, stale, unbound or foreign
- **THEN** the panel produces the existing unavailable form and never selects a different account from the NPC's back-reference

#### Scenario: Possession leaves each pending marker alone
- **WHEN** a session is possessing a bound companion
- **THEN** `pending` remains each owned character's own creation marker, unchanged by possession

#### Scenario: Row count is bounded by a presenter-owned constant
- **WHEN** an account owns more characters than the presenter's bound
- **THEN** the row count stays within a presenter-owned constant independent of configured capacity, and the current owned character is preserved within that bound

#### Scenario: A row states who the character is, not how they are doing
- **WHEN** a roster row is built
- **THEN** it carries no last-played field, alongside the already-absent resource, location and condition fields

#### Scenario: An ambiguous key earns no synthesized label
- **WHEN** a character's key is ambiguous
- **THEN** the panel synthesizes no display label; pending is the disambiguating fact, and its presentation belongs to the client

#### Scenario: The wire shape stays unchanged apart from the origin discriminator
- **WHEN** the roster's portrait vocabulary gains the server-authored origin discriminator added by the `official-art-resolution` capability
- **THEN** it is one bounded enum field on the portrait object, and portrait resolution, the roster wire shape, the row's own facts and every other field stay read-only and exactly as they are

### Requirement: Roster portraits resolve through the named-portrait subject mechanism
Each roster row's portrait SHALL be resolved through the same named-portrait resolution the art
panel's portrait catalog uses: an explicit named `portrait_policy` on the character, the
canonical-age eligibility check, and the resolved asset or its placeholder. Resolution SHALL NOT
require the character to be present in the rendering actor's current room.

#### Scenario: An activated character resolves its generated portrait
- **WHEN** a roster row is built for an activated character whose portrait asset is complete
- **THEN** the row carries that portrait's subject key, done status, and same-origin media URL,
  regardless of which room the character is standing in

#### Scenario: A pending character resolves to the no-portrait placeholder
- **WHEN** a roster row is built for a character still pending creation
- **THEN** the row carries the no-portrait placeholder with a null URL and a null subject key

#### Scenario: A not-yet-generated portrait resolves to its pending placeholder
- **WHEN** a roster row is built for an activated character whose portrait asset has not been
  generated yet
- **THEN** the row carries the placeholder descriptor and the asset's pending status rather than
  a URL

#### Scenario: A resolved roster row carries its face rectangle
- **WHEN** a roster row is built for an activated character that resolves to an image
- **THEN** the row carries the media URL and a face rectangle of exactly `x`, `y`, `w`, `h` in `[0, 1]`

#### Scenario: A placeholder roster row carries a null face rectangle
- **WHEN** a roster row resolves to any truthful placeholder
- **THEN** the row carries a null URL and a null face rectangle

#### Scenario: An official-resolved roster portrait names its origin
- **WHEN** a roster row's portrait resolves to an official read-only image through the presentation chain
- **THEN** the row carries the official-origin discriminator beside its media URL and the subject's own generation state remains untouched

#### Scenario: A roster row carries the catalog's portrait vocabulary
- **WHEN** a roster row carries a portrait
- **THEN** it carries the same portrait field vocabulary the art panel's catalog entries carry — the subject key, the asset status, the same-origin media URL, the aspect ratio, the alt text, the placeholder descriptor, and the normalized face rectangle
- **AND** the client renders roster portraits through its existing portrait treatment rather than a second vocabulary

#### Scenario: The face rectangle is normalized or null
- **WHEN** a roster row's face rectangle is serialized
- **THEN** it is a mapping of exactly `x`, `y`, `w`, `h` in `[0, 1]` when the row carries a URL, and `null` when it carries a placeholder

#### Scenario: Every media-bearing row names its portrait origin
- **WHEN** a roster row carries a media value
- **THEN** it also carries the server-authored portrait origin discriminator (see the `official-art-resolution` capability)

#### Scenario: Only activation establishes a portrait policy
- **WHEN** a character still pending creation carries no named portrait policy, because the policy is established only at activation
- **THEN** its portrait resolves to the no-portrait placeholder with no URL and no subject key

### Requirement: The roster carries the account's capacity and switch-lock facts
The `roster` panel SHALL carry, computed once per snapshot from canonical state: the configured
maximum number of characters the account may hold, whether another character may be created (the
account's character count is below that maximum), whether switching characters is currently
blocked, and, when it is blocked, one stable Traditional Chinese reason. Switching SHALL be
reported as blocked exactly when the rendering actor is in an active combat session.

#### Scenario: An account below the cap may create
- **WHEN** the account holds fewer characters than its configured maximum
- **THEN** the panel reports that maximum and permits creation

#### Scenario: An account at the cap may not create
- **WHEN** the account holds exactly its configured maximum
- **THEN** the panel reports that another character may not be created

#### Scenario: Combat blocks switching for the whole roster
- **WHEN** the rendering actor is in an active combat session
- **THEN** switching is blocked with the existing stable reason, never a per-row lock

#### Scenario: The lock clears when the session ends
- **WHEN** the rendering actor's combat session ends and the next snapshot is built
- **THEN** switching is unblocked and its reason is null

#### Scenario: Possession preserves the existing lock semantics
- **WHEN** B is the possessed session actor while A is roster-current
- **THEN** switch_locked and lock_reason follow B's existing combat predicate, while current/pending/portraits and capacity remain account-owned facts

#### Scenario: The switch lock shares the movement predicate
- **WHEN** the panel decides whether switching is blocked
- **THEN** it uses the same active-combat-session predicate that blocks the actor's movement and resolves the `combat` snapshot mode

#### Scenario: The lock is snapshot-wide with one shared reason
- **WHEN** switching is reported as blocked
- **THEN** the lock is one snapshot-wide fact with one shared reason, never a per-row status field

#### Scenario: The capacity and lock fields are advisory only
- **WHEN** an action acts on the panel's capacity or lock fields
- **THEN** those fields are advisory presentation state and not authorization for any state change, and the action re-evaluates the same predicates server-side at admission

#### Scenario: Possession alone never adds a switch lock
- **WHEN** a session is possessing bound companion B while A is roster-current
- **THEN** the rendering actor for this combat predicate remains B, not roster-current A, and possession alone adds no switch lock or new reason

#### Scenario: A possessed NPC consumes no character slot
- **WHEN** possession is active
- **THEN** capacity remains the authenticated account's owned-character count and the possessed NPC does not consume a character slot

### Requirement: Roster presentation is read-only and version-mirrored
Building the `roster` panel SHALL NOT write canonical state, SHALL NOT lazily construct a trait,
buff, or sexual handler on any listed character, and SHALL NOT read disguised stats or persona.
The panel's schema version SHALL be declared as a single server-side constant in its presenter
module, registered from that constant, and mirrored by the client's panel allowlist and per-panel
available-form re-check under the same dual-direction parity contract every other panel obeys.

#### Scenario: Rendering the roster mutates nothing
- **WHEN** a full snapshot including the `roster` panel is built for an account owning several
  characters
- **THEN** no listed character's traits, attributes, location, or handlers are created or changed,
  and the world-clock tick is unchanged

#### Scenario: The roster version stays equal across server and client
- **WHEN** the panel-version parity contract runs
- **THEN** the roster presenter module's constant, the registry's registered value, the client
  allowlist's mirrored value, and the client available-form re-check literal are all equal

### Requirement: Switching characters is an allowlisted account-scoped action
The production action registry SHALL register the account-scoped action
`account.character.switch`, accepting exactly `character_id`, a positive integer excluding
booleans. The adapter SHALL obtain the account from the authenticated session's own puppet and
SHALL resolve `character_id` only against that account's character list — never through a
world-wide object search and never through a permission-based fallback.

#### Scenario: A foreign character id is refused
- **WHEN** `account.character.switch` is submitted with the identity of a character owned by a
  different account
- **THEN** the action is rejected as an invalid character, no puppet change is scheduled, and no
  data about that character is returned

#### Scenario: A malformed payload never reaches the adapter
- **WHEN** `account.character.switch` is submitted with a missing, non-integer, boolean, negative,
  or extra field
- **THEN** the dispatcher returns the malformed-payload rejection and no adapter runs

#### Scenario: No foreign character is reachable through this surface
- **WHEN** any `account.character.switch` request is processed
- **THEN** no character outside the acting account is reachable through this surface

#### Scenario: Switching bypasses the text command parser
- **WHEN** `account.character.switch` is dispatched
- **THEN** neither the action identifier nor its payload is routed through the text command parser

### Requirement: A character-changing action reports its decision before its transition
An account-scoped action whose effect is a puppet change SHALL make every authorization decision
synchronously at admission, and its action result SHALL report the outcome of that decision. It
SHALL NOT perform the puppet transition inside the adapter: the transition SHALL be scheduled to
run after the completion result has been sent and both the server in-flight marker and the
browser's mutation lock have been released.

#### Scenario: A successful switch leaves no uncertain mutation
- **WHEN** a player switches to another owned character
- **THEN** the browser receives the success result and releases its mutation lock, then the detach
  signal, then the new puppet's fresh-epoch snapshot, and the mutation is not marked uncertain

#### Scenario: The result precedes the detach signal
- **WHEN** an accepted `account.character.switch` completes
- **THEN** its exact `ui_action_result` for that request identifier is delivered before any
  no-puppet protocol error, and no in-flight request is outstanding when the detach signal arrives

#### Scenario: A rejected action schedules nothing
- **WHEN** the action is rejected for any reason
- **THEN** the session keeps its current puppet, its presentation epoch is unchanged, and no
  transition is scheduled

#### Scenario: The transition is deferred because it retires the result's sequence
- **WHEN** the adapter decides whether to run the puppet transition inline
- **THEN** it defers, because the transition retires the very sequence the result would be published into

#### Scenario: Wire order is result, detach, then fresh snapshot
- **WHEN** an accepted character-changing action completes
- **THEN** the message order on the wire is the action result first, then the client's detach signal, then a fresh-epoch full snapshot for the new puppet

#### Scenario: A success is not an uncertain outcome
- **WHEN** a character-changing action reports success
- **THEN** the client does not mark it as an uncertain outcome

### Requirement: A scheduled puppet transition verifies its outcome and recovers explicitly
A scheduled puppet transition SHALL re-validate its decision against committed state before
acting, and after attempting the puppet change SHALL verify that the session actually holds the
requested character. On any failure — failed re-validation, a raised error, or a failed
verification — the transition SHALL take the highest applicable recovery step and SHALL NOT
report success or fall silent.

#### Scenario: A silent puppeting refusal keeps the current character
- **WHEN** the puppeting API refuses the requested character by returning without raising, before
  releasing the current one
- **THEN** the session still holds its previous character, the player is told the switch did not
  happen, and a fresh snapshot for that character is published

#### Scenario: A refusal after the previous character was released is repaired
- **WHEN** the puppeting API releases the previous character and then refuses the requested one
- **THEN** the transition re-attaches the previous character, verifies it, logs at error severity,
  informs the player, and publishes a fresh snapshot for that character

#### Scenario: An unrecoverable transition tells the player they hold no character
- **WHEN** re-attaching the previous character also fails
- **THEN** the session holds no character, an error-severity event carrying the account, session,
  previous-character, and target identities is emitted, the player is told explicitly that they are
  playing no character and how to return, and no snapshot is published

#### Scenario: A failed re-validation changes nothing at all
- **WHEN** the target is no longer owned, or the character entered combat, between the result and
  the scheduled transition
- **THEN** no detach signal, puppet change, or snapshot occurs beyond the recovery message and the
  current character's own refreshed snapshot

#### Scenario: A guard refusal leaves the current character attached
- **WHEN** the puppeting API's own guard refuses the transition's unpuppet
- **THEN** the current character stays attached, because the transition SHALL NOT unpuppet the session's current character as a separate preparatory step: the puppeting API's own guards SHALL own that unpuppet

#### Scenario: Verification guards against a silent refusal
- **WHEN** the transition verifies the session's puppet after the change
- **THEN** verification is required because the puppeting API can refuse silently — returning without raising — including after it has already released the previous character

#### Scenario: Recovery step one keeps and re-presents the previous character
- **WHEN** a failure leaves the session still holding its previous character
- **THEN** the transition logs the failure, tells the player in Traditional Chinese that the switch did not happen and which character they are still playing, and publishes a fresh snapshot for that character

#### Scenario: Recovery step two re-attaches the released character
- **WHEN** a failure leaves the session holding no character
- **THEN** the transition attempts to re-attach the previous character and, on success, proceeds as in recovery step one while logging at error severity

#### Scenario: Recovery step three leaves no character and says so
- **WHEN** re-attachment also fails
- **THEN** the session is left with no character, the failure is logged at error severity with the account, session, previous-character, and target identities, and the player is told explicitly that they are no longer playing any character and how to return
- **AND** no snapshot is published in this state, because there is no character to render

### Requirement: The switch action publishes no completion snapshot
`account.character.switch` SHALL declare no affected panels and SHALL emit no completion
presentation with its result. A successful action's canonical state reaches the client through the
transition's own fresh snapshot; a rejected action changes nothing and SHALL NOT trigger a full
snapshot, so a switch refused while the character-creation surface is open cannot re-render that
surface and discard the player's unsaved draft edits.

#### Scenario: A rejection does not disturb an open creation form
- **WHEN** a player with unsaved creation-wizard form edits triggers a rejected
  `account.character.switch`
- **THEN** the rejection result arrives with no panel update and no full snapshot, and the form
  edits are untouched

#### Scenario: A success emits no completion presentation
- **WHEN** an accepted `account.character.switch` completes
- **THEN** exactly one presentation follows it — the transition's fresh-epoch full snapshot — and
  no update or snapshot is published at the retiring epoch

### Requirement: Switching is refused for a foreign, current, or combat-locked target
`account.character.switch` SHALL reject with the stable code `invalid_character` when
`character_id` does not resolve to a member of the acting account's character list, with
`in_combat` when the session's current puppet is in an active combat session, and with
`already_current` when `character_id` is already the session's live puppet. Each rejection SHALL
carry a stable code and a safe Traditional Chinese message and SHALL change no state.

#### Scenario: Combat blocks switching
- **WHEN** a player in an active combat session submits `account.character.switch` for another
  owned character
- **THEN** the action is rejected with the `in_combat` code, the puppet is unchanged, and the
  combat session is unaffected

#### Scenario: A stale click after the lock appears is still refused
- **WHEN** the client submits a switch based on a roster snapshot rendered before combat began
- **THEN** the server re-derives the combat predicate and rejects the request, rather than trusting
  the panel's advisory field

#### Scenario: Switching to the current character is refused
- **WHEN** `account.character.switch` names the session's live puppet
- **THEN** the action is rejected with the `already_current` code and the session is untouched

#### Scenario: A current-target rejection is a rejection, not a hollow success
- **WHEN** the action evaluates a target that is already the session's live puppet
- **THEN** `already_current` is a rejection rather than a success, because a success would tell the client a transition is coming that will never arrive

#### Scenario: The combat check reuses the movement predicate
- **WHEN** the action evaluates the combat condition
- **THEN** it is evaluated from the same active-combat-session predicate that blocks the character's movement, and the roster panel's advisory lock field is never the authorization

### Requirement: A puppet change carries no session-scoped state across characters
A transition performed by an account-scoped action SHALL leave the retiring character's
session-scoped presentation state behind: the previous character's action-options state and
dismissal barriers, its transient creation concept proposal, and its completed-result cache and
in-flight marker SHALL NOT be visible to or reusable by the new puppet. Per-character persistent
state SHALL remain on the character it belongs to and SHALL be unchanged by the switch.

#### Scenario: The new puppet inherits no suggestion state
- **WHEN** a player with committed action-option cards switches to another character
- **THEN** the new puppet's first snapshot carries no card, fingerprint, or dismissal barrier from
  the previous character

#### Scenario: An in-flight generation cannot cross the switch
- **WHEN** an action-options generation started for the previous character settles after the switch
  completes
- **THEN** it publishes no panel state or result into the new character's sequence

#### Scenario: Per-character persistent state stays with its character
- **WHEN** a player switches away from a character holding quest progress and a party binding, and
  later switches back
- **THEN** that character's quest progress and party binding are unchanged

#### Scenario: An in-flight generation for the old character publishes nowhere
- **WHEN** a generation is still in flight for the previous character when the switch lands
- **THEN** it publishes nothing into the new sequence

#### Scenario: Dialogue sessions are persistent per-character state
- **WHEN** a player switches away from a character holding a dialogue session
- **THEN** the dialogue session — like party and companion bindings and quest progress — remains on the character it belongs to, unchanged by the switch

### Requirement: Creating a character is an allowlisted account-scoped action
The production action registry SHALL register the account-scoped action
`account.character.create`, accepting exactly an empty payload and following switching's
decide-synchronously / schedule-the-transition contract. It SHALL reject with the stable code
`character_slots_full` when the account already holds the configured maximum, and with
`in_combat` when the session's current puppet is in an active combat session, each with a safe
Traditional Chinese message and no state change.

#### Scenario: A full account cannot create
- **WHEN** an account already holding the configured maximum submits `account.character.create`
- **THEN** the action is rejected with the `character_slots_full` code, no character object is
  created, no transition is scheduled, and the session keeps its current puppet

#### Scenario: Creating during combat is refused
- **WHEN** a player in an active combat session submits `account.character.create`
- **THEN** the action is rejected with the `in_combat` code and no character is created

#### Scenario: A rejection does not disturb an open creation form
- **WHEN** a player with unsaved creation-wizard form edits triggers a rejected
  `account.character.create`
- **THEN** the rejection result arrives with no panel update and no full snapshot, and the form
  edits are untouched

#### Scenario: Any payload field is refused before the adapter runs
- **WHEN** `account.character.create` is submitted with any field at all
- **THEN** the dispatcher's existing malformed-payload rejection refuses it before the adapter runs

#### Scenario: The adapter takes the account from its own puppet
- **WHEN** the create adapter runs
- **THEN** it obtains the account from the authenticated session's own puppet

#### Scenario: Creation declares no panels and no completion presentation
- **WHEN** `account.character.create` returns its result
- **THEN** it declares no affected panels and emits no completion presentation with its result

#### Scenario: Creation is refused in combat because it leaves the current character
- **WHEN** the create action evaluates an active combat session
- **THEN** it refuses with `in_combat` because creating a character leaves the current one

#### Scenario: The combat condition is re-derived, not read from the panel
- **WHEN** the create action evaluates the combat condition
- **THEN** it is re-derived from the active-combat-session predicate, never read from the roster panel's advisory field

#### Scenario: Creation bypasses the text command parser
- **WHEN** `account.character.create` is dispatched
- **THEN** neither the action identifier nor its payload is routed through the text command parser

### Requirement: The new character shell is created before the current character is left
The scheduled creation transition SHALL create the new character shell **before** sending the
client's detach signal or changing the session's puppet. When shell creation reports an error or
fails, the transition SHALL stop with nothing about the session changed — no detach signal, no
retired sequence, no puppet change — SHALL log the failure, and SHALL deliver one Traditional
Chinese line telling the player the character was not created.

#### Scenario: A capacity failure at transition time costs the player nothing
- **WHEN** the account's character-creation API reports a full account at transition time
- **THEN** the session keeps its current puppet and its presentation epoch, no detach signal is
  sent, the player is told the character was not created, and the failure is logged

#### Scenario: A shell that cannot be attached is kept, not destroyed
- **WHEN** a shell is created but the puppet attach fails and the recovery ladder runs
- **THEN** the shell still exists, still belongs to the account, and appears as a pending roster
  row that the switch action can enter

#### Scenario: A successful creation attaches and synchronizes
- **WHEN** an account below its capacity accepts `account.character.create`
- **THEN** the new shell is created, verified as the session's puppet, recorded as the account's
  last puppet, and a fresh-epoch full snapshot is published for it

#### Scenario: Creation orders the shell first for the authoritative capacity check
- **WHEN** the creation transition orders its steps
- **THEN** the shell is created first because the account's own character-creation API performs the authoritative capacity check and reports a full account by returning an error rather than raising

#### Scenario: An unattachable shell is a legitimate pending character
- **WHEN** a shell was created but could not be attached
- **THEN** it is left in place, not deleted: it is a legitimate pending character the account owns, it appears in the roster with its pending marker, and it can be entered later through the switch action

#### Scenario: The creation failure branch destroys nothing
- **WHEN** the creation transition fails at any step
- **THEN** the creation path performs no destructive write on its failure branch

#### Scenario: Attachment happens only once a shell exists
- **WHEN** shell creation has succeeded
- **THEN** only then does the transition attach the shell, through the same verified attach and recovery ladder the switch action uses

### Requirement: A newly created character enters the existing wizard and never resends the world introduction
The created shell SHALL receive the project's pending-creation marker through the account's own
post-creation hook, exactly as an account's first shell does, so the unchanged mode derivation
resolves the creation mode and the existing creation surface is presented with no client change.
The reusable creation start presentation SHALL be delivered for the new shell. The world
introduction SHALL NOT be delivered for any character after the account's first.

#### Scenario: A second character enters the creation wizard
- **WHEN** an account below its capacity accepts `account.character.create`
- **THEN** the new pending shell is puppeted and the following snapshot resolves the creation mode
  with the creation surface available

#### Scenario: The world introduction is not resent
- **WHEN** a second or later character is created mid-session
- **THEN** the player receives the creation start presentation and does not receive the world
  introduction

#### Scenario: The action writes no canonical identity
- **WHEN** a new shell is created through the action
- **THEN** its key is the account's own default, no identity attribute or trait was assigned by the
  action, and only the wizard's activation later renames it

#### Scenario: An abandoned new character is reachable again
- **WHEN** a player creates a second character, leaves its wizard unfinished, and switches back to
  a finished character
- **THEN** the unfinished character remains a pending roster row, and switching to it presents the
  creation surface again with its saved draft

#### Scenario: The action names no shell and writes no identity
- **WHEN** the create action builds a new shell
- **THEN** it assigns no identity attributes, traits, or the pending marker directly, and names the shell not: the creation wizard's activation remains the sole writer of a character's display name

#### Scenario: Introduction suppression is structural, not remembered
- **WHEN** a mid-session puppet change lands on a newly created shell
- **THEN** the world introduction is unreachable because it is reachable only from the login hook, which a mid-session puppet change does not run — rather than by an explicit suppression this action has to remember

### Requirement: The top band carries a character switcher rendered from the committed roster
The client SHALL render a character switcher in the stage's top band, beside the meta pill and
above the HUD island anchors, whenever the committed `roster` panel is available, in every
committed mode. Its collapsed form SHALL present the current character's portrait thumbnail and
name, both read from the roster row marked as current. When the `roster` panel is unavailable the
switcher SHALL render nothing at all.

#### Scenario: The collapsed pill names the live character
- **WHEN** a snapshot commits a roster whose current row names 艾莉亞
- **THEN** the collapsed switcher renders 艾莉亞's name and portrait thumbnail

#### Scenario: The switcher is present during character creation
- **WHEN** the committed mode is `creation` and the roster panel is available
- **THEN** the switcher renders, and its collapsed form names the pending character being created

#### Scenario: An unavailable roster renders no switcher
- **WHEN** the committed `roster` panel reports the unavailable form
- **THEN** no switcher element is rendered anywhere in the top band

#### Scenario: The collapsed form reads only from the roster
- **WHEN** the collapsed switcher renders the current character
- **THEN** its name and thumbnail come from the roster row marked as current — never from the status or character panel — so the collapsed form and the expanded list can never name different characters

#### Scenario: A long name truncates instead of growing the pill
- **WHEN** the current character's name is long
- **THEN** the width-bounded collapsed form truncates it rather than growing with it

#### Scenario: An unavailable roster renders no empty pill or placeholder
- **WHEN** the `roster` panel is unavailable
- **THEN** the switcher renders nothing at all: neither an empty pill nor a placeholder character

#### Scenario: An abandoned wizard player can return from creation mode
- **WHEN** a player who abandoned a creation wizard is in creation mode
- **THEN** the switcher renders so they can return to a finished character

### Requirement: The expanded switcher lists every roster row with one shared lock note
Activating the switcher SHALL open a list rendering one row per committed roster character, in
payload order, each carrying that row's portrait thumbnail and name. The row marked as current
SHALL be presented as selected and SHALL NOT be activatable. When the committed roster reports
switching as blocked, every non-current row SHALL render disabled under exactly one shared inline
note carrying the panel's own committed reason string.

#### Scenario: Rows render in committed order with the current one selected
- **WHEN** a roster commits three characters and the switcher is expanded
- **THEN** three rows render in payload order, the current one is marked selected and is not
  activatable, and the other two are activatable

#### Scenario: A combat lock disables every other row under one note
- **WHEN** the committed roster reports switching as blocked with a reason
- **THEN** every non-current row renders disabled, exactly one inline note renders that committed
  reason, and no per-row badge is present

#### Scenario: A pending sibling is marked, not renamed
- **WHEN** a roster row carries the pending marker
- **THEN** the row renders the committed name plus a stable in-creation marker, and the name itself
  is unmodified

#### Scenario: Escape closes exactly one level
- **WHEN** the switcher list is open and Escape is pressed
- **THEN** the list closes, no action is dispatched, and no other open surface is affected

#### Scenario: The top band does not grow when the list opens
- **WHEN** the switcher list opens at the minimum supported viewport
- **THEN** the top band's own rendered box is unchanged and the list overlays the island anchors

#### Scenario: A pending row is marked, never renamed by the client
- **WHEN** a row's committed pending marker is set
- **THEN** the row carries a stable in-creation marker and the client synthesizes no disambiguating display name for it

#### Scenario: The lock note is never per-row or client-composed
- **WHEN** switching is blocked and the list renders
- **THEN** the shared inline note carries the panel's own committed reason string — never a per-row badge and never client-composed reason text

#### Scenario: The list scrolls and overlays rather than growing
- **WHEN** the list opens
- **THEN** it is bounded in height with internal scrolling rather than growing the top band, and overlays the HUD islands transiently rather than displacing them

#### Scenario: The list closes on Escape, outside activation, or a new epoch
- **WHEN** Escape is pressed, an outside pointer activation occurs, or a new presentation epoch is committed
- **THEN** the list closes

### Requirement: Switching dispatches once and commits only on the server's snapshot
Activating an enabled, non-current row SHALL submit exactly one `account.character.switch`
carrying that row's committed identity, through the client's single dispatch entry and its
existing connected / locked / one-in-flight gates. The surface SHALL NOT optimistically mark the
chosen row as current: the presented current character changes only when a snapshot naming the
new puppet lands.

#### Scenario: Activating a row dispatches exactly one switch
- **WHEN** the player activates an enabled non-current row
- **THEN** exactly one `account.character.switch` request carrying that row's identity is
  submitted

#### Scenario: The selection does not move before the commit
- **WHEN** a switch has been dispatched but no new snapshot has been accepted
- **THEN** the collapsed pill and the selected row still name the previous character

#### Scenario: A disconnected switcher dispatches nothing
- **WHEN** the transport is lost or mutations are locked
- **THEN** every row and the create control render disabled and activating them submits nothing

#### Scenario: Keyboard activation matches pointer activation
- **WHEN** a row is activated from the keyboard
- **THEN** the same action identifier and payload are submitted through the same dispatch entry
  and the same gates apply

#### Scenario: Neither dispatch-only closing nor own debouncing
- **WHEN** a switch is dispatched
- **THEN** the surface does not close on dispatch alone and adds no debouncing of its own

#### Scenario: Locked or disconnected spans render everything disabled
- **WHEN** the client is disconnected or its mutations are locked — including throughout the transition between the two characters
- **THEN** every row and the create control render disabled and dispatch nothing

### Requirement: Creating a character is a confirmation-gated trailing control
The expanded list SHALL end with a create-character control. Activating it SHALL NOT dispatch: it
SHALL open an explicit confirmation stating that the current character will be left, with a cancel
control and a confirm control, and only the confirm control SHALL submit exactly one
`account.character.create` with an empty payload.

#### Scenario: Opening the create control submits nothing
- **WHEN** the player activates the create-character control
- **THEN** a confirmation with a cancel control and a confirm control renders and no action is
  submitted

#### Scenario: Confirming dispatches exactly one creation
- **WHEN** the player activates the confirm control
- **THEN** exactly one `account.character.create` with an empty payload is submitted

#### Scenario: Cancelling leaves the current character
- **WHEN** the player cancels the confirmation or presses Escape on it
- **THEN** nothing is submitted, the session keeps its character, and the switcher returns to its
  list

#### Scenario: A full account cannot open the confirmation
- **WHEN** the committed roster reports that no further character may be created
- **THEN** the create control renders disabled with a stable capacity reason and activating it
  opens no confirmation

#### Scenario: Capacity comes from the committed field, not the row count
- **WHEN** the committed roster reports that another character may not be created
- **THEN** the create control renders disabled with a stable capacity reason, and the client takes that fact from the committed field rather than recomputing it from the row count

#### Scenario: Cancelling or escaping the confirmation submits nothing
- **WHEN** the player cancels, or leaves the confirmation with Escape
- **THEN** nothing is submitted and the current character is left untouched

#### Scenario: Switching is not confirmation-gated
- **WHEN** the player activates a switch row
- **THEN** no confirmation gates it: switching is reversible and is already refused server-side during combat

### Requirement: A session admits at most one scheduled puppet transition at a time
A session that already has a puppet transition scheduled from an accepted
`account.character.switch` or `account.character.create` SHALL refuse any further
`account.character.switch` or `account.character.create` submitted before that transition
finishes, with the stable code `transition_pending` and a safe Traditional Chinese message,
scheduling no further transition, because either action changes the same session's puppet.

#### Scenario: A second switch while one is pending is refused
- **WHEN** `account.character.switch` is submitted for a session that already has a puppet
  transition scheduled from an earlier accepted `account.character.switch`
- **THEN** the second request is rejected with the `transition_pending` code, no further
  transition is scheduled, and the first transition's own outcome is unaffected

#### Scenario: A create while a switch is pending is refused
- **WHEN** `account.character.create` is submitted for a session that already has a puppet
  transition scheduled from an earlier accepted `account.character.switch`
- **THEN** the create request is rejected with the `transition_pending` code and no character is
  created

#### Scenario: A switch while a create is pending is refused
- **WHEN** `account.character.switch` is submitted for a session that already has a puppet
  transition scheduled from an earlier accepted `account.character.create`
- **THEN** the switch request is rejected with the `transition_pending` code and no puppet change
  is scheduled

#### Scenario: The next request is admitted once the pending transition completes
- **WHEN** a session's pending transition finishes by success, or by a recovery/cancellation step
  that retained or restored a puppet, and the session submits a further
  `account.character.switch` or `account.character.create`
- **THEN** the request is admitted and evaluated normally, not refused as pending

#### Scenario: The pending refusal never shadows a puppet-less session
- **WHEN** the recovery rung that leaves the session holding no character has finished and a
  further character-changing action is submitted from that session
- **THEN** the request is answered by the ordinary no-character entry gate rather than the
  `transition_pending` refusal

#### Scenario: A rapid double submission never reports a false success
- **WHEN** two `account.character.switch` requests naming different owned characters are submitted
  from the same session before the first's transition has run
- **THEN** exactly one request is accepted and schedules a transition, and the other is rejected
  with the `transition_pending` code rather than being accepted and later silently dropped

#### Scenario: The pending refusal takes precedence over every other rejection reason
- **WHEN** a session with a puppet transition already pending submits a further
  `account.character.switch` that would also independently fail — for a character id not owned by
  the account, for a session whose current puppet is in an active combat session, or for the
  session's already-current puppet
- **THEN** the request is rejected with the `transition_pending` code, never with
  `invalid_character`, `in_combat`, or `already_current`

#### Scenario: Either action blocks the other while pending
- **WHEN** a switch or create is submitted while the other action's transition is pending
- **THEN** the refusal holds regardless of which of the two actions scheduled the pending transition and which is being refused

#### Scenario: The refusal costs only a session-scoped flag check
- **WHEN** the admission stage evaluates the pending marker
- **THEN** the refusal is decided at admission, before any account, character, or combat-session lookup, so it costs nothing beyond a session-scoped flag check

#### Scenario: A finished transition stops the pending refusal
- **WHEN** the pending transition finishes — whether by success or by any step of the recovery ladder
- **THEN** the session no longer refuses a further character-changing action as `transition_pending`

#### Scenario: A puppet-holding session is admitted normally
- **WHEN** the session holds a puppet — because the transition succeeded or a recovery/cancellation step retained or restored one — and submits a further `account.character.switch` or `account.character.create`
- **THEN** the request is admitted and evaluated normally

#### Scenario: The no-character recovery rung clears the marker
- **WHEN** the recovery rung that leaves the session holding no character completes and a request arrives from that puppet-less session
- **THEN** the pending marker is cleared and the request is answered by the ordinary no-character entry gate, never by the pending refusal
