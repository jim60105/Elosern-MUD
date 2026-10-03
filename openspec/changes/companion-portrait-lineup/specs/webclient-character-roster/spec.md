## MODIFIED Requirements

### Requirement: Each roster row reports only canonical, owned character facts
Each row of the `roster` panel SHALL correspond to exactly one character in the authenticated
session puppet's owning account's character list, and SHALL carry that character's stable numeric
identity, current object key, current marker, creation-pending marker and portrait resolution.
Normally `current` SHALL identify the live owned puppet. While possessing a bound companion, it
SHALL identify the owning player character A whose body/portrait remains in the lineup, not the
controlled NPC B; B SHALL NOT be added to the account roster. The live party owner and canonical
`possessed_by` binding SHALL agree, and A SHALL still be verified against that same account's
character list. A missing, stale, unbound or foreign owner SHALL produce the existing unavailable
form, never select a different account from the NPC's back-reference. `pending` SHALL remain each
owned character's own creation marker, unchanged by possession.

Rows SHALL be ordered by ascending numeric identity so the presented order never depends on
handler iteration order, and the current owned character SHALL NOT be reordered to the front — it
is identified by its own field. The row count SHALL be bounded by a presenter-owned constant
independent of configured capacity, preserving the current owned character within that bound.
The panel SHALL carry no per-character resources, location, condition or last-played field: a row
states who the character is, not how they are doing. The panel SHALL NOT synthesize a display label
for a character whose key is ambiguous; pending is the disambiguating fact, and its presentation
belongs to the client. Portrait resolution and the exact roster v2 wire shape SHALL remain unchanged
and read-only.

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

### Requirement: The roster carries the account's capacity and switch-lock facts
The `roster` panel SHALL carry, computed once per snapshot from canonical state: the configured
maximum number of characters the account may hold, whether another character may be created (the
account's character count is below that maximum), whether switching characters is currently
blocked, and, when it is blocked, one stable Traditional Chinese reason. Switching SHALL be
reported as blocked exactly when the rendering actor is in an active combat session — the same
predicate that blocks the actor's movement and resolves the `combat` snapshot mode. The lock SHALL
be one snapshot-wide fact with one shared reason, never a per-row status field. These fields are
advisory presentation state: they SHALL NOT be authorization for any state change, and any action
acting on them re-evaluates the same predicates server-side at admission. While possessing, the
rendering actor for this combat predicate remains B, not roster-current A: possession alone SHALL
NOT add a switch lock or a new reason. Capacity remains the authenticated account's owned-character
count; the possessed NPC does not consume a character slot.

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
