# Spec Delta

## ADDED Requirements

### Requirement: Identity edits preserve a creation portrait without warnings
Changing sex, race, subrace or apparent age, applying a concept, or saving a revised custom draft SHALL preserve the creation portrait and any in-flight request. These edits SHALL neither invalidate the portrait nor emit a portrait-mismatch warning. New generation remains an explicit player choice.

#### Scenario: Ready art survives edited identity
- **WHEN** a player edits identity fields after a draft portrait is ready and saves the custom form
- **THEN** the same portrait remains, no cleanup/regeneration action is submitted, and no portrait-mismatch warning appears

#### Scenario: Pending work uses its admitted snapshot
- **WHEN** a player changes identity while a draft portrait is pending
- **THEN** that request remains attached to its admitted values and may complete, with no invalidation or warning from the newer form values
