# monster-ai-legal-candidates Specification

## Purpose
Enumerate semantically legal, deduplicated damage plans under a hard proposal budget. This capability defines observable behavior at the monster decision boundary.

## Requirements

### Requirement: Candidate plans preserve actual skill semantics
Candidates SHALL use owned active supported hostile damage skills and their authored scale and target policies. SINGLE SHALL enumerate valid targets; enemy AREA SHALL use one legal group; SELF and NONE SHALL use existing implicit binding. Mixed plans SHALL use bounded legal audience combinations without arbitrary subset enumeration.

#### Scenario: Mixed and self effects
- **WHEN** a mixed skill permits a complete roster and legal friendly/hostile subsets
- **THEN** at most one plan per distinct allowed audience combination is produced; self-bound effects still bind the actor

#### Scenario: Unrepresentable harm
- **WHEN** a plan contains unsupported potentially harmful effects or inconsistent recipient semantics
- **THEN** that candidate is excluded with a reason while supported alternatives remain eligible

### Requirement: Mandatory single target restrictions precede utility
Hostile SINGLE damage SHALL first restrict to applicable lamb_seal bearers. Without a genuinely castable non-strike hostile SINGLE damage alternative, displaced targets SHALL be removed. With seals, the first remaining bearer in canonical order SHALL be used. Strike-only candidates SHALL always exclude displaced targets.

#### Scenario: Seal and displacement order
- **WHEN** multiple seals include displaced bearers and the only non-strike skill is self-healing or is uncastable
- **THEN** no alternate hostile attack is inferred; the first remaining bearer is selected in player-first then stable-pk order

#### Scenario: Independent attack families
- **WHEN** an actor has a castable non-strike hostile SINGLE damage alternative and a strike skill
- **THEN** non-strike plans can reach displaced targets; strike plans cannot; AREA and friendly support are not seal restricted

### Requirement: Canonical deduplication preserves executable representation
Equivalent candidates SHALL be deduplicated by skill, scale and sorted stable explicit target identifiers after shorthand expansion. The selected request SHALL retain its legal runtime target representation and scale.

#### Scenario: Duplicate shorthand
- **WHEN** the same legal AREA action appears as shorthand and an equivalent explicit roster
- **THEN** it has one sampling identity; the runtime shorthand is not converted into characters and non-default scale remains intact

### Requirement: Proposal work is deterministically bounded
The initial candidate budget SHALL be 256 and configurable in integer 1..4096. It SHALL bound deduplicated examined proposals including rejected plans. Slots SHALL be allocated round-robin across canonical skill/semantic-plan families after mandatory filtering, with a scope-digest starting offset.

#### Scenario: Exhaustion
- **WHEN** families and targets exceed the budget or many proposals fail legality
- **THEN** enumeration terminates at the bound; omitted family/target counts and exhaustion are reported without a participant cap or selection/combat RNG draw

#### Scenario: Target order and no action
- **WHEN** targets tie under the profile order or all legal plans are excluded
- **THEN** stable IDs order ties; an empty legal set returns None without forced attack or legacy fallback
