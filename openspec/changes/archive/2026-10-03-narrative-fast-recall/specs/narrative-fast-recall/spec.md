## Purpose

Selects relevant permitted memories deterministically using calibrated Traditional Chinese lexical recall with intentional empty results.

## ADDED Requirements

### Requirement: Permissions and explicit scope precede recall scoring

Recall SHALL filter owner knowledge and explicitly requested available thread scope before scoring. It SHALL combine bounded fixed selection with lexical/entity recall and deterministic ties, working without network generation.

#### Scenario: Informed and uninformed ask the same question
- **WHEN** two roles ask about protection but only one knows the event
- **THEN** only the informed role can retrieve the episode

#### Scenario: Rebuilding preserves results
- **WHEN** an index is rebuilt offline from identical effective records and versions
- **THEN** ordered selected source IDs are unchanged

### Requirement: Metadata cannot create unrelated recall

Candidates SHALL pass a precision-first lexical threshold before metadata bonuses rerank them. No qualifying candidate SHALL produce an empty recalled result.

#### Scenario: Salient unrelated episode loses
- **WHEN** an unrelated salient episode competes with a related protection episode
- **THEN** only lexical candidates qualify

#### Scenario: All episodes are unrelated
- **WHEN** a query concerns a subject absent from permitted memory
- **THEN** no recalled memory is returned

### Requirement: Project labeled evidence determines recall gates

Project-owned synthetic labeled cases SHALL measure Recall@1, Recall@2, false positives and latency, with committed calibrated gates and corpus/version/environment information.

#### Scenario: Calibration covers negative and historical cases
- **WHEN** the corpus is evaluated
- **THEN** the report includes all measurements and normal inactive exclusion versus historical retrieval

