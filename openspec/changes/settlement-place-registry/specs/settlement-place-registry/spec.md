## Purpose

Describe one service location — its room, its host and its goods — as a
single authored record, so adding a location to any settlement is a data
edit rather than a code edit across four files.

## ADDED Requirements

### Requirement: A place is the single authored record of one service location
The system SHALL support place records. One place SHALL carry everything
that distinguishes one service location: its stable key, the settlement it
belongs to, its kind, the Traditional Chinese name and description of its
interior room, the exterior coordinate the interior attaches to, the
doorway naming, its host's identity, the host's profession and that
profession's component identity kwargs, and the assortments the place
sells.

No part of a place SHALL be declared anywhere else. In particular a place's
host SHALL NOT also require a separate roster row, and a place's interior
SHALL NOT also require a code-side constant.

A place SHALL declare assortments if and only if it declares a shop
identity. A location that sells nothing and a location that sells something
but names no goods are both authoring errors and SHALL fail load.

#### Scenario: One record yields a working location
- **WHEN** a place record is added and synchronization runs
- **THEN** its interior room exists and is tagged, its doorways connect it
  to its exterior in both directions, its host stands in it with the
  declared profession's components attached, and its goods are purchasable —
  with no other file edited

#### Scenario: Goods without a shop identity fail load
- **WHEN** a place declares assortments but no shop identity, or a shop
  identity but no assortments
- **THEN** catalog validation raises naming the place

### Requirement: A settlement declares its archetype and coordinate space
The system SHALL support settlement records carrying a stable key matching
the geographic anchor registry, an archetype drawn from a closed vocabulary
of the six settlement archetypes the world defines, and the map coordinate
space its places sit in.

A place SHALL name a settlement that exists; its exterior coordinate SHALL
be resolved within that settlement's coordinate space rather than being
declared with one.

The archetype vocabulary SHALL be distinct from the geographic anchor kind
vocabulary. Anchor kinds classify geography and include non-settlements;
archetypes classify how a settlement is built.

#### Scenario: A place in an unknown settlement fails load
- **WHEN** a place names a settlement key absent from the settlement
  registry
- **THEN** catalog validation raises naming the place and the missing
  settlement

#### Scenario: Two settlements' places resolve in their own coordinate spaces
- **WHEN** two settlements each declare a place at the same exterior
  coordinate
- **THEN** each interior attaches to its own settlement's exterior room, and
  neither attaches to the other's

### Requirement: Shop identities and the service-host roster are derived from places
Shop identities SHALL be derived from the places that declare one, and the
service-host roster SHALL be derived from every place. Neither SHALL be
hand-authored.

A place SHALL carry the component identity kwargs its profession's blueprint
requires, whatever that profession is — a trading place supplies its shop
identity, a guild hall supplies its branch and dialogue identities. A flat
shop-only field SHALL NOT be used, because it cannot describe a
non-trading service location.

Blueprint coverage SHALL be enforced as it is for a hand-authored roster
row: every component's identity fields except the row-level service anchor
must be supplied, and a kwarg no component consumes SHALL be rejected.

The authored-name uniqueness rule SHALL continue to hold across shops,
guild branches and guild rank examiners, evaluated over the derived rows.

#### Scenario: A trading place and a non-trading place both derive hosts
- **WHEN** the registry holds a place whose profession is a merchant and a
  place whose profession is guild staff
- **THEN** both derive complete roster rows, each carrying exactly the
  identity kwargs its own blueprint consumes

#### Scenario: A missing blueprint kwarg fails load
- **WHEN** a place's profession declares a component whose identity field
  the place does not supply
- **THEN** catalog validation raises naming the place, the profession and
  the missing field, without touching the database

#### Scenario: A duplicate authored name is rejected
- **WHEN** two derived rows, or a derived row and a guild registry row,
  carry the same authored name
- **THEN** load fails naming both holders

### Requirement: Interiors are created by iterating the place registry
Interior rooms SHALL be created, tagged, described and connected to their
exteriors by iterating the place registry. No location SHALL be named by a
code-side constant.

Synchronization SHALL remain idempotent: a repeated run SHALL reuse the
tagged room rather than creating a second one, SHALL re-apply the authored
description in place, and SHALL not duplicate doorways.

When a place's exterior room cannot be resolved, synchronization SHALL warn
naming the place and skip it, and SHALL continue processing the remaining
places rather than aborting.

#### Scenario: Adding a place adds an interior with no code change
- **WHEN** a place record is added to the registry and synchronization runs
- **THEN** its interior and both doorways appear, and no module constant was
  added for it

#### Scenario: A repeated run changes nothing
- **WHEN** synchronization runs twice
- **THEN** no room, doorway or host is duplicated, and live merchant stock
  is unchanged

#### Scenario: One unresolvable exterior does not stop the rest
- **WHEN** one place's exterior coordinate resolves to no room
- **THEN** that place is warned and skipped, and every other place still
  synchronizes

### Requirement: A place authors its host's race, subrace and sex
A place SHALL declare its host's race, and may declare a subrace and SHALL
declare a sex. Synchronization SHALL apply them instead of assuming a
default race, so a settlement whose inhabitants are not human produces hosts
of the right people.

These SHALL be creation-time authored identity: written once when the host
is created, alongside the authored title, and never rewritten on a later
synchronization. Changing an authored value therefore takes effect through
roster convergence — the host is deleted and recreated — consistent with the
existing never-rename and never-retitle contract.

Validation SHALL reject an unknown race, an unknown sex, and a subrace whose
own race disagrees with the place's declared race.

#### Scenario: A non-human settlement produces non-human hosts
- **WHEN** a place declares a non-human race and a subrace bound to that
  race, and synchronization creates the host
- **THEN** the host carries that race and subrace with its race baselines
  applied, not the default race

#### Scenario: A mismatched subrace fails load
- **WHEN** a place declares a subrace whose race differs from the place's
  declared race
- **THEN** catalog validation raises naming the place, the race and the
  subrace

#### Scenario: Re-synchronization does not rewrite authored identity
- **WHEN** a place's authored race, subrace or sex is edited and
  synchronization runs against the existing host
- **THEN** the live host is left unchanged, exactly as an edited name or
  title is
