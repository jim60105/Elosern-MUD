## Purpose

Measured, isolated, and coverage-preserving execution profiles for the Evennia test suite.
## Requirements
### Requirement: Optimization is based on reproducible measurements
The project SHALL capture a pre- and post-change Evennia test performance report comparing a recorded baseline commit SHA to an optimized revision identity on the same reference machine under identical Python/Evennia versions, dependency lock, target ownership, migrations, fixtures, warm-up protocol, and coverage state. Acceptance SHALL require at least a 20% median wall-time reduction for the full non-browser Evennia profile and SHALL NOT use hardware-independent seconds thresholds.

#### Scenario: Baseline identifies measured hot spots
- **WHEN** the profiling profile completes its baseline runs
- **THEN** the report contains sufficient command, environment, timing, count, and slow-test data to select fixture optimizations without guessing

#### Scenario: Performance claim uses comparable runs
- **WHEN** the implementation claims that the full profile is faster
- **THEN** the claim compares serial medians for the recorded baseline and optimized revision identities under the same machine, dependency environment, target ownership, migrations, fixtures, warm-up protocol, and coverage state, discloses any database storage or reuse difference, and demonstrates at least a 20% reduction

#### Scenario: Provisional optimized identity is superseded
- **WHEN** the optimized revision has no commit yet
- **THEN** the optimized identity names the worktree branch, base SHA, and dirty state, and its eventual commit SHA supersedes that provisional identity

#### Scenario: Measured runs and report fields are recorded
- **WHEN** either side of the performance comparison is measured
- **THEN** it uses a warm-up followed by at least three measured serial runs
- **AND** the report lists raw wall times, median wall time, test count, result status, database setup timing, storage and reuse state, coverage state, environment versions, and the slowest tests

### Requirement: Test-only settings are explicit and isolated
The project SHALL provide an explicit Evennia test settings module that uses Django's test-only fast password hasher and sets `DATABASES["default"]["TEST"]["NAME"]` to a unique file-backed SQLite path compatible with `--keepdb`, distinct from both `:memory:` and the developer database, and MUST confine retained test state to its named test database.

#### Scenario: Repeated local run reuses only test state
- **WHEN** a developer runs a supported Evennia profile twice with the test settings and `--keepdb`
- **THEN** the second run reuses the dedicated test database without reading or writing the developer database

#### Scenario: Production cannot select weak hashing
- **WHEN** the normal server settings or browser-test settings are loaded for their intended runtime
- **THEN** neither settings profile selects the test-only fast password hasher or retained local test database

#### Scenario: Clean database remains supported
- **WHEN** the suite runs after the dedicated test database is absent or retention is disabled
- **THEN** Django creates a fresh test database and the suite passes with the same discovered tests and outcomes

#### Scenario: Settings loading is an explicit opt-in
- **WHEN** the test settings module load is attempted without an explicit environment opt-in or outside the pinned launcher's exact test-command context
- **THEN** the load is rejected with a documented configuration error for direct or non-test server use

#### Scenario: Database storage differences and production isolation are disclosed
- **WHEN** database storage or cross-process reuse differs between compared performance runs
- **THEN** the difference is an explicit optimization variable and MUST be disclosed
- **AND** the test settings MUST NOT change production or browser-test password hashing or persistence

### Requirement: Supported execution profiles preserve suite ownership
The project SHALL document uv-locked focused, full local, profiling, canonical quality-gate, and managed browser profiles, and contract verification MUST prove every current Python test path belongs to exactly one Python entry point.

#### Scenario: Developer runs one affected test
- **WHEN** a developer follows the focused profile with a dotted test label
- **THEN** the command uses the locked environment, explicit test settings, retained test database, and no unrelated package label

#### Scenario: Final verification remains complete
- **WHEN** the documented final verification workflow is followed
- **THEN** all package-local, top-level, Node, browser, OpenSpec, traceability, coverage-root, aggregate coverage, and Codecov gates remain represented without failure suppression

#### Scenario: Retained database rebuild is documented
- **WHEN** migrations change or retained-state failures occur
- **THEN** the documentation directs removal or rebuilding of only the dedicated test database before rerunning the clean profile

#### Scenario: Focused profiles are development feedback
- **WHEN** a focused profile is documented or used
- **THEN** it accepts dotted module, class, or method labels and is described as development feedback rather than final verification

