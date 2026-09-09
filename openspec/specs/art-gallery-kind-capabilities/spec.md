# art-gallery-kind-capabilities Specification

## Purpose
TBD - created by archiving change gallery-kind-capabilities. Update Purpose after archive.
## Requirements
### Requirement: One closed declaration states what every subject kind's gallery may do
`world/art/gallery_kinds.py` SHALL declare exactly one immutable capability record per art subject
kind, and that declaration SHALL be the single origin of every per-kind gallery rule. Each record
SHALL carry at least: whether the kind has a gallery at all, the directory segment its stored
identities use, the maximum number of cards one record may hold, and whether the kind supports
equipment bindings. A kind without a gallery SHALL be declared explicitly as such rather than being
represented by an absent entry, so "this kind has no gallery" is an assertion in the table and not an
accident of a missing key.

The card maximum SHALL be nullable, and a null maximum SHALL mean genuinely unbounded — the character
portrait kind is uncapped today and SHALL stay uncapped, so "no maximum" MUST be representable rather
than approximated by a large sentinel. The declared maximum SHALL be either null or exactly `1`; the
contract test SHALL reject any other value. The gallery holds no kind needing an intermediate cap, and
admitting arbitrary values would require an eviction algorithm no real declaration exercises. A future
kind that genuinely needs one widens this rule in the change that introduces it.

The declaration SHALL be data only: it SHALL perform no I/O and read no settings, and it SHALL expose
no mutable state to consumers — records and the table view are frozen, and the writable origin is a
module-private mapping that no consumer API hands out and only the test patch seam rewrites — so the
same kind resolves the same capabilities in every process.

#### Scenario: Every declared capability is readable from one place
- **WHEN** the capability record for the character kind and for the monster kind are read
- **THEN** each reports its gallery-bearing flag, store directory segment, maximum card count, and binding support without consulting any other module

#### Scenario: A kind with no gallery is declared, not omitted
- **WHEN** the capability record for the scene kind is read
- **THEN** an entry exists that declares the kind as having no gallery, and reading it raises no error

#### Scenario: The character kind declares no maximum and stays uncapped
- **WHEN** the character capability record is read and cards are appended to a character record well past any single-card limit
- **THEN** the declared maximum is null and every card is retained in append order with no replacement

#### Scenario: A maximum outside the admitted values fails the contract
- **WHEN** the contract test runs against a declaration naming a card maximum that is neither null nor `1`
- **THEN** the test fails naming the offending kind and value

#### Scenario: The declaration is immutable
- **WHEN** a caller attempts to mutate a capability record or the table that holds them
- **THEN** the attempt fails and no other caller observes a changed capability

### Requirement: The declaration covers every subject kind exhaustively
A contract test SHALL assert that the declaration holds exactly one entry for every member of
`ArtSubjectKind` — no member undeclared and no entry naming a kind that does not exist. Adding a new
subject kind without declaring its gallery capability SHALL therefore fail at test time rather than
degrade silently at runtime, which is what a missing key in the previous directory lookup did.

#### Scenario: A newly added kind without a declaration fails the contract
- **WHEN** the contract test runs against a subject-kind vocabulary carrying a member with no capability entry
- **THEN** the test fails naming the undeclared kind

#### Scenario: A stale entry for a removed kind fails the contract
- **WHEN** the contract test runs against a declaration holding an entry whose kind is not a member of the vocabulary
- **THEN** the test fails naming the stale entry

### Requirement: The declaration module imports nothing and is keyed by the kind's declared value
`world/art/gallery_kinds.py` SHALL import no module — neither from `world.art` nor from anywhere else
in the project — and SHALL key its table by the subject kind's declared string value, exactly as
`world/art/fallback_keys.py` does and for the same reason. `world/art/subjects.py` imports the gallery
prompt layer at module level, so a capability table that imported `subjects` would close an import
cycle as soon as the prompt layer needed to consult it. An import-boundary test SHALL enforce the
zero-import rule.

#### Scenario: The module has no imports
- **WHEN** the import-boundary test parses `world/art/gallery_kinds.py`
- **THEN** it finds no import statement of any kind

#### Scenario: Consulting the table from the prompt layer closes no cycle
- **WHEN** the gallery prompt layer imports the capability table
- **THEN** the package imports cleanly and no circular import is raised

### Requirement: Gallery enforcement reads the declaration instead of comparing kinds
The gallery modules SHALL decide every per-kind gallery rule by reading the declaration: whether a
record or card may exist for the subject at all, which directory segment its stored identity uses,
whether an append exceeds the kind's card maximum, whether a card may carry a binding, and whether the
resolution chain runs its binding steps. Enforcement SHALL follow the declared value, so changing a
kind's declaration changes the enforced rule with no edit to the enforcing module.

#### Scenario: A changed card maximum changes what an append does
- **WHEN** a kind's declared maximum is changed from null to `1` and a card is appended to a record already holding one card
- **THEN** the append replaces rather than accumulates, with no change to the enforcing module

#### Scenario: An unbounded kind never replaces
- **WHEN** cards are appended repeatedly to a record whose kind declares a null maximum
- **THEN** every card is retained in append order, no stored file is deleted, and the original default is unchanged

#### Scenario: A kind declaring no binding support rejects a bound card
- **WHEN** a card carrying a binding is appended for a kind whose declaration does not support bindings
- **THEN** a typed validation error is raised and the record is unchanged

#### Scenario: The resolution chain runs binding steps only where declared
- **WHEN** display resolution runs for a kind whose declaration does not support bindings
- **THEN** no equipment snapshot is computed and no card is selected by a binding

#### Scenario: A kind declared as having no gallery is refused at every write
- **WHEN** a record creation, a card validation, or a gallery job enqueue is attempted for a kind declared as having no gallery
- **THEN** each is refused with a typed error and nothing is written

