# Spec Delta

## ADDED Requirements

### Requirement: Gallery previews retain exact image identity and reached failures
Gallery card thumbnails, official rows, detail rails and binding/generation references SHALL use the common ordered load result for the exact requested image. Preview failure MAY show the subject silhouette without changing card status, selecting another original or enabling substitute editing. Reached unexpected faults SHALL remain locally accessible after preview fallback.

#### Scenario: Preview substitute preserves the requested card
- **WHEN** a card original fails and its alpha fallback decodes
- **THEN** its own card remains selected with its status unchanged and a persistent accessible failure marker; no different card becomes original

#### Scenario: All preview readers share the result
- **WHEN** the same exact original appears in card, official-row, detail, binding or generation surfaces
- **THEN** each uses the common lifecycle and shared message categories without a local failed-URL selector
