# Spec Delta

## MODIFIED Requirements

### Requirement: Eligibility checks order before official and runtime presentation
Portrait age and eligibility validation SHALL precede official/runtime character artwork. Ordinary characters SHALL pass canonical checks; an authorized pending draft receipt SHALL instead prove its validated draft request and exact owned card. Rejected inputs SHALL expose no image URL or prompt. Catalog metadata and crafted media URLs SHALL NOT grant eligibility.

#### Scenario: Directory metadata cannot unlock an ineligible character
- **WHEN** a character whose canonical ages fail the existing check has a content reference whose official directory is fully valid
- **THEN** no official URL or rectangle is presented for it and the truthful placeholder is returned

#### Scenario: Presentation adds no bypass
- **WHEN** a direct request names a well-formed official media URL for an ineligible entity's content directory
- **THEN** presentation-layer surfaces never construct such a URL, and the media route's own rules (capability `art-queue-worker`) remain the only official URL admission

#### Scenario: Built-in placeholder selection keeps its validated attributes
- **WHEN** built-in placeholder selection runs for an entity without a named portrait policy
- **THEN** it remains able to use validated entity attributes for that selection

#### Scenario: Official artwork never changes the eligibility outcome
- **WHEN** eligibility is evaluated for an entity once with official artwork present and once without
- **THEN** the eligibility outcome is identical whether or not official artwork exists for the entity

#### Scenario: Draft receipt authorizes only its exact validated output
- **WHEN** creation presents a pending character’s successful draft portrait while canonical identity remains unset
- **THEN** its valid rule-owned receipt and completed owned image authorize only that runtime card and alpha terminal; another subject/id, an invalid receipt or an unvalidated request yields no ready artwork
