# Evennia Test Optimization Specification (Delta)

## Purpose

Split the combat-session and skill-registry test modules into themed modules
so specific test cases run individually during development.

## ADDED Requirements

### Requirement: Combat-session and skill-registry test modules are split into themed modules
The `world/rules/tests/test_combat_session.py` and `world/skills/tests/test_registry.py` modules SHALL be split by class into themed `test_*.py` modules: class bodies, method names, substantive assertions, and requirement annotations SHALL be preserved unchanged; module-level helpers used by moved classes SHALL move to a helpers module or the module that owns them; base classes and mixins SHALL stay where they are and be imported by the new modules. The original modules SHALL be emptied of moved classes and deleted when nothing remains. A top-level contract test SHALL verify that every class from the pre-split inventories appears in exactly one test module of the owning package. Any contract test pinning a moved class's file path and the evennia shard manifest SHALL be updated in the same change.

#### Scenario: The split lands without behavior change
- **WHEN** the combat-session and skill-registry modules are split into themed modules
- **THEN** the full suite passes with the same discovered test count, every `covers_requirement` annotation stays on its method, and each class from the pre-split inventory appears in exactly one module

#### Scenario: Pinned class paths move with the split
- **WHEN** a contract test pins `CombatSessionRecordTests` or `CombatSessionIdTests` by the old module path
- **THEN** the contract test is updated to the new module path with the same class-to-base assertions

#### Scenario: Shard manifest ownership stays complete
- **WHEN** the split creates new test modules under `world.rules`
- **THEN** the evennia shard manifest replaces the removed module label with the new module labels and the ownership contract test still partitions every discovered module exactly once
