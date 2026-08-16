# Evennia Test Optimization Specification (Delta)

## Purpose

Split the scene-builder and compile test modules into themed modules while
keeping shared base classes importable.

## ADDED Requirements

### Requirement: Scene-builder and compile test modules are split with shared bases kept importable
The `world/quests/tests/test_scene_builder.py` and `world/quests/tests/test_compile.py` modules SHALL be split by class into themed `test_*.py` modules: class bodies, method names, substantive assertions, and requirement annotations SHALL be preserved unchanged. Shared base classes and mixins (`SceneBuilderTestBase`, `SceneBuilderIsolation`, `CompileRegistryIsolation`) SHALL keep a single fixed home — either the original module or a helpers module — and every new module SHALL import them from that home, with no duplicated base code. Module-level payload helpers SHALL also keep a single fixed home — either the original module or a helpers module — so deleting an emptied original module never orphans an import. A top-level contract test SHALL verify that every class from the pre-split inventories appears in exactly one test module of `world/quests/tests`. The original modules SHALL be emptied of moved classes and deleted only when nothing (including a shared base) still lives in them.

#### Scenario: The quests split lands without behavior change
- **WHEN** the scene-builder and compile modules are split into themed modules
- **THEN** the full suite passes with the same discovered test count, every `covers_requirement` annotation stays on its method, and each class from the pre-split inventory appears in exactly one module

#### Scenario: Shared bases keep one fixed import home
- **WHEN** a new module needs `SceneBuilderTestBase`, `SceneBuilderIsolation`, or `CompileRegistryIsolation`
- **THEN** the base or mixin lives in exactly one module (the original module or a helpers module) and every new module imports it from there, so deleting the original file never orphans an import

#### Scenario: Package-level manifest ownership stays complete
- **WHEN** the split creates new test modules under `world.quests`
- **THEN** the ownership contract test still partitions every discovered module exactly once without a manifest edit
