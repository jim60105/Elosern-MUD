# Spec Delta

## Purpose

Own deterministic persistent ordinary monster births, individual budgets and atomic initialization independently from transient wilderness rooms and foreign placement owners.

## ADDED Requirements

### Requirement: Automatic births satisfy local and home-owned individual ceilings
Automatic birth waves SHALL count living individuals independently against local-zone, home-owned, per-cell and per-wave ceilings, retaining ownership independently from current presence.

#### Scenario: Local and home measures
- **WHEN** a zone-owned living member leaves or detaches while a foreign visitor arrives
- **THEN** the member still consumes home headroom, the visitor consumes local headroom, each ID is counted once per measure and ownership is unchanged

#### Scenario: Manual excess
- **WHEN** manual, site or quest individuals exceed a local or cell ceiling
- **THEN** automatic births stop without deleting, relocating or modifying any existing individual

#### Scenario: Complete fitting groups
- **WHEN** a weighted composition has multiple count outcomes
- **THEN** only complete legal outcomes fitting every ceiling are selected; no row is truncated below its minima

### Requirement: Birth occurrences retain deterministic persistent individual state
Population initialization and successful waves SHALL persist selection seed and sequence with fresh individual identities and home ownership, reselecting position and composition per occurrence without replacing living survivors.

#### Scenario: Initialization once
- **WHEN** an initialized world reloads, rereads source, prepares or recycles a room, or receives a player
- **THEN** the same living IDs, consumed resources, initialization flag and selection state remain; no initial filling repeats

#### Scenario: Occurrence selection
- **WHEN** two lawful births use different saved occurrence inputs in a synthetic pool
- **THEN** selection can differ at the same coordinate and replay of either input reproduces its own complete plan

#### Scenario: No materialized room
- **WHEN** a birth occurs at an eligible inactive coordinate
- **THEN** the actual ID is registered without creating a room and later activation attaches that same ID

### Requirement: Population wave commit is atomic across durable and live surfaces
Each wave SHALL commit its complete constructed population, registrations, attachments and selection state atomically with surrounding owned settlement, restoring durable state and live caches on any later failure.

#### Scenario: Failure after real writes
- **WHEN** a fault follows an actual member construction and coordinate registration or a later scheduling/state write
- **THEN** DB reload and in-process state equal baseline, no half-group or success event remains and retry repeats the failed selection

#### Scenario: Protection and refusals
- **WHEN** birth space is protected by an active encounter, unavailable or temporarily full
- **THEN** no enemy is appended to a persisted session; invalid authoring and unavailable world state are distinct from temporary blocked birth space

#### Scenario: Commit observability
- **WHEN** a wave commits or an unchanged read runs
- **THEN** only the committed wave emits its bounded facade boundary event with available identifiers; reads emit no mutation event

