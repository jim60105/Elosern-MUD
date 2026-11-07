## REMOVED Requirements

### Requirement: world/ai/action_options.py defines the frozen one-wire-shape card vocabulary
**Reason**: `OptionSet` and `SuggestionCard` are the retired surface's vocabulary; the module is deleted with the client card renderer.
**Migration**: None.

### Requirement: The schema defines exact caps and a status-dependent card-count contract
**Reason**: The card-count, label, hint, params, cache-entry, and memo bounds exist only for the retired cards.
**Migration**: None.

### Requirement: The validation ladder runs 12 fixed stages with one named rejection code each
**Reason**: The 12-stage ladder validated model card output; there is no model card output.
**Migration**: None.

### Requirement: Stage 9 enforces canonical replacement against the affordance vocabulary
**Reason**: Canonical replacement served the retired cards' `known_action` params; the affordance vocabulary itself survives unchanged under `exploration-affordances`.
**Migration**: None.

### Requirement: Leak gates apply to model-visible text only and expose no hidden values
**Reason**: The leak, placeholder, and digit gates guarded model-visible card text; no such text reaches a surface.
**Migration**: None.

### Requirement: Enrichment injects caller-side fields before validation
**Reason**: Enrichment produced the retired wire payload; nothing consumes it.
**Migration**: None.

### Requirement: The LLM JSON output contract is enforced by exact-field parsing
**Reason**: The `action_options` inline schema and its exact-field parser are deleted with the layer.
**Migration**: None.
