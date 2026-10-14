# bundled-scene-art Specification

## Purpose
Define the complete built-in official scene collection, immutable type declarations and confined fingerprinted media serving independent of operator art.

## Requirements

### Requirement: Every registered scene has complete required bundled artwork
Every registered normal archetype plus dream_throne SHALL have a required bundled official WebP and an authored terminal reference. The terminal SHALL be city_street or forest_path. Future archetypes SHALL add their declaration and real artwork together.

#### Scenario: Complete collection is valid
- **WHEN** the contract enumerates the scene registry and explicit dream type
- **THEN** all eleven required images decode within resource limits and every terminal points to a required image

#### Scenario: Broken coverage names its source
- **WHEN** a required image is absent or corrupt, a declaration is missing, or a terminal references an unregistered key
- **THEN** the contract fails naming the affected scene key; runtime still degrades without blocking gameplay

### Requirement: Bundled media has a closed trusted namespace
Bundled scene media SHALL use a closed scene-key identity and content fingerprint under a fixed repository root distinct from operator roots. Requests SHALL retain confinement, no-follow opening, decode admission and actual 404 failure semantics. An operator file SHALL NOT replace a bundled identity or terminal image.

#### Scenario: Operator collisions cannot replace bundled art
- **WHEN** an operator supplies a matching scene filename or attempts a bundled identity
- **THEN** the bundled media boundary serves only repository-admitted bytes at the current fingerprint

#### Scenario: Missing media is a real failure
- **WHEN** a required file disappears after snapshot admission
- **THEN** its media request returns 404 rather than substitute bytes or successful status

#### Scenario: Traversal and stale tokens are refused
- **WHEN** a request contains an unknown scene key, symlink, traversal or outdated fingerprint
- **THEN** it receives 404 without exposing filesystem roots