#### Scenario: Suite ownership is partitioned across entry points
- **WHEN** the test entry points are documented
- **THEN** the non-browser Evennia profile owns package-local tests under `commands`, `server`, `typeclasses`, `world`, and `web.webclient`, the top-level regression command owns `tests/`, and the managed browser command solely owns `web/tests/browser/`

### Requirement: Fixture optimization preserves the tested boundary
The project SHALL optimize only measured or inventoried test hot spots. Pure logic SHALL use standard `unittest.TestCase`; tests needing Django or Evennia setup without default game objects SHALL use `EvenniaTestCase` with minimal fixtures; command tests SHALL retain the command-test lifecycle; and tests asserting default world, typeclass persistence, account, session, room, exit, object, or script integration SHALL retain an integration-capable base.

#### Scenario: Pure logic avoids default-world creation
- **WHEN** a measured hot test exercises deterministic calculation, parsing, or formatting without persistence behavior
- **THEN** it runs without constructing the default `EvenniaTest` world

#### Scenario: Integration behavior retains real persistence
- **WHEN** a test asserts an Evennia handler, Attribute, typeclass, command lifecycle, session, or database transaction behavior
- **THEN** the optimized test still exercises the real required integration boundary rather than mocking the behavior under assertion

#### Scenario: Shared fixture mutation is isolated
- **WHEN** class-level test data is introduced
- **THEN** isolation, package, order-variation, and full-suite runs demonstrate that one test method cannot affect another method's outcome

#### Scenario: Fixture-free classes inherit the light base
- **WHEN** a test class never references the `EvenniaTestMixin` fixtures (any of `char1`, `char2`, `room1`, `room2`, `account`, `session`, `obj1`, `obj2`, `exit`, `script1`) and needs no command lifecycle
- **THEN** it inherits `EvenniaTestCase` (or an isolation mixin plus `EvenniaTestCase`), preserving transaction isolation and cache flushing

#### Scenario: Conversions preserve assertions and annotations
- **WHEN** a fixture-base conversion is applied to a test
- **THEN** its substantive assertions and requirement annotations are preserved

### Requirement: Tests restore process-global registry state
Any test that mutates a process-global registry shared across the test process SHALL snapshot the registry's contents before mutating and restore them in teardown, preserving whatever the process held before the test rather than clearing state other tests rely on. The restoration MUST be registered before the mutation (for example via `addCleanup`) so a failing setup cannot leak registry state.

#### Scenario: Leaked offer cannot break a later test
- **WHEN** a test runs `sync_guild_economy()` (or registers catalog offers) and a later test in the same process registers a differently-shaped offer under the same identity
- **THEN** the later registration succeeds because the earlier test restored the registry to its pre-test contents

#### Scenario: Cleared registry is restored to prior contents
- **WHEN** a test clears `QUEST_DEFINITION_REGISTRY` or `GUILD_OFFER_REGISTRY` during its body
- **THEN** the registry is restored to exactly the entries it held before the test, so later tests relying on those entries (for example an affinity-rulebook load resolving `introductory_hunt`) continue to pass

#### Scenario: Failing setup cannot leak registry state
- **WHEN** a test's setup mutates a covered registry and then raises before its teardown would run
- **THEN** the registry is still restored to its pre-test contents because the restoration was registered before the mutation

#### Scenario: Order variation cannot change outcomes
- **WHEN** the full non-browser Evennia suite runs in serial, parallel, shuffled, and reversed order
- **THEN** every test passes in every ordering with the same discovered test count

#### Scenario: Contract covers the named registries
- **WHEN** a test mutates a registry covered by this contract
- **THEN** it applies to at least `QUEST_DEFINITION_REGISTRY`, `GUILD_OFFER_REGISTRY`, and `SCENE_REQUIREMENT_REGISTRY`

#### Scenario: Rulebook-driven reads register their own entries
- **WHEN** a test reads rulebook-driven state requiring registry entries (for example an affinity-rulebook load that resolves quest keys)
- **THEN** it registers the required catalog definitions in its own setup instead of depending on an earlier test to have registered them

#### Scenario: Sync entry points follow the same discipline
- **WHEN** a test uses a synchronization entry point that registers offers or definitions (such as `sync_guild_economy()`)
- **THEN** that use is paired with the same snapshot/restore discipline

### Requirement: Parallel execution is gated by equivalence
Parallel Evennia execution SHALL be adopted for the non-browser Evennia profile only after repeated runs demonstrate identical discovered test counts and outcomes, complete parseable requirement evidence, isolated databases and shared resources, equivalent combined branch coverage and source roots, actionable failures, and at least a 20% median wall-time reduction.

