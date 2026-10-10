# Spec Delta

## MODIFIED Requirements

### Requirement: Data-contract tests are explicitly classified
Every test file intentionally exercising shipped content SHALL retain the exact `Data-contract test:` first-docstring-line tag (or leading JS/TS comment) and matching contract ledger reason. The classification SHALL permit generic schema/reference/content-quality checks and minimal real consumer smoke. It SHALL NOT authorize duplicated mutable balance tables, literal production magnitude pins, mock forwarding echoes or expected values obtained by calling the same production calculation. Fixed synthetic mechanism fixtures MAY use independently known literal results.

#### Scenario: Tag and ledger agree
- **WHEN** the gate reads a contract entry
- **THEN** tag and reason agreement remains mandatory and an absent/empty/divergent tag fails with the existing untagged-contract violation

#### Scenario: Classification remains discoverable
- **WHEN** contributors search Data-contract test tags
- **THEN** every intentionally shipped-content test has its matching ledger reason and behavior-only tests are absent

#### Scenario: Mutable data cannot be approved by duplication
- **WHEN** an author changes a valid balance magnitude within existing explicit invariants
- **THEN** content checks pass without updating a second expected-value table, while relevant shared synthetic mechanism tests still execute unchanged

## ADDED Requirements

### Requirement: Production content checks validate references without numerical approval mirrors
Shipped-content tests SHALL validate schema, ownership/identity, references, recipients, earlier-hit dependencies and profile bindings without duplicated mutable-value expectations. Established quality, polarity, security and authoring bounds SHALL remain. Each assertion SHALL name its detectable defect.

#### Scenario: Reference integrity failure
- **WHEN** a scoped fixture or temporary content perturbation introduces a missing effect/status/modifier/profile, invalid ownership, wrong recipient or invalid hit dependency
- **THEN** the relevant check fails by declaration and reference without accepting a copy of that declaration as its oracle

#### Scenario: Valid magnitude edit
- **WHEN** a production magnitude changes within established schema and intentional invariants
- **THEN** the content test remains green unchanged

### Requirement: Shared synthetic mechanism coverage owns independently known outcomes
Engine behavior tests SHALL use fixed synthetic fixtures and independently known consumer-visible outcomes. Expectations SHALL NOT call the calculation under test, duplicate its formula in a helper, or echo mock inputs. Shared coverage SHALL replace cloned per-species engine vectors.

#### Scenario: Fixed mechanism oracle
- **WHEN** a synthetic transfer fixture starts with target MP 3, requests removal 10 with full share, and starts caster MP 20 with cost 10
- **THEN** actual target MP ends at 0 and caster MP ends at 13, independently of production crocodile tuning

#### Scenario: Broken execution fails
- **WHEN** payment, recipient routing, hit qualification, rollback or durable reload behavior is perturbed
- **THEN** shared tests fail on independently observed state, including untouched controls, resource deltas and committed persistence

### Requirement: Representative production smoke proves real consumer integration proportionally
Representative production smoke SHALL execute real construction, selection, resolution, settlement and persistence. Declaration-derived expectations SHALL establish a distinct consumer boundary and name its detectable defect; they SHALL NOT claim calculation correctness. Exact mechanism vectors SHALL remain shared.

#### Scenario: Distinct consumer workflows
- **WHEN** representative crocodile drain, sparrow enemy hit-rider and crab hit-independent self-guard compositions are constructed and selected through a real session
- **THEN** execution produces independently observed recipient changes, leaves controls untouched, applies payment and retains committed depleted state after reload

#### Scenario: An agreement assertion has bounded evidence
- **WHEN** expected input comes from a declaration but committed state comes from a different consumer boundary
- **THEN** the test states which wrong consumer wiring it detects; shared-oracle agreement alone is never claimed to prove calculation correctness
