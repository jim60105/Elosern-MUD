# place-driven-service-sync Specification

## Purpose
Make startup synchronization read the place registry: build every service
interior from it, and give each host the race, subrace and sex its place
authors instead of a hard-coded default.

## Requirements

### Requirement: One place record yields a complete working location
Adding a place record and running synchronization SHALL produce the whole
location with no other file edited: its interior room tagged and described,
its doorways connecting it to its exterior in both directions, its host
standing in it with the declared profession's components attached, and its
goods purchasable.

A place record that authors no host SHALL still yield its whole location —
the tagged, described interior and both doorways — with no NPC created for
it and no roster row derived from it. The room is the deliverable; the host
is an optional part of it, not its precondition.

#### Scenario: One record yields a working location
- **WHEN** a place record is added and synchronization runs
- **THEN** its interior, both doorways, its host and its purchasable goods
  all exist, and no module constant was added for it

#### Scenario: A host-less record yields a room and no NPC
- **WHEN** a place record authoring no host is added and synchronization
  runs
- **THEN** its interior exists once, tagged and described, reachable from
  and back to its exterior, and no service host stands in it

#### Scenario: A repeated run leaves a host-less room alone
- **WHEN** synchronization runs twice over a host-less place record
- **THEN** the room exists exactly once and no NPC is created on either run

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

### Requirement: A newly created service host receives its authored card
When synchronization creates a service host, it SHALL initialize the host's compact NPC card from the place's host profile, with `profile` provenance naming that profile, in the same transaction as the host's creation, before the host is published as usable. A roster row whose profile does not resolve SHALL fail synchronization before any write, naming the service. Synchronization SHALL NOT initialize, rewrite, or repair the card of a reused host: a restart, a registry reload, or an edit to the authored profile SHALL leave every existing host's effective card and persona version unchanged. Two hosts created from equal profiles SHALL carry independent cards.

#### Scenario: A created host carries its profile card
- **WHEN** synchronization creates the host for a place naming a synthetic profile
- **THEN** the host's persona equals that profile's card and its persona metadata is at version 1 with `profile` provenance naming the profile

#### Scenario: Restart never overwrites an edited host
- **WHEN** a host's card was edited to version 2 and synchronization runs again after the authored profile text changed
- **THEN** the host's card and version 2 are unchanged

#### Scenario: A reused host without a card is left untouched
- **WHEN** synchronization reuses an existing host that carries no persona metadata
- **THEN** synchronization writes no persona or metadata for it

#### Scenario: A failed initialization leaves no host
- **WHEN** the card initialization raises while synchronization creates a host
- **THEN** the startup transaction rolls back and no host for that service exists
