# narrative-context Specification

## Purpose

Builds reproducible permission-filtered cognition inputs with enforceable rendered budgets and immutable provenance across retries and effective-state changes.

## Requirements

### Requirement: Rendered context obeys profile budgets

Context SHALL use stable ordering and one rendered representation for selection and assembly. Section soft targets and hard input bounds SHALL reserve completion, Deep Recall capacity and estimation safety. Mandatory contracts/permission information SHALL NOT be silently removed.

#### Scenario: Rendered headings exceed budget
- **WHEN** text fits a target but headings/attribution exceed the rendered bound
- **THEN** selection reduces deterministically or mandatory overflow rejects before generation

### Requirement: Generation retains an immutable source snapshot

Important generation SHALL retain capability, prompt/schema/rendering versions, source IDs/read revisions, section hashes, accounting and truncation decisions. Retry SHALL reuse that snapshot. Hashes alone SHALL NOT represent reconstructible omitted content. Owner-generation changes SHALL invalidate new-generation caches without rewriting historical snapshots.

#### Scenario: Sources change before retry
- **WHEN** effective memory changes after capture
- **THEN** retry uses captured revisions while new generation sees the changed generation

#### Scenario: Offline reconstruction
- **WHEN** the process restarts with services disabled
- **THEN** retained snapshots reconstruct and permitted recall remains deterministic

### Requirement: Observability protects private prompt data

Operational logging SHALL use world.observability stable events, context and exception chains. Normal logs SHALL contain IDs/counts and actual token/cache/retry/degrade/latency accounting, not player text, secret values, full personas or prompts. Full debug payloads SHALL require opt-in controlled storage.

#### Scenario: Private generation is traced
- **WHEN** generation succeeds or degrades with private sources
- **THEN** normal traces contain accounting and identifiers without private text
