# art-gallery-autogen Specification

## Purpose

Define how every automatic character-portrait path — player creation, validated
import, named-NPC spawn, startup recovery, and staff retry/requeue — routes
through the gallery generation seam: exactly one unbound card built from the
subject's standard deterministic description with the shared default face
rectangle and no classic fixed-identity record, guarded for idempotency
against the subject's gallery, with the existing age-check, post-commit, and
failure-isolation guarantees intact. Player creation carries an explicit skip
flag that establishes the named policy without requesting anything.

## Requirements

### Requirement: Automatic character portraits produce exactly one unbound default card
Every automatic portrait path — player creation, validated import, named-NPC spawn, startup recovery,
and generic-monster startup synchronization — SHALL route through the gallery generation request,
not the subject-keyed asset `ensure`, requesting exactly one image from the subject's standard
deterministic description with no free text, no binding, and `face_rect=None`.
The resulting card SHALL be unbound, displayed only as the subject's default.

#### Scenario: A committed creation produces one unbound default card
- **WHEN** player creation commits and its post-commit job is drained
- **THEN** the character's gallery holds exactly one unbound card carrying the fitted default square for its image, that card is the default, and no classic asset record exists for the subject

#### Scenario: A registered monster tier produces one unbound default card
- **WHEN** startup synchronization runs for a registered monster tier with an empty gallery and its job is drained
- **THEN** that tier's gallery holds exactly one unbound card carrying the fitted default square for its image, that card is the default, and startup wrote no classic asset record for the tier

#### Scenario: The age gate still rejects before any record or prompt
- **WHEN** an automatic path runs for a character whose `age` or `apparent_age` is missing or non-integer
- **THEN** nothing is queued, no prompt is rendered, no card is appended, and the named diagnostic is logged

#### Scenario: A kind without the age precondition reads no age attribute
- **WHEN** an automatic path runs for a registered monster tier
- **THEN** no canonical-age check runs, no age attribute is read, and the request proceeds

#### Scenario: A rolled-back transaction produces nothing
- **WHEN** a creation, import, or materialization transaction rolls back
- **THEN** the on-commit callback never fires, no gallery job exists, and no card is appended

#### Scenario: An art failure never rolls back gameplay
- **WHEN** the gallery request or its job fails on an automatic path
- **THEN** the creation, import, spawn, move, or startup is still reported as successful and a bounded diagnostic is logged

#### Scenario: The description is authored appearance only, for field-selecting kinds
- **WHEN** the automatic request targets a kind that declares field-selection support
- **THEN** the description is the authored appearance contribution and nothing else, expressed as the
  `appearance` field alone

#### Scenario: The description is registry-driven, for non-selecting kinds
- **WHEN** the automatic request targets a kind that declares no field selection
- **THEN** the description is that kind's registry-driven description with no selection supplied at all

#### Scenario: The requirement binds the description, not the argument shape
- **WHEN** compliance with this requirement is judged
- **THEN** the requirement is on the resulting description, not on the request's argument shape

#### Scenario: The first card is the default automatically
- **WHEN** the unbound card is the subject's first card
- **THEN** it becomes the subject's default automatically

#### Scenario: Each path keeps its existing guarantees unchanged
- **WHEN** an automatic path is wired to the gallery request
- **THEN** it keeps the canonical-age check at schedule time and again immediately before the queue
  write for every kind that declares the age precondition, the `transaction.on_commit` registration on
  the paths that have one, and the total failure isolation in which an art failure never rolls back
  creation, import, spawn, movement, or startup

#### Scenario: The unbound card takes the fitted default square
- **WHEN** the automatic request settles
- **THEN** the resulting card takes the fitted default square computed from the settled image's
  recorded pixel size

#### Scenario: No classic fixed-identity asset record on any path
- **WHEN** any gallery-bearing subject goes through these automatic paths
- **THEN** no classic fixed-identity asset record is produced

### Requirement: Automatic generation is idempotent against the subject's gallery
An automatic path SHALL request a generation only when the subject's gallery holds no card AND no
gallery job for that subject is in flight AND — for an entity whose official content reference is
eligible and already satisfied by a valid catalog entry in the startup official snapshot (see the
`official-art-resolution` capability) — no official default resolves for it. A subject that already
holds any card SHALL be left alone. The guard SHALL be the same one for every gallery-bearing kind.