#### Scenario: Unsafe parallel run is rejected
- **WHEN** parallel evaluation loses coverage or evidence, collides on a file, cache, process, database, or port, produces a flake, or improves median wall time by less than 20%
- **THEN** serial execution remains canonical, parallel is not adopted in the workflow, and the failed adoption condition is recorded

#### Scenario: Parallel mode qualifies for canonical use
- **WHEN** repeated clean and retained-database parallel runs satisfy every correctness, artifact-equivalence, isolation, diagnostic, and speed condition
- **THEN** the profile is documented and adopted for the proven non-browser scope, including the committed quality-gate workflow

#### Scenario: Subprocess coverage is captured and combined
- **WHEN** the adopted parallel profile runs under the quality gate with coverage
- **THEN** every worker's coverage data is written to its own file, combined with the parent data, and the combined report equals the serial profile's source roots and statement/branch totals

#### Scenario: Adoption evidence enables the workflow and is recorded
- **WHEN** the equivalence evidence exists
- **THEN** the quality-gate workflow MAY execute the non-browser Evennia profile with the documented parallel worker count and subprocess-aware coverage instrumentation
- **AND** the performance report SHALL record the adoption evidence

#### Scenario: Managed browser stays out of generic parallel profiles
- **WHEN** a generic parallel profile is defined
- **THEN** managed browser acceptance MUST NOT be included in it

#### Scenario: Serial remains the canonical handoff evidence
- **WHEN** final handoff evidence is produced
- **THEN** serial execution SHALL remain the canonical final-handoff evidence profile

### Requirement: Existing quality gates remain authoritative
The optimized workflow SHALL execute the managed browser suite exactly once across its committed execution jobs and SHALL collect separate coverage data for the non-browser Evennia, managed browser, and top-level entry points. Test performance improvements MUST NOT come from skipped tests, reduced assertions, removed annotations, disabled gates, or failure suppression.

#### Scenario: Optimized serial workflow proves equivalence
- **WHEN** final verification runs from a clean test database
- **THEN** strict OpenSpec validation, all three disjoint Python suites, execution-evidence verification, coverage-root verification, the aggregate 80% branch gate, Node tests, and Codecov publication retain their required semantics

#### Scenario: Browser coverage is collected without duplicate execution
- **WHEN** the committed quality workflow is inspected and run
- **THEN** `web/tests/browser/` has exactly one serial execution owner per test method across the workflow's browser jobs, the combined browser coverage files are required by aggregation, and the non-browser Evennia labels use `web.webclient` instead of broad `web` discovery

#### Scenario: Browser shard runs two isolated processes
- **WHEN** a browser shard job runs two test processes from two separate checkouts
- **THEN** each process owns its own serial label list, coverage file, and evidence file; the per-process evidence files are concatenated per shard; and the per-shard artifacts satisfy the aggregation completeness checks exactly once

#### Scenario: Non-browser suite is machine-sharded with per-module ownership
- **WHEN** the quality gate runs the non-browser Evennia suite across multiple machine-sharded jobs driven by a committed manifest
- **THEN** every non-browser test module under `commands`, `server`, `typeclasses`, `world`, and `web.webclient` belongs to exactly one shard, every shard runs its labels with the documented parallel worker profile and subprocess-aware coverage, and each shard's coverage sidecars and evidence file are required by aggregation exactly once

#### Scenario: Parallel CI aggregation preserves the gate
- **WHEN** the quality gate runs the non-browser Evennia profile with parallel workers and the browser suite across sharded jobs
- **THEN** the final aggregation job combines every entry point's coverage files into one report, verifies the coverage roots, enforces the aggregate branch gate, verifies the concatenated requirement evidence, and publishes coverage XML from the combined data only

#### Scenario: Missing artifact fails the aggregation gate
- **WHEN** an entry-point job finishes without uploading its coverage data or evidence file
- **THEN** aggregation fails with a diagnostic naming the missing artifact instead of producing a coverage report from partial data

#### Scenario: Empty artifacts also fail aggregation
- **WHEN** an expected entry-point coverage or evidence artifact is present but empty
- **THEN** aggregation MUST fail rather than silently lowering the combined total

