## REMOVED Requirements

### Requirement: Generation resolves to an OptionSet or the None degrade outcome
**Reason**: The AI action-suggestion surface is retired end to end; nothing consumes an `OptionSet`, so the guarded generation entry point has no caller and no contract to keep.
**Migration**: None. Exploration actions are the deterministic dock's own affordances.

### Requirement: Bounded-context serialization is public-only and truncation-ordered
**Reason**: The prompt context existed only to feed the retired generation call.
**Migration**: None.

### Requirement: Prompt assembly honors the registered placeholder allowlist
**Reason**: The two `action_options` prompt keys and their allowlists are deleted with the layer (`ai-action-options-prompts`).
**Migration**: None.

### Requirement: Freeform NPC references are bound before validation
**Reason**: `{npc_index}` binding existed only to resolve model output into card params; there is no model output to bind.
**Migration**: None.

### Requirement: Validation failures retry within the bounded budget
**Reason**: The retry loop wrapped the retired generation call.
**Migration**: None.

### Requirement: Guardrail hooks install atomically and idempotently
**Reason**: With no generation entry point and no output schema, the layer registers no degrade fallback and no schema at startup.
**Migration**: None.

### Requirement: The layer is strictly proposal-only
**Reason**: The module is deleted; the repository's single-writer invariant is unchanged and still enforced by the import-linter contract for every surviving `world/ai/` module.
**Migration**: None.

### Requirement: Monster entries carry identity facts
**Reason**: Monster identity in the bounded context existed only for the suggestion prompt; the panel and board surfaces keep their own identity fields.
**Migration**: None. Monster identity presentation is owned elsewhere.
