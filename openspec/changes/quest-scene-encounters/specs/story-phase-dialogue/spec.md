# Spec Delta

## Purpose

Select complete generated story dialogue phases from committed observations while preserving role knowledge and conversation history.

## ADDED Requirements

### Requirement: Packages declare complete finite dialogue phases

Every reachable per-role phase SHALL provide bounded fixed greeting/topics/responses, validated conditions/effects, free-form situation/goals and offline response before publication. Only registered deterministic predicates SHALL be allowed. Missing coverage, ambiguous selection, conflicting selection, automatic cycles and generated expressions/code SHALL reject.

#### Scenario: Phase content remains in-world and private
- **WHEN** fixed or generated phase dialogue is validated and presented
- **THEN** it uses in-character Traditional Chinese without command names, mechanics, UI instructions, private authoring text or hidden locations

#### Scenario: Invalid phase coverage rejects publication
- **WHEN** a package omits a reachable phase or declares overlapping selection, an automatic cycle, or unsupported condition/effect code
- **THEN** publication fails before any writes

### Requirement: Phase selection uses committed outcomes and permitted role knowledge

Phase selection SHALL use committed observations and per-role permitted knowledge. Exact participant identities and committed provenance SHALL drive owner-API transitions with monotonic revision, preserving persona and historical turns. Global stage changes SHALL confer no remote knowledge. Escort/reunion observations SHALL remain guarded until their owner lands and SHALL never derive from prose.

#### Scenario: Unknown information stays out of mother-first dialogue
- **WHEN** a searching role is encountered first without knowledge of its related role's location or private source text
- **THEN** fixed topics and free-form context disclose neither, and later committed permitted information transfer can change its knowledge and eligible phase

#### Scenario: Generic closure and unresolved outcomes select different phases
- **WHEN** a synthetic package receives committed supported closure observations through the deterministic transition boundary, or separately receives abandonment while separation remains true
- **THEN** closure selects everyday greetings/topics without the old commission choice, abandonment selects unresolved content, and both preserve prior memories

### Requirement: Phase revision invalidates pending dialogue work

A phase change SHALL refresh live greeting/topic models and invalidate obsolete choice capabilities using the existing versioned surface contract. A reply captured under an obsolete phase revision SHALL deliver no speech, apply no intent, and append no memory or exchange; the current phase SHALL be refreshed instead. Historical dialogue SHALL remain unchanged and an old topic SHALL never be reinterpreted as a new phase action.

#### Scenario: Old choice and late reply are refused
- **WHEN** a choice or pending free-form reply captured before a phase revision is delivered afterward
- **THEN** neither applies effects or appends obsolete dialogue, late speech is suppressed, and the current window receives refreshed content
