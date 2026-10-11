# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: Monster species references await the separate species catalog and forbid tier substitution`
- TO: `### Requirement: Monster species references use declared visual provenance and forbid tier substitution`

## MODIFIED Requirements

### Requirement: Monster species references use declared visual provenance and forbid tier substitution
Species-specific monster official artwork SHALL resolve from validated stored complete-species provenance, or explicit baseline visual provenance only when complete-species provenance is absent. Both sources SHALL use the registered visual vocabulary; no display-name inference or threat-tier substitution is permitted.

#### Scenario: Monsters resolve no official image before the catalog exists
- **WHEN** a monster has registered complete-species or baseline visual provenance and its species directory is mounted
- **THEN** the resolver returns exactly that monster visual reference; absent provenance resolves no reference and never uses tier or name matching

#### Scenario: A threat tier never borrows a species image
- **WHEN** a monster has only a threat tier and a display name textually equal to a catalog directory
- **THEN** no visual reference is inferred; the monster presents monster_anon

#### Scenario: Synthetic species references resolve when supplied
- **WHEN** a test injects a species/content reference provider and asks the resolver for a monster carrying a validated species reference
- **THEN** the resolver answers with that monster's own reference — never a sibling content key's — leaving content existence and presentation to the resolution layer

#### Scenario: Tiers are never substituted or mapped to
- **WHEN** any code path resolves a monster's official artwork
- **THEN** it never substitutes a threat tier for a species reference, never maps an unknown species to a tier, and never reuses one content reference's official image for another subject

#### Scenario: Shared-by-species behavior is spawn-independent
- **WHEN** a species reference provider exists and individuals of one species spawn at differing places or in differing numbers
- **THEN** the shared-by-species image behavior is independent of where or how many individuals spawn

