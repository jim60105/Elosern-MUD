# webclient-character-roster Specification

## Purpose
The committed account-level roster read model — which characters an account owns, which one is live, each row's portrait resolution, the capacity facts, and the switch-lock state.

## Requirements

### Requirement: The account roster is a committed presentation panel available in every mode
The system SHALL register a `roster` presentation panel whose subject is the account owning the
rendered puppet, rather than the puppet itself, and SHALL render it in every full snapshot. The
panel SHALL be available in creation, exploration, combat, and dialogue mode alike: it SHALL NOT
gate its availability on the actor's `creation_pending` marker, because a player who abandoned a
creation wizard must still be able to see the characters they can return to. When the rendering
actor has no resolvable owning account, or the account's character list cannot be read without
mutation, the panel SHALL report the common non-internal unavailable form rather than an empty
roster, so an unreadable account is never presented as an account with no characters.

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

### Requirement: Each roster row reports only canonical, owned character facts
Each row of the `roster` panel SHALL correspond to exactly one character in the rendered actor's
owning account's character list, and SHALL carry that character's stable numeric identity, its
current object key as its name, whether it is the session's live puppet, whether its creation is
still pending, and its portrait resolution. Rows SHALL be ordered by ascending numeric identity so
the presented order never depends on handler iteration order, and the live puppet SHALL NOT be
reordered to the front — it is identified by its own field. The row count SHALL be bounded by a
presenter-owned constant independent of the configured capacity, so a misconfigured capacity can
never produce a payload exceeding the envelope limit. The panel SHALL carry no per-character
resources, location, condition, or last-played field: a row states who the character is, not how
they are doing. The panel SHALL NOT synthesize a display label for a character whose key is
ambiguous; the pending marker is the disambiguating fact the panel carries, and how it is
presented belongs to the client.

#### Scenario: Rows name the account's characters in identity order
- **WHEN** an account owns three characters and a snapshot is built for one of them
- **THEN** the `roster` panel carries exactly three rows in ascending identity order, exactly one
  of which is marked as the current puppet

#### Scenario: A pending sibling appears as a pending row
- **WHEN** an account owns one activated character and one character still pending creation
- **THEN** both appear as rows, and the pending one carries the pending marker while the activated
  one does not

#### Scenario: The roster states nothing about a character's condition
- **WHEN** a roster row is inspected for a character at low health, in another room, or under a
  status condition
- **THEN** the row carries no resource, location, or condition field

#### Scenario: A foreign character never appears
- **WHEN** a character not owned by the rendering actor's account exists in the world
- **THEN** it appears in no roster row

### Requirement: Roster portraits resolve through the named-portrait subject mechanism
Each roster row's portrait SHALL be resolved through the same named-portrait resolution the art
panel's portrait catalog uses: an explicit named `portrait_policy` on the character, the adult
eligibility gate, and the resolved asset or its placeholder. A row SHALL carry the same portrait
field vocabulary the art panel's catalog entries carry — the subject key, the asset status, the
same-origin media URL, the aspect ratio, the alt text, and the placeholder descriptor — so the
client renders roster portraits through its existing portrait treatment rather than a second
vocabulary. Resolution SHALL NOT require the character to be present in the rendering actor's
current room. A character carrying no named portrait policy — which every character still pending
creation does, because the policy is established only at activation — SHALL resolve to the
no-portrait placeholder with no URL and no subject key.

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

