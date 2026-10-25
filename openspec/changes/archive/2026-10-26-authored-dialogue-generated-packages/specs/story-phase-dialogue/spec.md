# Spec Delta

## MODIFIED Requirements

### Requirement: Packages declare complete finite dialogue phases
Every reachable per-role phase SHALL provide bounded greeting, complete shared topic scenes/variants/qualification/refusal/predecessors, validated conditions/effects, freeform situation/goals and offline response before publication. Phase facts SHALL remain registered deterministic predicates. Missing coverage, ambiguous/conflicting selection, automatic cycles and generated code SHALL reject. Old response-only topics SHALL be unsupported.

#### Scenario: Phase content remains in-world and private
- **WHEN** fixed or generated phase dialogue is validated and presented
- **THEN** it uses in-character Traditional Chinese without command names, mechanics, UI instructions, private authoring text or hidden locations

#### Scenario: Invalid phase coverage rejects publication
- **WHEN** a package omits a reachable phase or declares overlapping selection, an automatic cycle, or unsupported condition/effect code
- **THEN** publication fails before any writes

#### Scenario: Complete scenes replace response-only topics
- **WHEN** a package topic declares valid shared scene primitives or instead the old response-only fields
- **THEN** the complete scene is accepted under shared bounds and the old representation rejects without compatibility conversion

### Requirement: Phase selection uses committed outcomes and permitted role knowledge
Phase selection SHALL use committed observations and per-role permitted knowledge. Exact participant identities/provenance SHALL drive deterministic transitions with monotonic revision, preserving persona/history. Global stage changes SHALL confer no remote knowledge. Escort/reunion facts SHALL require existing committed owner authority and never derive from prose. Topic conditions SHALL use the shared permitted canonical/package reference catalog.

#### Scenario: Unknown information stays out of mother-first dialogue
- **WHEN** a searching role is encountered first without knowledge of its related role's location or private source text
- **THEN** fixed topics and free-form context disclose neither, and later committed permitted information transfer can change its knowledge and eligible phase

#### Scenario: Generic closure and unresolved outcomes select different phases
- **WHEN** a synthetic package receives committed supported closure observations through the deterministic transition boundary, or separately receives abandonment while separation remains true
- **THEN** closure selects everyday greetings/topics without the old commission choice, abandonment selects unresolved content, and both preserve prior memories

### Requirement: Phase revision invalidates pending dialogue work
Phase change SHALL refresh live greeting/topics and retire obsolete scene deliveries, choice/reading receipts and notification scope through the common versioned surface. Obsolete freeform replies SHALL emit no speech/intent/memory. Historical dialogue and saved same-phase topic completion SHALL remain unchanged; an old topic SHALL never be reinterpreted as a new phase action.

#### Scenario: Old choice and late reply are refused
- **WHEN** a choice or pending free-form reply captured before a phase revision is delivered afterward
- **THEN** neither applies effects or appends obsolete dialogue, late speech is suppressed, and the current window receives refreshed content

#### Scenario: Old acknowledgement is retired without resetting reading
- **WHEN** an old-phase completion retries after transition and that phase later becomes permitted again
- **THEN** the old receipt rejects while already saved completion for that phase remains available
