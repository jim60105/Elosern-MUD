# Evennia Test Optimization Specification (Delta)

## Purpose

Downgrade fixture-free `EvenniaTest` classes to `EvenniaTestCase` and pin the
new fixture boundary in the contract tests.

## MODIFIED Requirements

### Requirement: Fixture optimization preserves the tested boundary
The project SHALL optimize only measured or inventoried test hot spots. Pure logic SHALL use standard `unittest.TestCase`; tests needing Django or Evennia setup without default game objects SHALL use `EvenniaTestCase` with minimal fixtures; command tests SHALL retain the command-test lifecycle; and tests asserting default world, typeclass persistence, account, session, room, exit, object, or script integration SHALL retain an integration-capable base. A test class that never references the `EvenniaTestMixin` fixtures (any of `char1`, `char2`, `room1`, `room2`, `account`, `session`, `obj1`, `obj2`, `exit`, `script1`) and needs no command lifecycle SHALL inherit `EvenniaTestCase` (or an isolation mixin plus `EvenniaTestCase`), preserving transaction isolation and cache flushing. Fixture conversions MUST preserve substantive assertions and requirement annotations.

#### Scenario: Pure logic avoids default-world creation
- **WHEN** a measured hot test exercises deterministic calculation, parsing, or formatting without persistence behavior
- **THEN** it runs without constructing the default `EvenniaTest` world

#### Scenario: Integration behavior retains real persistence
- **WHEN** a test asserts an Evennia handler, Attribute, typeclass, command lifecycle, session, or database transaction behavior
- **THEN** the optimized test still exercises the real required integration boundary rather than mocking the behavior under assertion

#### Scenario: Shared fixture mutation is isolated
- **WHEN** class-level test data is introduced
- **THEN** isolation, package, order-variation, and full-suite runs demonstrate that one test method cannot affect another method's outcome

## ADDED Requirements

### Requirement: Fixture-free test classes use the lightest base
A test class that, after a dependency review covering its base classes, isolation mixins, the code under test, and any `SESSION_HANDLER` or default-session dependence, never references the `EvenniaTestMixin` fixtures and needs no command lifecycle SHALL inherit `EvenniaTestCase` (or an isolation mixin plus `EvenniaTestCase`) rather than `EvenniaTest`, so per-method setup and teardown cost is not paid for a world the test never uses. The conversion SHALL preserve method bodies, names, substantive assertions, and requirement annotations; a class that fails after conversion SHALL be reverted to its prior base and reported, never repaired by adding fixture usage or weakening assertions. The excluded classes and their exclusion reasons SHALL be recorded with the change for reproducibility, and conversion SHALL be verified per package during the change and by the full suite afterward.

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
