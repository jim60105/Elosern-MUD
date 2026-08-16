## RENAMED Requirements

- FROM: `### Requirement: SKILL_REGISTRY's 117 entries partition exactly across the eight categories`
- TO: `### Requirement: SKILL_REGISTRY's entries partition exactly across the eight categories`

## MODIFIED Requirements

### Requirement: SKILL_REGISTRY's entries partition exactly across the eight categories
Every key in `SKILL_REGISTRY` SHALL have a `category` that is a valid `SkillCategory` member. The
union of the eight categories' member sets, computed by grouping `SKILL_REGISTRY` by each entry's
`category`, SHALL equal `set(SKILL_REGISTRY.keys())` exactly, with no key counted in more than one
category and no category naming a key absent from `SKILL_REGISTRY`.

#### Scenario: Every registry key has a valid category
- **WHEN** `SKILL_REGISTRY` is iterated
- **THEN** every entry's `category` is a member of `SkillCategory`

#### Scenario: The per-category partition covers the registry exactly
- **WHEN** `SKILL_REGISTRY`'s keys are compared against the union of keys grouped by `category`
- **THEN** the two sets are identical, and no key appears in more than one category's group

#### Scenario: A later proposal fills exactly one module with no other file touched
- **WHEN** the seven seed acts are registered alongside the pre-existing 117 skills
- **THEN** the registry still partitions exactly, with the seven new `SEXUAL_ACT`-category entries in
  the `sexual_act` category group and the category count unchanged at eight
