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
