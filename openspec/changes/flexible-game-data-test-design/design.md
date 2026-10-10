# Design

## Context

See proposal.md for motivation and scope. Architectural authority is `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`; AGENTS.md defines registry ownership, literal imported bases, no baked multipliers, age bounds, atomic writes and independent fixtures. `docs/development/evennia-testing-guide.md` provides the existing pure/Evennia fixture conventions. This design amends test contracts, not runtime architecture.

The baseline has 311 current capabilities/2,074 requirement headings, 94 classified content-test files and 14 debt paths. Static screening of 1,244 versioned test sources finds existing explicit associations for all capabilities. `scope-inventory.md` gives exhaustive capability/classified-file dispositions; `test-migration.md` grounds concrete retained/replaced assertions in source. Source inspection found numerical approval duplication beyond crocodile/sparrow/crab: lore/stat bands, skills/lineage, equipment/economy, church/affinity, sexual catalogs and world-time/calibration surfaces.

## Goals / Non-Goals

**Goals:** valid authored tuning requires no duplicated expected-data edit; missing references and broken consumer mechanics fail meaningfully; test volume grows by new composition rather than engine-vector cloning; existing real invariants and traceability remain intact.

**Non-goals:** game balance adjustments, new global calibration/balance bands, formula replacement, a new lint engine, compatibility or save migration. Historical archives and all existing active proposals remain immutable to this change. Main-spec delta application is future implementation work, never part of this planning commit.

## Decisions

### 1. Classify each assertion by the property, not whether it calls game code

Use three existing test roles:

1. Generic production integrity validates schema, ownership/identity, references, recipient and hit-dependency topology, bounds and intentional content quality. Production balance magnitudes have one source, the declarations.
2. Shared synthetic mechanism tests have fixed local inputs and independently known outcomes. Literal costs/coefficients/durations are appropriate here. They execute the real engine without deriving expected values from the production helper under test or reproducing its formula in a new helper.
3. Minimal production integration smoke crosses a distinct consumer boundary: declaration to construction, real policy selection to request resolution, payment/buff writer to externally observed state and committed state to reload. Reading a declaration as input can prove wiring across that boundary; it does not prove the calculation itself. No blanket claim is made that shared-oracle assertions cannot fail.

Each migrated assertion names a concrete bug it detects, as specified by the migration matrix. Do not remove valid state observations just because the test uses authored input; do remove copy/forwarding/mock echoes and unsupported reuse claims. Reject relocation of `APPROVED_BALANCE`, approval snapshots or expected-row builders: centralizing the duplicate still requires coordinated edits and verifies agreement, not behavior.

### 2. Preserve intentional invariants, including intentional numeric ones

Stable mechanics include integer copper conversion, bounded ages and pleasure, ordered closed vocabularies, canonical affinity floors/natural cap, irreversible flags, single-writer/atomic ownership, cost-before-effect order, partial transfer on actual loss, routing by DB identity, hit evidence per target, recipient scope, inclusive gates, no multiplier baked into stored bases, rollback and durable reload. Existing cost-tier/band constraints, racial power-gap bounds, zero-sum/directional modifier intent and comparative sexual-content requirements remain enforceable. Named roster sizes and grammar/count limits are not mutable balance values.

Production profile values, costs, coefficient magnitudes, durations, percentage/flat adjustments, stock/prices, configurable edge thresholds, ordinary budgets/gains, density and configured time/recovery values are authored data. Their existing schema/quality constraints still apply. A magnitude edit that violates a retained content-quality invariant is not a benign tuning acceptance case.

The damage-ability eligibility correction reflects current registry behavior and the existing skill-registry contract: `usable_out_of_combat=True` for every damage ability, including crocodile. It does not authorize damage without a battlefield. No game data changes are requested.

