## REMOVED Requirements

### Requirement: Offline persona bundles are authored whole cards grouped into pools
**Reason**: User-approved KISS retirement (§13c) removes the unused whole-card pools, 22 cards and exclusive vocabulary/validation; no production consumer requires them.
**Migration**: No replacement, migration, alias or backup subsystem. Retain complete authored host/examiner, companion, import and quest-template sources; unsupported development databases are reset under §13b. Git history is the recovery source if a separately approved future need arises.

### Requirement: Pool resolution prefers the role tier and falls back to the race
**Reason**: The tier/race pool resolver is unused production infrastructure removed with its exclusive pools; generic tier and race registries remain live and unchanged.
**Migration**: No compatibility resolver or replacement caller. Existing production NPC creation continues through its own complete-card source; no offline or online LLM integration is added.

### Requirement: Offline selection is deterministic by stable identity and persisted once
**Reason**: The stable bundle selector has no production caller; its proposed cutover caller was cancelled. Removing only selection while keeping owned pools/provenance/tests would leave dead weight.
**Migration**: Remove selector and bundle-only provenance acceptance together without reselecting or replacing valid generated cards. Unsupported development data uses the existing reset runbook, never an in-place migration or legacy decoder; preserve current LLM inputs/outputs and call count.
