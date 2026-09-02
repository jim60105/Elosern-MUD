# creation-persona-persistence — Delta Spec

## REMOVED Requirements

### Requirement: The owner can freely update the background after activation
**Reason**: the single-key background service is generalised into the four-field whitelist service `update_persona_field` with `PERSONA_EDITABLE_FIELDS` (`background`, `personality`, `life_story`, `habit`), whose contract lives in the `persona-editing` capability together with its action and command family; keeping a background-only requirement here would double-own the same writer.
**Migration**: `persona-editing::One deterministic service writes the four editable persona fields` fully supersedes it (the `update_background` wrapper preserves every current caller); the existing `world/rules/tests/test_persona_edit.py` scenarios migrate to that requirement's `covers_requirement` IDs in this change.