Some legacy numerical scenarios now describe scoped synthetic fixtures, including fixed trait transformations and counter gates. Keep their mechanism assertions and named content topology; do not treat the example input as production approval. Requirement headings are retained to preserve existing IDs, even where a legacy title mentions literal approval or 5% recovery; their revised body is authoritative. Do not rename them opportunistically.

### 3. Reuse the existing shared suites and retain three compositions

Shared hit dependencies, gauge transfer, effect audiences, potency, progression, transactional item use and clock/settlement suites own the broad engine vectors. Add only a missing independent property, such as a real second synthetic species execution or fault injection after practice claim acquisition. Existing synthetic fixtures are not rewritten merely to change their numbers.

The delivered drain, enemy hit-rider and hit-independent self-guard compositions retain representative real session-selection/execution smoke. Both variants of each delivered species receive generic identity/profile/kit/reference checks; do not multiply the engine battery by every variant. Avoid a numerical per-species target for test count. Proportionality is demonstrated by removal of duplicate vectors with justified shared coverage, not an arbitrary line budget.

Payment assertions observe resource state before/after resolution. Recipient assertions observe target and untouched actor/ally controls. Buff lifecycle assertions observe absence on miss, actual refresh of an aged instance, expiry across clock advances and durable source identity after reload. Rollback faults occur after a relevant write or acquired claim, so a failure before any mutation cannot falsely stand in for rollback coverage. Persistence reads a reloaded object, not only a cached dictionary.

### 4. Keep classification and traceability bookkeeping honest

Preserve the existing AST/data gate and its shrink-only debt policy. Its contract tag is classification, not a numerical approval exemption or semantic proof. Keep generic checks in existing classified files where possible. Align first-line reasons with `tools/test_data_freeze.json` and the seed's corresponding contract metadata; `tools/test_data_lint.py` checks seed-reason agreement and rejects new contract paths outside seeded classification. Retiring a wholly synthetic file's classification retires the matching seed contract metadata, not seed debt. Do not add debt, expand allowlists or re-seed.

`tools.spec_traceability` derives canonical IDs from current headings and only records successful decorated test execution. Preserve every existing current association that remains valid, map migrations to meaningful assertions and add coverage for the four new requirements. No baseline waiver, bulk decoration of a weak smoke or replacement numerical checker. Aggregate coverage stays a floor, not a reason to manufacture redundant tests.

Future authoring guidance in AGENTS.md, the testing guide and the relevant developer balance/content guidance must explain the three roles, defect rationale and the rule that balance tuning does not update duplicate expectations. Update affected current deltas through the ordinary implementation workflow; do not edit archived proposal evidence.

## Migration Plan: one proposal, eight serial work packages

The full approved inventory exceeds one engineer-day. This is an explicit size exception to the normal one-day change convention, required to preserve the user-requested single coherent proposal. Implementation is serially split into these bounded packages; all are required before completion. No additional proposal or partial delivery is created now.

| Package | Depends on | Concrete deliverable | Size boundary |
| --- | --- | --- | --- |
| A: shared oracles and bookkeeping | none | Reuse shared synthetic fixtures, remove identified self-oracles, fill actual second-execution/post-write rollback gaps and establish per-assertion rationale/requirement mapping. | One engineer-day; only the existing shared suite locations in the migration matrix. |
| B: delivered monster contracts | A | Remove `APPROVED_BALANCE` and literal registry/profile pins; generic checks for all delivered/deferred identities; replace three long suites with representative real compositions; apply the four monster capability deltas. | One engineer-day; no new species or changes to active monster plans. |
| C1: lore and skill contracts | B | Migrate race/subrace/preset/title data and skill/lineage assertions, preserving independent trait and prerequisite mechanics. | One engineer-day scope; no new registries or runtime transformations. |
| C2: equipment and economy contracts | C1 | Migrate mutable equipment/price/stock/host tables with shared synthetic commerce and trait fixtures. | One engineer-day scope; retain existing slot/budget/currency constraints. |
| C3: church and affinity contracts | C2 | Migrate recorded church finals, passive adjustments and configurable affinity gains with synthetic atomicity and ordering fixtures. | One engineer-day scope; preserve endpoints, stage vocabulary and all authority/privacy gates. |
| C4: sexual catalog and state contracts | C3 | Migrate per-act tuning and state-band examples, retaining exact counter/event topology and explicit comparative quality. | One engineer-day scope; no effect or content roster redesign. |
| C5: clock and calibration contracts | C4 | Migrate time/density/recovery tuning and production calibration pins, preserving causal and bounded execution evidence. | One engineer-day scope; no new calibration bands or geometry changes. |
| D: coverage, guidance and acceptance evidence | C5 | Close every current requirement association, classification metadata and docs; run scoped benign/broken perturbations and final relevant/full gates. | One engineer-day scope; no permanent exhaustive mutation suite or per-monster regression clones. |

