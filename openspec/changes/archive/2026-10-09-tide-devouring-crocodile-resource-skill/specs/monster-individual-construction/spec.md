# Spec Delta

## MODIFIED Requirements

### Requirement: Species-backed individuals are constructed through one validated deterministic entry point
The existing `Monster` typeclass SHALL carry persistent `species_key` and `variant_key` identity
alongside its existing traits, state, and location data. Exactly one construction entry point owned
by the deterministic core SHALL create a species-backed individual: it SHALL validate that both keys
resolve in the species/variant registries and that the variant belongs to the species before any
persistence. It SHALL also validate the complete ordered active/passive kit, matching skill kinds,
identity qualification, prerequisite usability, supported effects and optional behavior-profile reference.
Identity, literal traits, ownership and behavior binding SHALL be applied atomically; failures leave no individual.

#### Scenario: A mismatched species and variant pair builds nothing
- **WHEN** construction is asked for a variant whose owning species differs from the supplied species key
- **THEN** construction raises a named construction error and a database before/after comparison shows no new individual

#### Scenario: An unknown key builds nothing
- **WHEN** construction is asked for a species key or variant key absent from the registries
- **THEN** construction raises the named error and no individual exists afterwards

#### Scenario: Names never carry identity
- **WHEN** an individual is created with a display name that matches a registered species' display text but with no species key
- **THEN** it is not a species-backed individual and resolves no species identity from its name

#### Scenario: Identity is never inferred from incidental strings or roles
- **WHEN** species or variant identity would have to come from a display name, an object key string, a threat tier, a quest role, or generative output
- **THEN** it is NOT inferred from any of these; only the validated persistent keys carry identity

#### Scenario: A failed construction leaves nothing behind
- **WHEN** a construction fails validation
- **THEN** it leaves no partially built individual behind

## ADDED Requirements

### Requirement: Constructed kits and depleted resources survive reload without registry resets
Individual persistence SHALL retain identity, owned kit, bound behavior profile and current gauge values. Registry changes SHALL NOT refill or rescale live individuals. Variants without special kits SHALL retain innate actions and tier-default behavior.

#### Scenario: Reload is not reconstruction
- **WHEN** a formally constructed individual spends MP/SP and is reloaded
- **THEN** identity, owned order and behavior binding persist and current depleted gauges are unchanged

#### Scenario: Registry changes leave live state alone
- **WHEN** a variant profile or kit is edited after creation
- **THEN** existing ownership and gauges are not reset by startup or reload; an authorized GM workflow is required for live changes

#### Scenario: Other species retain their defaults
- **WHEN** a variant has no authored special kit or behavior binding
- **THEN** construction keeps basic_attack/flee and tier-default policy with no inferred spells or pools