#### Scenario: Distributed suites keep one serial owner
- **WHEN** the managed browser suite is distributed across parallel CI jobs by test file, class, or method label
- **THEN** each test method has exactly one serial execution owner
- **AND** the non-browser Evennia suite MAY likewise be distributed across parallel CI jobs by manifest-owned dotted labels (package or module) as long as each test module under `commands`, `server`, `typeclasses`, `world`, and `web.webclient` has exactly one serial execution owner and every shard's coverage and requirement-evidence files are aggregated exactly once

#### Scenario: Shared requirement evidence is preserved
- **WHEN** the workflow runs across all required Python entry points
- **THEN** it preserves shared successful requirement evidence across all of them

#### Scenario: Exact coverage roots gate the aggregate and the XML
- **WHEN** coverage from every entry point is combined into one aggregate
- **THEN** the aggregate verifies exact coverage roots for `commands`, `server`, `typeclasses`, `web`, and `world`
- **AND** enforces aggregate branch coverage of at least 80%
- **AND** coverage XML is generated and uploaded only from the verified aggregate data

### Requirement: Machine shards preserve exact per-module test ownership
The committed non-browser Evennia shard manifest SHALL partition every discoverable non-browser test module exactly once: a top-level contract test SHALL enumerate all `test*.py` modules under `commands`, `server`, `typeclasses`, `world`, and `web.webclient`, resolve every manifest label to its module(s) without importing them, and assert that the discovered set and the labeled set are identical with no overlap between shards.

#### Scenario: Every non-browser test module is owned exactly once
- **WHEN** the evennia shard manifest is inspected by the ownership contract test
- **THEN** each discovered test module appears in exactly one shard's labels, labels resolve without importing game code, indices are unique and sorted, and no module is orphaned or duplicated

#### Scenario: Manifest labels resolve to real test modules
- **WHEN** a manifest label does not correspond to an existing test module file or a package directory containing test modules
- **THEN** the ownership contract test fails with a diagnostic naming the unresolvable label

#### Scenario: Empty or malformed manifest cannot skip the gate
- **WHEN** the committed evennia manifest declares no shards, a non-sorted or duplicate index, or a shard without non-empty string labels
- **THEN** the preflight job fails before any execution job is dispatched, so the sharded suite and the aggregation gate always run when the workflow runs

#### Scenario: Shard balance is observable and rebalancable
- **WHEN** a CI run reports one evennia shard dominating the others by a wide margin
- **THEN** rebalancing is a manifest edit followed by the contract tests, and the measured per-shard durations are recorded in the performance report

#### Scenario: Labels name modules or walkable packages
- **WHEN** a manifest label is resolved
- **THEN** it names either a module file directly or a package directory to walk recursively

#### Scenario: Manifest shape is constrained
- **WHEN** the manifest is declared
- **THEN** shard indices are unique and sorted
- **AND** every shard contains at least one label, every label resolves to at least one test module, and the manifest declares at least one shard

#### Scenario: Preflight validates the manifest before the matrix
- **WHEN** the workflow computes the execution matrix
- **THEN** the preflight job validates these manifest properties first, so a syntactically valid but empty or malformed manifest fails the workflow rather than skipping every shard job and the aggregation gate

### Requirement: Browser method labels preserve exact ownership
The committed browser shard manifest SHALL partition every test method of every `test_*.py` file under `web/tests/browser/` exactly once across its process lists: a top-level contract test SHALL parse each browser test file with `ast` without importing it, collect every `test_*` method per class, resolve each manifest label (module, class, or method) to its (file, class, method) set, and assert that the resolved set equals the discovered set with no overlap.

#### Scenario: Every browser test method is owned exactly once
- **WHEN** the browser shard manifest is inspected by the method-level ownership contract test
- **THEN** each discovered test method appears in exactly one process list, labels resolve without importing test modules, indices are unique and sorted, and no method is orphaned or duplicated

#### Scenario: Unresolvable browser label fails the contract
- **WHEN** a manifest label does not correspond to an existing browser test module, class, or method
- **THEN** the ownership contract test fails with a diagnostic naming the unresolvable label

#### Scenario: Two isolated processes per shard stay serial per process
- **WHEN** a browser shard's two process lists run on the same runner from separate checkouts
- **THEN** each process executes its own labels serially with its own coverage and evidence files, and the per-shard evidence is the concatenation of both processes' files

#### Scenario: Shard shape is constrained
- **WHEN** the browser manifest is declared
- **THEN** shard indices are unique and sorted
- **AND** every shard contains exactly two process lists, each with at least one label, and every label resolves to at least one test method