No package may narrow the inventory or mark the proposal complete independently. If implementation reveals that a package is larger, retain the full acceptance unit and explicitly replan its serial steps; do not silently exclude a capability. Normal rollback of an implementation package is revert of its scoped test/spec/docs commit, with no runtime/save migration. Never revert unrelated concurrent edits.

## Risks / Trade-offs

- Removing a duplicated number can accidentally remove a real invariant. Mitigation: preserve each named structural/mechanical/quality assertion and use its explicit defect rationale; fixed synthetic examples stay.
- A real-code smoke can still be an echo. Mitigation: observe independently committed recipient/control/resource/clock/persistence state; keep calculation correctness in independent fixtures.
- Declared-value comparisons can share an upstream defect. Mitigation: bound the claim to integration wiring and require independent mechanism evidence, not a blanket rejection of every such comparison.
- Content-quality relationships can legitimately fail after tuning. Mitigation: acceptance chooses edits satisfying those established constraints; add no global replacement bands.
- Seed contract reasons and ledger tags can drift. Mitigation: update all three together and preserve seeded debt paths.
- Legacy lore magic-order prose states a stronger all-beast-bands-below-human-floor relation than its overlapping bands/current endpoint checks support. This proposal neither tightens tests to that impossible relation nor changes magic balancing. Preserve existing explicit power-gap/band shape checks and report this inherited discrepancy rather than introduce a new restriction.
- The overall inventory is broad. Mitigation: C1 through C5 split known families into serial one-day scopes; nothing remains a generic research task, and scope cannot be reduced without explicit approval.

## Report-only dependencies / conflict matrix

| Existing proposal | Dependency status | Possible overlapping code/spec surface | Handling now |
| --- | --- | --- | --- |
| `ridge-burrow-hare-resource-skill` | No dependency edit; future apply should reconcile after this design | Four monster capabilities, skill registry/monster content tests, shared payment/hit coverage | Untouched; supervisor decides ordering; pipeline paused after crab. |
| `rock-echo-goat-resource-skill` | Same | Same monster/registry/shared suites | Untouched; no task/design edits. |
| `fog-mane-lynx-resource-skill` | Same | Same monster/registry/shared suites | Untouched; no remaining-monster batch edits. |
| `exploration-room-actions` | No runtime prerequisite | Requirement associations, command/clock integration and testing documentation | Report-only; do not alter exploration scope or behavior. |
| `exploration-exit-compass` | No runtime prerequisite | Shared exploration test helpers/docs/traceability, not a new compass contract | Report-only; preserve its artifacts. |
| `exploration-presence-rail` | No runtime prerequisite | Shared exploration presentation fixtures/docs/traceability, not presence behavior | Report-only; preserve its artifacts. |

This is one change, so no new inter-change `depends-on:` batch edges are introduced. The package A→B→C1→C2→C3→C4→C5→D dependency is internal, not a rewrite of the existing supervisor queue. Existing archived crocodile, sparrow and crab artifacts remain historical evidence.
