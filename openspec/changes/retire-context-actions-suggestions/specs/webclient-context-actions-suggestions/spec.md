## REMOVED Requirements

### Requirement: The context_actions panel carries a suggestions envelope at version 7
**Reason**: The `suggestions` field is removed from both available forms; the panel carries no suggestion state, so no envelope contract remains.
**Migration**: `webclient-context-actions` and `webclient-combat-menu` state the version-9 field sets.

### Requirement: Suggestion cards are a bounded closed exact shape
**Reason**: No card vocabulary reaches the wire.
**Migration**: None.

### Requirement: Exploration suggestions render from an immutable session snapshot
**Reason**: `OptionsSnapshot`, `FrozenCard`, `PresentationContext.options_state`, and the presenter's suggestion section are deleted; there is no snapshot to render from.
**Migration**: None.

### Requirement: The v7 client mirror and parity contract enforce the suggestions shape
**Reason**: The client mirror registers the panel without a `suggestions` field and `web/static/webclient/js/elosern/protocol/panels/suggestions.js` is deleted; the parity contract's suggestion half is removed with it, and its surviving combat-bound check stays in `tests/test_context_actions_parity_contract.py`.
**Migration**: The panel schema-version parity contract (`tests/test_panel_schema_version_parity_contract.py`) covers the new version.