### Requirement: Registry-content assertions use the registry's key domain
Any test asserting membership or contents of a process-global registry covered
by the isolation contract SHALL use that registry's documented key domain, not
an incidental attribute of the entities it indexes. The skip-safety battlefield
registry SHALL be asserted with participant dbrefs: a test that checks
`world.rules.skip_safety._BATTLEFIELDS` SHALL assert `str(entity.pk)` keys,
never `str(entity.key)` display keys, matching the dbref indexing the registry
implements.

#### Scenario: Restore path registers each participant by dbref
- **WHEN** a persisted combat session is restored and the test verifies the
  skip-safety registration survived
- **THEN** the test asserts `str(actor.pk)` and `str(monster.pk)` are present in
  `_BATTLEFIELDS` after restoration, never the participants' display keys

#### Scenario: Display-key assertion fails under the dbref-keyed registry
- **WHEN** a test asserts that a participant's display key is a key of
  `_BATTLEFIELDS` whose entries are indexed by participant dbref
- **THEN** the assertion fails, proving the display-key form is not the
  registry's key domain

### Requirement: AI test modules are split into themed helpers-backed modules
The `world/ai/tests/test_scenario_director.py` and `world/ai/tests/test_npc_dialogue.py` modules SHALL be split by class into themed `test_*.py` modules: class bodies, method names, substantive assertions, and requirement annotations SHALL be preserved unchanged. The original modules SHALL be emptied of moved classes and deleted when nothing remains.

#### Scenario: The AI split lands without behavior change
- **WHEN** the scenario-director and npc-dialogue modules are split into themed modules
- **THEN** the full suite passes with the same discovered test count, every `covers_requirement` annotation stays on its method, and each class from the pre-split inventory appears in exactly one module

#### Scenario: Shared helpers centralize without duplication
- **WHEN** a split's module-level helpers or support classes are used by classes in multiple new modules
- **THEN** the helpers move once into a dedicated helpers module that the new modules import, with no duplicated code and no import cycles

