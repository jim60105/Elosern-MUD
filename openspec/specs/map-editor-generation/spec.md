# map-editor-generation Specification

## Purpose
Run explicit partition jobs outside the request loop with cancellation, mutation exclusion and fingerprint-guarded output publication. This capability defines the observable mechanism boundary for its consumers.

## Requirements

### Requirement: Explicit generation isolates inputs and guards publication
Partition generation SHALL run one explicit job at a time outside request handling, reject world-data mutation while running, and publish atomically only for still-current captured inputs with no write pause or stale preview.

#### Scenario: Changed source
- **WHEN** external source replacement occurs during a running job
- **THEN** the result cannot publish as current and the last artifact remains intact

#### Scenario: Cancellation and browsing
- **WHEN** a user browses then cancels a running partition job
- **THEN** requests remain responsive, cancellation/failure leaves the last output unchanged and no second job or world mutation is admitted

### Requirement: Partition status distinguishes source persistence from output freshness
The editor SHALL expose the input revision and current, stale, generating, cancelled or failed output state without automatically regenerating on ordinary edits.

#### Scenario: Old output
- **WHEN** a relevant saved source edit makes existing output stale
- **THEN** old geometry is labelled older-input and game-readiness is withheld until explicit successful regeneration
