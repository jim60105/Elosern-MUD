# Evennia Test Optimization Specification (Delta)

## Purpose

Split the AI test modules into themed modules backed by dedicated helpers
modules.

## ADDED Requirements

### Requirement: AI test modules are split into themed helpers-backed modules
The `world/ai/tests/test_scenario_director.py` and `world/ai/tests/test_npc_dialogue.py` modules SHALL be split by class into themed `test_*.py` modules: class bodies, method names, substantive assertions, and requirement annotations SHALL be preserved unchanged. Module-level helpers and support classes used by moved classes (including `_raw`, `_reset_all`, `await_result`, `_item`, `_location`, `_stage`, `_blueprint`, `_payload`, `_context`, `_instance_payload`, `_npc_context`, `_player_context`, `_memory`, `_reply_text`, `_HeldDialogueClient`) SHALL move once into dedicated `_director_helpers.py` / `_dialogue_helpers.py` modules that the new modules import, with no duplicated helper code and no import cycles. A test module that guards the scenario-director test sources by reading a fixed module path SHALL be updated to scan the split modules instead. A top-level contract test SHALL verify that every class from the pre-split inventories appears in exactly one test module of `world/ai/tests`. The original modules SHALL be emptied of moved classes and deleted when nothing remains.

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