#### Scenario: The offline-test-rule guard still scans all test sources
- **WHEN** the scenario-director offline-test-rule test can no longer read its original fixed module path
- **THEN** it scans the split scenario-director test modules (for example by globbing the package's `test_*.py` files) and still rejects live-client constructors and socket imports

#### Scenario: Package-level manifest ownership stays complete
- **WHEN** the split creates new test modules under `world.ai`
- **THEN** the ownership contract test still partitions every discovered module exactly once without a manifest edit

#### Scenario: Named helpers move once into dedicated modules
- **WHEN** module-level helpers and support classes used by moved classes (including `_raw`, `_reset_all`, `await_result`, `_item`, `_location`, `_stage`, `_blueprint`, `_payload`, `_context`, `_instance_payload`, `_npc_context`, `_player_context`, `_memory`, `_reply_text`, `_HeldDialogueClient`) are relocated
- **THEN** they move once into dedicated `_director_helpers.py` / `_dialogue_helpers.py` modules that the new modules import, with no duplicated helper code and no import cycles

#### Scenario: Fixed-path source guard scans the split modules
- **WHEN** a test module guards the scenario-director test sources by reading a fixed module path
- **THEN** it is updated to scan the split modules instead

#### Scenario: Inventory contract verifies one home per class
- **WHEN** the AI split is complete
- **THEN** a top-level contract test verifies that every class from the pre-split inventories appears in exactly one test module of `world/ai/tests`

### Requirement: Scene-builder and compile test modules are split with shared bases kept importable
The `world/quests/tests/test_scene_builder.py` and `world/quests/tests/test_compile.py` modules SHALL be split by class into themed `test_*.py` modules: class bodies, method names, substantive assertions, and requirement annotations SHALL be preserved unchanged. The original modules SHALL be emptied of moved classes and deleted only when nothing (including a shared base) still lives in them.

#### Scenario: The quests split lands without behavior change
- **WHEN** the scene-builder and compile modules are split into themed modules
- **THEN** the full suite passes with the same discovered test count, every `covers_requirement` annotation stays on its method, and each class from the pre-split inventory appears in exactly one module

#### Scenario: Shared bases keep one fixed import home
- **WHEN** a new module needs `SceneBuilderTestBase`, `SceneBuilderIsolation`, or `CompileRegistryIsolation`
- **THEN** the base or mixin lives in exactly one module (the original module or a helpers module) and every new module imports it from there, so deleting the original file never orphans an import

#### Scenario: Package-level manifest ownership stays complete
- **WHEN** the split creates new test modules under `world.quests`
- **THEN** the ownership contract test still partitions every discovered module exactly once without a manifest edit

#### Scenario: Module-level payload helpers keep one fixed home
- **WHEN** module-level payload helpers are needed after the quests split
- **THEN** they keep a single fixed home — either the original module or a helpers module — so deleting an emptied original module never orphans an import

#### Scenario: Quests inventory contract verifies one home per class
- **WHEN** the quests split is complete
- **THEN** a top-level contract test verifies that every class from the pre-split inventories appears in exactly one test module of `world/quests/tests`

### Requirement: Fixture-free test classes use the lightest base
A test class that, after a dependency review covering its base classes, isolation mixins, the code under test, and any `SESSION_HANDLER` or default-session dependence, never references the `EvenniaTestMixin` fixtures and needs no command lifecycle SHALL inherit `EvenniaTestCase` (or an isolation mixin plus `EvenniaTestCase`) rather than `EvenniaTest`, so per-method setup and teardown cost is not paid for a world the test never uses.

#### Scenario: Stateless-entity tests skip the default world
- **WHEN** a reviewed test class creates its own entities (`create_object`) and never touches the mixin fixtures, its bases, or session-dependent code
- **THEN** its base is `EvenniaTestCase` (or an isolation mixin plus `EvenniaTestCase`) and the full suite passes with the same discovered test count

#### Scenario: A failing conversion is reverted, not patched
- **WHEN** a downgraded class fails under `EvenniaTestCase`
- **THEN** the class is reverted to `EvenniaTest`, the failure is reported, and no test is weakened or given fake fixtures to make the downgrade stick

#### Scenario: Exclusions are recorded and reproducible
- **WHEN** a candidate class is excluded from the downgrade (contract-pinned, mixin-dependent, session-dependent, or otherwise)
- **THEN** the class and its exclusion reason are recorded with the change, and a re-run of the conversion can reproduce the same candidate and exclusion sets

#### Scenario: Contract pins the new boundary
- **WHEN** the fixture-boundary contract test runs
- **THEN** a representative sample of the newly downgraded classes is asserted to inherit exactly `EvenniaTestCase` (plus any isolation mixin), and the previously pinned classes keep their documented bases

#### Scenario: Conversions preserve content
- **WHEN** a test class is converted to the lightest base
- **THEN** its method bodies, names, substantive assertions, and requirement annotations are preserved

#### Scenario: Conversion is verified per package then by the full suite
- **WHEN** the fixture-free conversion proceeds
- **THEN** it is verified per package during the change and by the full suite afterward

### Requirement: Combat-session and skill-registry test modules are split into themed modules
The `world/rules/tests/test_combat_session.py` and `world/skills/tests/test_registry.py` modules SHALL be split by class into themed `test_*.py` modules: class bodies, method names, substantive assertions, and requirement annotations SHALL be preserved unchanged. The original modules SHALL be emptied of moved classes and deleted when nothing remains.

#### Scenario: The split lands without behavior change
- **WHEN** the combat-session and skill-registry modules are split into themed modules
- **THEN** the full suite passes with the same discovered test count, every `covers_requirement` annotation stays on its method, and each class from the pre-split inventory appears in exactly one module

#### Scenario: Pinned class paths move with the split
- **WHEN** a contract test pins `CombatSessionRecordTests` or `CombatSessionIdTests` by the old module path
- **THEN** the contract test is updated to the new module path with the same class-to-base assertions

#### Scenario: Shard manifest ownership stays complete
- **WHEN** the split creates new test modules under `world.rules`
- **THEN** the evennia shard manifest replaces the removed module label with the new module labels and the ownership contract test still partitions every discovered module exactly once

#### Scenario: Helpers move to their owning module
- **WHEN** module-level helpers are used by moved classes
- **THEN** they move to a helpers module or the module that owns them

#### Scenario: Base classes and mixins stay in place
- **WHEN** moved classes rely on base classes or mixins
- **THEN** those bases and mixins stay where they are and are imported by the new modules

#### Scenario: Inventory contract verifies one home per class
- **WHEN** the combat-session and skill-registry split is complete
- **THEN** a top-level contract test verifies that every class from the pre-split inventories appears in exactly one test module of the owning package

#### Scenario: Pinned paths and shard manifest update together
- **WHEN** a class moves to a new module
- **THEN** any contract test pinning that class's file path and the evennia shard manifest are updated in the same change
