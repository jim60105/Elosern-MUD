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
and generic-monster startup synchronization — SHALL route through the gallery generation request
rather than the subject-keyed asset `ensure`, and SHALL request exactly one image built from the
subject's standard deterministic description with no free text, no binding, and the shared default
face rectangle. For a kind that declares field-selection support, that description is the authored
appearance contribution and nothing else, expressed as the `appearance` field alone; for a kind that
declares no field selection, it is that kind's registry-driven description with no selection supplied
at all. The requirement is on the resulting description, not on the request's argument shape.

The resulting card SHALL be unbound, so it is displayed only as the subject's default — which, being
the subject's first card, it becomes automatically. NO gallery-bearing subject SHALL produce a classic
fixed-identity asset record on any of these paths. Each path SHALL keep its existing guarantees
unchanged: the canonical-age check at schedule time and again immediately before the queue write for
every kind that declares the age precondition, the `transaction.on_commit` registration on the paths
that have one, and the total failure isolation in which an art failure never rolls back creation,
import, spawn, movement, or startup.

#### Scenario: A committed creation produces one unbound default card
- **WHEN** player creation commits and its post-commit job is drained
- **THEN** the character's gallery holds exactly one unbound card carrying the shared default rectangle, that card is the default, and no classic asset record exists for the subject

#### Scenario: A registered monster tier produces one unbound default card
- **WHEN** startup synchronization runs for a registered monster tier with an empty gallery and its job is drained
- **THEN** that tier's gallery holds exactly one unbound card carrying the shared default rectangle, that card is the default, and startup wrote no classic asset record for the tier

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

### Requirement: Automatic generation is idempotent against the subject's gallery
An automatic path SHALL request a generation only when the subject's gallery holds no card AND no
gallery job for that subject is in flight. A subject that already holds any card — generated, seed-
synced, or player-kept — SHALL be left alone. This SHALL hold across restarts, so repeated startup
recovery and repeated startup synchronization never stack duplicate cards, and across quests, so a
`stable_key` shared by several scenes yields exactly one auto-generated card. The guard SHALL be the
same one for every gallery-bearing kind, so a monster tier is protected by exactly the rule a character
subject is — which is also what keeps a capped kind from replacing its one card on every restart.

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

### Requirement: Player creation may skip the automatic portrait
`world/rules/character_creation.py::finalize_player_portrait` SHALL accept an explicit skip flag,
defaulting to generating. It SHALL establish the explicit named `portrait_policy` on every path,
including the skipped one, so the character stays eligible for a later request. A skipped creation
SHALL enqueue nothing and SHALL leave the character with an empty gallery, which resolves through the
standard chain's terminal fallback seam (inert until the gallery-fallback capability fills it — today
the honest outcome is the truthful placeholder, owned by ``gallery-builtin-fallbacks``). The flag SHALL
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

