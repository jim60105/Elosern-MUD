# Proposal

## Why

Mutable game balance currently appears as duplicate approval tables and literal outcomes in implemented specs and tests. Authoring a valid balance edit then requires changes to both copies, while long creature-specific smoke suites repeat shared engine coverage.

## What Changes

- Replace numerical approval mirrors across all implemented current contracts with authored-data/schema/reference checks, independently known synthetic mechanism outcomes and representative real consumer smoke.
- Preserve existing mechanics, identity/ownership/recipient/hit-dependency rules, transaction rollback, persistence, security and explicit content-quality invariants. Preserve `usable_out_of_combat=True` on every damage ability, including crocodile declarations; battlefield resolution remains separately gated.
- Remove `APPROVED_BALANCE` and equivalent mutable per-row tables from tests rather than relocate them. Reuse shared engine suites and state the defect each retained assertion detects.
- Migrate relevant tests, their requirement associations, contract tags/ledger reasons and authoring documentation together. No production balance edits, compatibility layer, save migration or runtime feature is included.
- Treat archive artifacts as immutable history. Current main specs are the implementation-phase destination for these deltas; every existing unimplemented proposal is untouched.

## Capabilities

### New Capabilities

None. Existing test-design and content capabilities own this contract.

### Modified Capabilities

- `affinity-cap-break`: keep cap-raise ordering while treating quest gains as authored data.
- `affinity-system`: preserve the canonical stage ladder and move budgeting examples to synthetic fixtures.
- `buff-handler-integration`: retain ordered tick records without pinning shipped buff deltas.
- `church-ordination`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `combat-modifier-table`: retain merge, routing and cost mechanics without pinning production adjustments.
- `defeat-aftermath-recovery`: retain the wake solver and rollback while reading the authored wake fraction.
- `entity-trait-scales`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `equipment-effects`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `guild-exam-restrictions`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `human-guild-hosts`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `lore-registries`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `masterwork-price-band`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `military-equipment`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `monster-action-policy`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `monster-individual-construction`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `monster-resource-abilities`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `monster-species-registry`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `party-system`: retain atomic companion quest gains without pinning the authored gain.
- `quest-reward-settlement`: retain cap-before-gain and reward rollback with synthetic exact outcomes.
- `saintess-vessel`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `sexual-act-effects`: retain pleasure calculation behavior with independently known synthetic multipliers.
- `sexual-catalog-combat`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `sexual-catalog-interspecies`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `sexual-catalog-partner`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `sexual-catalog-shame`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `sexual-catalog-solo`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `sexual-state-handler`: retain derived state and exposure behavior with synthetic band examples.
- `sexual-transition-rulebook`: retain sanctioned writers and phase transitions without pinning shipped deltas.
- `skill-lineage`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `skill-registry`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `spec-test-traceability`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `starting-companions`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `test-data-independence`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `title-system`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `wilderness-gateway`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.
- `wilderness-monster-population`: retain deterministic placement without a duplicate density table.
- `world-clock`: revise mutable-value test contracts while retaining the existing mechanics and intentional invariants.

## Impact

The complete baseline is 311 current capabilities and 2,074 requirement headings. `scope-inventory.md` records every capability and all 94 classified content-test files; `test-migration.md` identifies concrete migrations and shared coverage. Delta specs modify 98 existing requirements across 36 capabilities and add four test-design/traceability requirements, for 37 delta capabilities. Other current requirements receive a retained or test-only disposition, including calibration and existing synthetic suites. The static source inventory also screens all 1,244 versioned test sources and finds existing literal requirement associations for every current capability.

The full approved migration exceeds one engineer-day. The requested single proposal therefore declares eight serial implementation work packages, each scoped to one engineer-day, in design/tasks. They remain one acceptance unit; none may claim the approved scope complete independently. This planning change creates no extra proposal or implementation branch. The existing pipeline remains paused after crab.

## Non-goals

No implementation in this proposal, runtime tests, main-spec sync, archive rewrite, new monster delivery, new global balance/calibration bands, or edits to active monster/exploration proposals or the remaining-monster batch design. Numerical synthetic fixtures and established explicit invariants stay valid. Content relationships remain enforceable even when they constrain an otherwise schema-valid magnitude edit.

## Dependencies and conflicts

No new prerequisite change. Current master already contains shared mechanics and delivered crocodile/sparrow/crab. Existing hare/goat/lynx proposals conflict with the four monster capabilities and shared registry tests; exploration proposals can conflict with documentation/traceability and exploration test files. These are report-only conflicts for later reconciliation, with no edits or automatic queue resumption. See the matrix in design.md.