### Requirement: The roster carries the account's capacity and switch-lock facts
The `roster` panel SHALL carry, computed once per snapshot from canonical state: the configured
maximum number of characters the account may hold, whether another character may be created (the
account's character count is below that maximum), whether switching characters is currently
blocked, and, when it is blocked, one stable Traditional Chinese reason. Switching SHALL be
reported as blocked exactly when the rendering actor is in an active combat session — the same
predicate that blocks the actor's movement and resolves the `combat` snapshot mode. The lock SHALL
be one snapshot-wide fact with one shared reason, never a per-row status field. These fields are
advisory presentation state: they SHALL NOT be the authorization for any state change, and any
action acting on them re-evaluates the same predicates server-side at admission.

#### Scenario: An account below the cap may create
- **WHEN** an account holding fewer characters than the configured maximum receives a snapshot
- **THEN** the `roster` panel reports that maximum and that another character may be created

#### Scenario: An account at the cap may not create
- **WHEN** an account holding exactly the configured maximum receives a snapshot
- **THEN** the `roster` panel reports that another character may not be created

#### Scenario: Combat blocks switching for the whole roster
- **WHEN** a snapshot is built for an actor in an active combat session
- **THEN** the `roster` panel reports switching as blocked with one stable reason, and no row
  carries a per-row lock field

#### Scenario: The lock clears when the session ends
- **WHEN** the actor's combat session ends and the next snapshot is built
- **THEN** the `roster` panel reports switching as unblocked and carries no reason

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
booleans. Any other, missing, or wrongly typed field SHALL be refused through the dispatcher's
existing malformed-payload rejection before the adapter runs. The adapter SHALL obtain the account
from the authenticated session's own puppet and SHALL resolve `character_id` only against that
account's character list — never through a world-wide object search and never through a
permission-based fallback — so no character outside the acting account is reachable through this
surface. The action SHALL NOT route an action identifier or payload through the text command
parser.

#### Scenario: A foreign character id is refused
- **WHEN** `account.character.switch` is submitted with the identity of a character owned by a
  different account
- **THEN** the action is rejected as an invalid character, no puppet change is scheduled, and no
  data about that character is returned

#### Scenario: A malformed payload never reaches the adapter
- **WHEN** `account.character.switch` is submitted with a missing, non-integer, boolean, negative,
  or extra field
- **THEN** the dispatcher returns the malformed-payload rejection and no adapter runs

### Requirement: A character-changing action reports its decision before its transition
An account-scoped action whose effect is a puppet change SHALL make every authorization decision
synchronously at admission, and its action result SHALL report the outcome of that decision. It
SHALL NOT perform the puppet transition inside the adapter: the transition SHALL be scheduled to
run after the completion result has been sent and both the server in-flight marker and the browser's
mutation lock have been released, because the transition retires the very sequence the result would
be published into. The resulting message order on the wire SHALL be the action result first, then
the client's detach signal, then a fresh-epoch full snapshot for the new puppet. A successful action
SHALL NOT be marked as an uncertain outcome by the client.

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

### Requirement: A scheduled puppet transition verifies its outcome and recovers explicitly
A scheduled puppet transition SHALL re-validate its decision against committed state before acting,
and SHALL NOT unpuppet the session's current character as a separate preparatory step: the
puppeting API's own guards SHALL own that unpuppet, so a guard refusal leaves the current character
attached. After attempting the puppet change the transition SHALL verify that the session actually
holds the requested character, because the puppeting API can refuse silently — returning without
raising — including after it has already released the previous character.

On any failure — failed re-validation, a raised error, or a failed verification — the transition
SHALL take the highest applicable recovery step and SHALL NOT report success or fall silent:

1. When the session still holds its previous character, it SHALL log the failure, tell the player
   in Traditional Chinese that the switch did not happen and which character they are still
   playing, and publish a fresh snapshot for that character.
2. When the session holds no character, it SHALL attempt to re-attach the previous character and,
   on success, proceed as in step 1 while logging at error severity.
3. When re-attachment also fails, it SHALL leave the session with no character, log at error
   severity with the account, session, previous-character, and target identities, and tell the
   player explicitly that they are no longer playing any character and how to return. It SHALL NOT
   publish a snapshot in this state, because there is no character to render.

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
`already_current` when `character_id` is already the session's live puppet. `already_current` SHALL
be a rejection rather than a success, because a success would tell the client a transition is
coming that will never arrive. Each rejection SHALL carry a stable code and a safe Traditional
Chinese message and SHALL change no state. The combat condition SHALL be evaluated from the same
active-combat-session predicate that blocks the character's movement; the roster panel's advisory
lock field SHALL never be the authorization.

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

### Requirement: A puppet change carries no session-scoped state across characters
A transition performed by an account-scoped action SHALL leave the retiring character's
session-scoped presentation state behind: the previous character's action-options state and
dismissal barriers, its transient creation concept proposal, and its completed-result cache and
in-flight marker SHALL NOT be visible to or reusable by the new puppet, and any generation still in
flight for the previous character SHALL publish nothing into the new sequence. Per-character
persistent state — party and companion bindings, dialogue sessions, quest progress — SHALL remain
on the character it belongs to and SHALL be unchanged by the switch.

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

### Requirement: Creating a character is an allowlisted account-scoped action
The production action registry SHALL register the account-scoped action
`account.character.create`, accepting exactly an empty payload; any field at all SHALL be refused
through the dispatcher's existing malformed-payload rejection before the adapter runs. The adapter
SHALL obtain the account from the authenticated session's own puppet, SHALL follow the same
decide-synchronously / schedule-the-transition contract as switching, and SHALL declare no affected
panels and emit no completion presentation with its result. It SHALL reject with the stable code
`character_slots_full` when the account already holds the configured maximum number of characters,
and with `in_combat` when the session's current puppet is in an active combat session — because
creating a character leaves the current one — each with a safe Traditional Chinese message and no
state change. The combat condition SHALL be re-derived from the active-combat-session predicate,
never read from the roster panel's advisory field. The action SHALL NOT route an action identifier
or payload through the text command parser.

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

### Requirement: The new character shell is created before the current character is left
The scheduled creation transition SHALL create the new character shell **before** sending the
client's detach signal or changing the session's puppet, because the account's own
character-creation API performs the authoritative capacity check and reports a full account by
returning an error rather than raising. When shell creation reports an error or fails, the
transition SHALL stop with nothing about the session changed — no detach signal, no retired
sequence, no puppet change — SHALL log the failure, and SHALL deliver one Traditional Chinese line
telling the player the character was not created. Only once a shell exists SHALL the transition
attach it through the same verified attach and recovery ladder the switch action uses.

A shell that was created but could not be attached SHALL be left in place, not deleted: it is a
legitimate pending character the account owns, it appears in the roster with its pending marker,
and it can be entered later through the switch action. The creation path SHALL perform no
destructive write on its failure branch.

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

### Requirement: A newly created character enters the existing wizard and never resends the world introduction
The created shell SHALL receive the project's pending-creation marker through the account's own
post-creation hook, exactly as an account's first shell does, so the unchanged mode derivation
resolves the creation mode and the existing creation surface is presented with no client change.
The action SHALL NOT assign identity attributes, traits, or the pending marker directly, and SHALL
NOT name the shell: the creation wizard's activation remains the sole writer of a character's
display name. The reusable creation start presentation SHALL be delivered for the new shell. The
world introduction SHALL NOT be delivered for any character after the account's first, and this
SHALL hold structurally — the introduction is reachable only from the login hook, which a
mid-session puppet change does not run — rather than by an explicit suppression this action has to
remember.

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

### Requirement: The top band carries a character switcher rendered from the committed roster
The client SHALL render a character switcher in the stage's top band, beside the meta pill and
above the HUD island anchors, whenever the committed `roster` panel is available. Its collapsed
form SHALL present the current character's portrait thumbnail and name, both read from the roster
row marked as current — never from the status or character panel — so the collapsed form and the
expanded list can never name different characters. The collapsed form SHALL be width-bounded and
truncate a long name rather than growing with it. When the `roster` panel is unavailable the
switcher SHALL render nothing at all: neither an empty pill nor a placeholder character. The
switcher SHALL render in every committed mode, including creation, so a player who abandoned a
creation wizard can return to a finished character.

#### Scenario: The collapsed pill names the live character
- **WHEN** a snapshot commits a roster whose current row names 艾莉亞
- **THEN** the collapsed switcher renders 艾莉亞's name and portrait thumbnail

#### Scenario: The switcher is present during character creation
- **WHEN** the committed mode is `creation` and the roster panel is available
- **THEN** the switcher renders, and its collapsed form names the pending character being created

#### Scenario: An unavailable roster renders no switcher
- **WHEN** the committed `roster` panel reports the unavailable form
- **THEN** no switcher element is rendered anywhere in the top band

### Requirement: The expanded switcher lists every roster row with one shared lock note
Activating the switcher SHALL open a list rendering one row per committed roster character, in
payload order, each carrying that row's portrait thumbnail and name. A row whose committed pending
marker is set SHALL carry a stable in-creation marker; the client SHALL NOT synthesize a
disambiguating display name for it. The row marked as current SHALL be presented as selected and
SHALL NOT be activatable. When the committed roster reports switching as blocked, every
non-current row SHALL render disabled under exactly one shared inline note carrying the panel's
own committed reason string — never a per-row badge and never client-composed reason text. The
list SHALL be bounded in height with internal scrolling rather than growing the top band, SHALL
overlay the HUD islands transiently rather than displacing them, and SHALL close on Escape, on
outside pointer activation, and when a new presentation epoch is committed.

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

### Requirement: Switching dispatches once and commits only on the server's snapshot
Activating an enabled, non-current row SHALL submit exactly one `account.character.switch`
carrying that row's committed identity, through the client's single dispatch entry and its
existing connected / locked / one-in-flight gates. Keyboard and pointer activation SHALL submit
the same action identifier and payload through the same entry. The surface SHALL NOT optimistically
mark the chosen row as current, SHALL NOT close on dispatch alone, and SHALL NOT add debouncing of
its own: the presented current character changes only when a snapshot naming the new puppet lands.
While the client is disconnected or its mutations are locked — including throughout the transition
between the two characters — every row and the create control SHALL render disabled and dispatch
nothing.

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

### Requirement: Creating a character is a confirmation-gated trailing control
The expanded list SHALL end with a create-character control. When the committed roster reports
that another character may not be created, that control SHALL render disabled with a stable
capacity reason, and the client SHALL take that fact from the committed field rather than
recomputing it from the row count. When creation is permitted, activating the control SHALL NOT
dispatch: it SHALL open an explicit confirmation stating that the current character will be left,
with a cancel control and a confirm control, and only the confirm control SHALL submit exactly one
`account.character.create` with an empty payload. Cancelling, or leaving the confirmation with
Escape, SHALL submit nothing and leave the current character untouched. Switching SHALL NOT be
confirmation-gated: it is reversible and is already refused server-side during combat.

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
