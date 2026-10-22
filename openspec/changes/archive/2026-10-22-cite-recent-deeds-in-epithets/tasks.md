# Tasks

## 1. Prompt input cutover

- [x] 1.1 Replace old EventLog context/serializer and all callers with the authorized detached feed; verify actual adult structured outcomes, identities/roles and provenance survive prompt construction and no live entities or forbidden private fields serialize.
- [x] 1.2 Keep identity/full title and advisory decline/removal preferences while excluding fixed/live-owned names and collision rules; verify prompt tests, update prompt documentation and traceability, and remove obsolete serializer coverage.

## 2. Cited candidate admission

- [x] 2.1 Add request-bounded source_ids response fields and membership validation while preserving ordered display/collision filters and first-three survivors; verify empty/duplicate/unknown/omitted-source citations, duplicate-display interaction, one/two/zero survivors and whole-round shape/count/field-size failures.
- [x] 2.2 Consume citations before the existing display/basis ballot writer and retain provenance in transcripts; verify stored ballot/title shapes and cross-session accept/decline behavior remain unchanged, no model call for empty/disabled cases, no cooldown on offline/void output, and register added tests.

## Integration gate

- [x] 9.1 Run this slice's focused synthetic tests, observability lint for logging changes, and repository contract gate after integration; record commands and outcomes. Full browser suites and complete evidence verification remain CI-owned.