#### Scenario: Repeated recovery appends nothing
- **WHEN** startup recovery runs on consecutive restarts for a subject that already holds one card
- **THEN** no additional generation is requested and the gallery still holds one card

#### Scenario: Repeated startup synchronization never replaces a monster card
- **WHEN** startup synchronization runs on consecutive restarts for a monster tier that already holds its one card
- **THEN** no generation is requested, the existing card is not replaced, and its stored file is untouched

#### Scenario: A seed-synced subject is not auto-generated
- **WHEN** an automatic path runs for a subject whose only card came from seed synchronization
- **THEN** no generation is requested

#### Scenario: An in-flight job suppresses a second request
- **WHEN** an automatic path runs for a subject whose gallery job is already pending or in progress
- **THEN** no second job is enqueued

#### Scenario: Satisfying official artwork suppresses the initial automatic generation
- **WHEN** a preset-born character activates with an empty gallery while its preset content reference resolves a valid official default
- **THEN** no gallery generation is enqueued, the character still carries its named portrait policy, and it presents the official default

#### Scenario: An ineligible or unsatisfied reference does not suppress
- **WHEN** an automatic path runs for an entity with no content reference, or one the snapshot does not hold
- **THEN** the existing automatic request proceeds exactly as today

#### Scenario: Manual generation remains available after suppression
- **WHEN** an entity whose automatic generation was official-suppressed is later requested through the manual gallery generation seam
- **THEN** the request is served through the existing seam and settles a runtime card that then outranks the official default

#### Scenario: Any existing card kind counts as held
- **WHEN** the idempotency guard finds the subject's only card
- **THEN** a generated, seed-synced, or player-kept card all count, and the subject is left alone

#### Scenario: The guard holds across restarts
- **WHEN** startup recovery and startup synchronization repeat across restarts
- **THEN** they never stack duplicate cards

#### Scenario: The guard holds across quests
- **WHEN** several scenes share one `stable_key`
- **THEN** they yield exactly one auto-generated card

#### Scenario: One rule protects every gallery-bearing kind
- **WHEN** the guard is applied per kind
- **THEN** a monster tier is protected by exactly the rule a character subject is — which is also what
  keeps a capped kind from replacing its one card on every restart

#### Scenario: A suppressed request leaves nothing and is not revived later
- **WHEN** an automatic request is suppressed
- **THEN** it leaves no record and enqueues nothing; the entity presents the official default through
  the presentation chain, and updating the official directory later does not retroactively enqueue the
  suppressed subject

### Requirement: Player creation may skip the automatic portrait
`world/rules/character_creation.py::finalize_player_portrait` SHALL accept an explicit skip flag,
defaulting to generating. It SHALL establish the explicit named `portrait_policy` on every path,
including the skipped one. A skipped creation
SHALL enqueue nothing and SHALL leave the character with an empty gallery. The flag SHALL
be read inside the activation transaction like
the rest of the finalization, so a rollback leaves no portrait state either way.

#### Scenario: A skipped creation starts with an empty gallery
- **WHEN** a character is activated with the skip flag set
- **THEN** it carries the named portrait policy, its gallery is empty, no job is enqueued, and it resolves through the standard chain's terminal fallback seam rather than owning any portrait state of its own

#### Scenario: The default path still generates
- **WHEN** a character is activated without the skip flag
- **THEN** exactly one post-commit gallery generation is scheduled

#### Scenario: A rolled-back skipped activation leaves nothing
- **WHEN** an activation with the skip flag set rolls back
- **THEN** no portrait policy and no gallery state remain on the character

#### Scenario: The empty gallery resolves through the terminal fallback seam
- **WHEN** a skipped character's empty gallery is presented
- **THEN** it resolves through the standard chain's terminal fallback seam (inert until the
  gallery-fallback capability fills it — today the honest outcome is the truthful placeholder, owned
  by ``gallery-builtin-fallbacks``)
- **AND** establishing the policy on every path keeps the character eligible for a later request
