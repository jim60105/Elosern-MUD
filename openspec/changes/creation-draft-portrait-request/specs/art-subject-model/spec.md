# Spec Delta

## ADDED Requirements

### Requirement: Draft portrait descriptions use only validated request values
A pending-character portrait description SHALL use the validated request’s parent-race display label and apparent age plus accepted free text through the existing character-description template. It SHALL read no pending-shell identity, persona, equipment, concept text or display name, and SHALL render no appearance/equipment contribution.

#### Scenario: Stored identity cannot override the draft
- **WHEN** a pending shell’s stored identity disagrees with a valid synthetic draft-portrait input
- **THEN** the rendered description uses the input’s registry parent-race label and apparent age, contains accepted normalized free text, and reads none of the shell’s identity/persona/equipment data

#### Scenario: Description validation precedes rendering
- **WHEN** draft values or custom prompt fail their shared validation
- **THEN** no template render, queue write or policy change occurs

#### Scenario: Existing composition remains equivalent
- **WHEN** the same validated race and apparent age are composed from a draft input and from an activated character with no selected fields and the same free text
- **THEN** their description template inputs agree; existing prompt-unavailable degradation remains registry-driven and persona-free
