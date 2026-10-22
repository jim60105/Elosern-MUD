# Design

## Context

`fulfill_record_for` currently emits observers during planning. `buy` computes its inventory/ACQUIRE plan before opening its source transaction, so `on_commit` can execute immediately. The actual transition writer later creates completion facts, but its serializer only retains a subset of objective fields. Terminal records have already cleared ordinary target bindings.

## Goals / Non-Goals

**Goals:** Pure planning; authoritative completion snapshots; one owner notification after the outer commit.

**Non-Goals:** No reward timing, quest progression, objective semantics or trigger-policy changes. Future completion-title evaluation is owned by D, not implemented here. No new persistent quest model or migration.

## Decisions

1. Make fulfillment computation side-effect-free. Remove observer dispatch from pure planners and migrate callers, rather than adding a transaction merely around each planner. The quest transition writer owns newly-completed detection and calls the existing completion observer registry only through an outer `on_commit` callback after its immutable event has been finalized.
2. Build a detached frozen completion receipt from authoritative pre-completion bindings and the actual satisfied objective. Carry it through the existing quest transition/auto-settlement plan instead of reconstructing missing roles from the terminal record. Include quest/definition identity, objective kind/quantity, destination, bound recipient/target identities with readable labels, escort protected/meeting roles and required relation where relevant, plus the actual completed result. Do not copy arbitrary blueprint prose or private NPC state.
3. Cover every actual write path: skill/event planners, inventory ACQUIRE, item delivery, arrival/escort, automatic reward chains and direct quest replacements. Chain planners retain each intermediate completion snapshot before clearing bindings; a chain receipt is not evidence until its enclosing owner commits it. Explicitly migrate replacement/delta callers and observer signatures with no alias.
4. The post-commit observer receives the canonical completion `source_id` and finalized result envelope, not a source identity rebuilt in the service. Unchanged terminal replacements or replayed receipts neither create a new event nor schedule a new completion attempt. A later read/generation failure never undoes gameplay. Keep the observer isolation contract and facade exception logging.

## Risks / Trade-offs

- Planning callers may have relied on observer side effects -> search all fulfillment/observer references with code intelligence during apply and migrate all callers; no dual dispatch.
- An outer purchase/transfer can fail after the quest writer returns -> register notification only inside that outer transaction and prove discard on failure after required writes.
- C must remain independently usable before D -> initially forward existing authoritative empty/nonempty award results; D adds completion-specific grants at this same finalization seam.

## Migration Plan

Cut over pure fulfillment and owner dispatch together. No old-callback shim. Preserve current grant attribution until D. Update affected technical/command documentation if availability changes; command syntax itself remains unchanged.

## Verification and size

Budget: receipt and pure-planner cutover 2 h; write-owner notification 2 h; purchase/chain/objective/rollback regressions 2 h; smoke/docs/traceability/gates 2 h. Prove a first-ever ACQUIRE completion sees its newly committed deed and a discarded plan or late failing purchase makes no nomination call.
