## ADDED Requirements

### Requirement: The defeat entry carries species and variant identity for species-backed monsters
Step 7's `target_defeated` entry SHALL additionally carry the defeated monster's registered
`species_key` and `variant_key` when the target is a species-backed individual, and SHALL omit both
fields (or carry `None`) for a tier-only individual. Consumers SHALL resolve species or variant identity
only from these fields, never by matching the target's display key or threat tier against registry text.
The existing carriage — integer `target_id` dbref and monster tier or `None` — SHALL stay unchanged, and
non-Monster targets SHALL be unaffected.

#### Scenario: A species-backed defeat carries its registered identity
- **WHEN** pending damage lethally crosses a species-backed monster
- **THEN** the `target_defeated` entry carries `target_id`, the tier, and the individual's registered species and variant keys

#### Scenario: A tier-only defeat carries no species fields
- **WHEN** a tier-only monster (no species identity) is defeated
- **THEN** the entry carries `target_id` and its tier exactly as before, with no species or variant value, and consumers treat it as identityless

#### Scenario: No consumer name-matches the registry
- **WHEN** a defeat consumer needs to know the defeated species
- **THEN** it reads the entry's species key, and no consumer resolves species identity by comparing a display name or tier against registry display text
