# Spec Delta

## MODIFIED Requirements

### Requirement: Portrait focus stays client-local against the art catalog seam
Exploration look/interact descriptors SHALL carry null or an unchanged bounded ASCII-decimal portrait_ref. Every non-null reference SHALL name an admitted canonical entry regardless of real-image availability. Existing visibility, capacity, age eligibility and no client-built URL/key rules SHALL remain; admitted missing/pending/failed/alpha-only subjects SHALL retain their reference.

#### Scenario: Absence of art never blocks exploration
- **WHEN** the art catalog is absent or a descriptor carries `portrait_ref: null`
- **THEN** look, interact, and dialogue operate normally, and no portrait card or focus packet is produced

#### Scenario: Catalog-driven focus is verified
- **WHEN** the server supplies a `portrait_catalog` and an exploration descriptor references a catalog identity
- **THEN** client-local focus switches only to that server-verified value and no subject key or URL is constructed by the browser

#### Scenario: Missing art is never a failure
- **WHEN** an admitted descriptor has expected missing imagery, or no subject is admitted
- **THEN** expected absence has no error marker; a real panel availability failure is indicated locally while look/interact/dialogue remain usable

#### Scenario: Both descriptor paths join the same current image
- **WHEN** the same authorized entity occurs in look and interact and the bounded art view
- **THEN** both rows carry the same catalog reference and complete descriptor including missing-source facts

#### Scenario: A non-interact entity can carry an admitted portrait
- **WHEN** a present named-policy character is catalogued with real imagery and appears only in the look-entity list
- **THEN** its entity row carries the catalog reference while its existing look payload and bystander eligibility remain unchanged

#### Scenario: Catalog exclusion remains a truthful null
- **WHEN** an entity is excluded from the existing art membership or dropped by its 32-entry cap, including a non-catalogued monster with otherwise resolvable art
- **THEN** its exploration reference is null and no catalog expansion or browser-generated key occurs

#### Scenario: Missing and ineligible imagery never becomes a real reference
- **WHEN** an authorized catalogued entity lacks real art or fails named-policy/age eligibility
- **THEN** its reference names the admitted safe descriptor without forbidden real candidates; no job or gameplay mutation occurs and exploration remains usable

#### Scenario: Exact validators preserve admitted reference values
- **WHEN** either descriptor carries null or an ASCII-decimal reference of length 1 or 32, and then an empty, overlong, numeric, Unicode-digit, subject-key or URL-like value
- **THEN** both validators accept and preserve the first values and reject the latter values without coercion; exact fields and envelope bounds still apply

#### Scenario: Available exploration survives unavailable art
- **WHEN** the art capability cannot supply its view or the client receives an unavailable art panel
- **THEN** exploration actions remain available, refs without a supplied view are null and unresolved client refs use the established fallback without a focus request

