## REMOVED Requirements

### Requirement: Fingerprint identifies the situation, not the moment
**Reason**: The situation fingerprint existed only to key the retired option cache and its presentation snapshot; `web/webclient/presentation/fingerprints.py` is deleted with it.
**Migration**: None.

### Requirement: One LLM call per cache residency with replay and pending semantics
**Reason**: There is no suggestion generation to cache or replay.
**Migration**: None.

### Requirement: Session-scoped options presentation state survives async completion and puppet change
**Reason**: `session.ndb.options_state` and its immutable `OptionsSnapshot` are deleted; no surface reads suggestion state.
**Migration**: None.

### Requirement: Delivery is guarded by token and epoch, and retired generations write nothing
**Reason**: The guarded delivery wrote the retired presentation state only.
**Migration**: None. The epoch/revision guard that every panel push uses is owned by `webclient-publication-assembly` and `webclient-publication-settlements`.

### Requirement: Eviction is per-session and clears the displayed situation
**Reason**: Eviction existed for the `options.dismiss` action, which is deleted.
**Migration**: None.

### Requirement: The negative memo applies to transport failures only
**Reason**: The negative memo suppressed repeat suggestion generations; no generation remains.
**Migration**: None.

### Requirement: Watcher registry resolves live sessions for the room-entry hook
**Reason**: The registry mechanism survives (it serves every targeted panel push), so its contract moves to `webclient-publication-settlements` rather than dying here.
**Migration**: See the added requirement in `webclient-publication-settlements`.

### Requirement: Scheduling never raises and never blocks
**Reason**: `schedule_action_options` is deleted; no trigger schedules anything.
**Migration**: None.

### Requirement: Current situation freshness gates session-backed suggestions
**Reason**: The freshness gate compared a stored suggestion fingerprint with the current situation; neither side exists.
**Migration**: None.

### Requirement: All committed player relocations and terminal combat returns trigger options
**Reason**: The room-entry and terminal-combat trigger call sites are deleted from `typeclasses/characters.py` and the dispatcher.
**Migration**: None.

### Requirement: Dismissal prevents replay from a concurrent older generation
**Reason**: The dismissal barrier protected against a racing generation that no longer exists.
**Migration**: None.

### Requirement: Retired pending generations are removed by identity immediately
**Reason**: There is no pending-generation registry to retire an entry from.
**Migration**: None.
