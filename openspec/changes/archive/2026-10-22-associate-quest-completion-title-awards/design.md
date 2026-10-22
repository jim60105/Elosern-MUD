# Design

## Context

Current shipped registry rows have no quest-completed title, so the reviewed mismatch is a future-contract gap rather than a current starter-title defect. The generic title planner associates awards with an action source; completion persistence reads a different quest source. The starter epithet belongs to a later reward-claim occurrence and must retain that attribution.

## Goals / Non-Goals

**Goals:** Make a synthetic/future quest-completed fixed-title predicate work through the existing completion owner with atomic source attribution and generic suppression.

**Non-Goals:** No new shipped title, changed predicate truth, starter-at-completion award, trigger-type exclusion, generated-epithet award result, migration or event patching.

## Decisions

1. Add one narrow rules-layer completion-award settlement operation using the existing registry predicate and unified automatic award entry point. The quest owner supplies C's completion receipt/source after the new quest state is applied, and receives all newly granted results before writing the immutable event. Several grants share that occurrence; grants to another recipient do not suppress the nominated player.
2. Remove quest-completed-family automatic discovery from unrelated generic action grants so an already completed quest cannot be discovered later under an arbitrary action source. Retain the pure predicate evaluator for rules consumers. A new occurrence with an already-owned title yields no new award; replay of the original occurrence returns its stored original results before reevaluation.
3. Forward finalized results through C's post-commit envelope into the service's unchanged generic award check. Do not query a not-yet-existing event to manufacture its original results, persist an event early, or patch awards into it afterward. A later wake/logout may reuse that eligible deed under the ordinary window.
4. Extend durable and idmapper/cache rollback ownership for title collection/equipped state in every enclosing completion owner, including inventory/purchase, delivery, arrival, automatic settlement chains and action transactions. The inner quest writer alone cannot restore caches after an outer writer fails. Reuse existing snapshot surfaces rather than introducing a parallel undo system.

## Risks / Trade-offs

- Many enclosing owners share the delta writer -> maintain an explicit callsite/snapshot checklist in implementation notes and inject failures after the quest writer returns.
- Synthetic registry conditions could accidentally alter authored content -> isolate registries per test and restore them; ship no registry edits.
- A service-specific title exception would hide attribution defects -> tests invoke real award settlement and the unchanged generic suppression entry.

## Migration Plan

Integrate C first, then replace planner ownership and completion finalization together. Existing malformed title state stays fail-closed. No migration, compatibility dispatch or historical award repair. Update technical title/quest documentation and traceability during apply.

## Verification and size

Budget: rules award owner 2 h; caller/cache snapshot integration 2 h; synthetic attribution/replay/outer rollback regressions 2 h; source-to-nomination smoke/docs/gates 2 h. Demonstrate new/owned/multiple/other-recipient awards and later feed reuse.
