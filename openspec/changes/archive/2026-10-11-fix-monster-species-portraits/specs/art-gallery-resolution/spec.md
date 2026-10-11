# Spec Delta

## MODIFIED Requirements

### Requirement: Monster subjects resolve through the chain without the binding steps
The chain SHALL run the binding steps only for a subject kind whose capability declaration supports
bindings. A kind that does not SHALL resolve with those steps skipped: the entity-local official
selection if valid, else the species default card, then a valid species classic asset record, then
the species official-default step, then the fallback seam, then the placeholder. The skip SHALL come
from the declaration, never an inline kind comparison.

#### Scenario: A monster resolves its single card
- **WHEN** a monster subject holds its one card
- **THEN** that card is resolved with no equipment read

#### Scenario: A monster with no card falls through unchanged
- **WHEN** a monster subject holds no card and its classic asset record is `done`
- **THEN** the classic asset is resolved exactly as it is today

#### Scenario: The binding steps follow the declaration
- **WHEN** display resolution runs for a kind whose declaration does not support bindings
- **THEN** the binding steps are skipped and no equipment snapshot is computed, with no edit to the resolution module

#### Scenario: A tier-keyed monster falls through the official step
- **WHEN** a monster has no resolvable visual provenance, regardless of its combat tier
- **THEN** no tier subject or card is read; monster_anon is carried without an equipment, age or personal-state write

#### Scenario: The binding steps are steps 1 through 3
- **WHEN** the declaration-gated steps are named
- **THEN** they are steps 1 through 3 — the equipment snapshot, the binding candidates, and the
  most-specific-mask selection

#### Scenario: No snapshot and no binding selection for a non-binding kind
- **WHEN** resolution runs for a kind whose declaration does not support bindings
- **THEN** no equipment snapshot is computed for such a subject and no card of such a subject is
  selected by a binding

#### Scenario: Monster official defaults await the species catalog
- **WHEN** a monster has validated complete-species or baseline visual provenance
- **THEN** its own registered visual species official default can resolve; an absent package falls through only to monster_anon after same-species runtime resolution fails

#### Scenario: Tier records cannot outrank a species default
- **WHEN** a species has an official image while its monster's tier has an old gallery or classic image on disk
- **THEN** those tier records are never read or applied and the species image resolves

