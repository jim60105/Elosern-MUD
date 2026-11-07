## REMOVED Requirements

### Requirement: Room entry triggers a proposal on deterministic movement success
**Reason**: The room-entry trigger existed only to schedule suggestion generation; `typeclasses/characters.py`'s scheduling helpers and the `at_post_move` call are deleted, and movement settlement is unchanged.
**Migration**: None.

### Requirement: Conversation completion triggers a proposal after publication
**Reason**: The dispatcher's completion hook scheduled suggestion generation; the hook is deleted and the completion publication itself is unchanged (`webclient-action-dispatch`).
**Migration**: None.

### Requirement: Reconnect triggers a proposal subject to the stale predicate
**Reason**: `ui_sync` scheduled suggestion generation after the snapshot; the schedule call is deleted and the snapshot path is unchanged.
**Migration**: None.

### Requirement: The watcher registry is ingress-maintained and pruned
**Reason**: The mechanism survives because every targeted panel push resolves its audience through it; the contract moves, verbatim in substance, to `webclient-publication-settlements`.
**Migration**: See the added requirement in `webclient-publication-settlements`.

### Requirement: Every trigger is fire-and-forget, non-raising, and non-mutating
**Reason**: There is no trigger left to constrain.
**Migration**: None.
