## MODIFIED Requirements

### Requirement: Existing quality gates remain authoritative
The optimized workflow SHALL execute the managed browser suite exactly once across its committed execution jobs and SHALL collect separate coverage data for the non-browser Evennia, managed browser, and top-level entry points. The managed browser suite MAY be distributed across parallel CI jobs by test file as long as each file has exactly one serial execution owner and the per-job coverage and requirement-evidence files are aggregated exactly once. The workflow SHALL preserve shared successful requirement evidence across all required Python entry points, combine the coverage files of every entry point into one aggregate, verify exact coverage roots for `commands`, `server`, `typeclasses`, `web`, and `world`, enforce aggregate branch coverage of at least 80%, and generate and upload coverage XML only from the verified aggregate data. Aggregation MUST fail when an expected entry-point artifact is missing or empty rather than silently lowering the combined total. Test performance improvements MUST NOT come from skipped tests, reduced assertions, removed annotations, disabled gates, or failure suppression.

#### Scenario: Optimized serial workflow proves equivalence
- **WHEN** final verification runs from a clean test database
- **THEN** strict OpenSpec validation, all three disjoint Python suites, execution-evidence verification, coverage-root verification, the aggregate 80% branch gate, Node tests, and Codecov publication retain their required semantics

#### Scenario: Browser coverage is collected without duplicate execution
- **WHEN** the committed quality workflow is inspected and run
- **THEN** `web/tests/browser/` has exactly one serial execution owner per test file across the workflow's browser jobs, the combined browser coverage files are required by aggregation, and the non-browser Evennia labels use `web.webclient` instead of broad `web` discovery

#### Scenario: Parallel CI aggregation preserves the gate
- **WHEN** the quality gate runs the non-browser Evennia profile with parallel workers and the browser suite across sharded jobs
- **THEN** the final aggregation job combines every entry point's coverage files into one report, verifies the coverage roots, enforces the aggregate branch gate, verifies the concatenated requirement evidence, and publishes coverage XML from the combined data only

#### Scenario: Missing artifact fails the aggregation gate
- **WHEN** an entry-point job finishes without uploading its coverage data or evidence file
- **THEN** aggregation fails with a diagnostic naming the missing artifact instead of producing a coverage report from partial data
