## REMOVED Requirements

### Requirement: The dismiss action accepts exactly an empty payload
**Reason**: `options.dismiss` is unregistered and its adapter deleted; the client no longer dispatches a dismissal.
**Migration**: None. The action roster in `webclient-action-dispatch` loses the id.

### Requirement: Dismiss clears the displayed proposal state through per-session eviction
**Reason**: The eviction service is deleted with the suggestion trigger service.
**Migration**: None.

### Requirement: Dismissal publishes exactly one state-backed unavailable update
**Reason**: There is no suggestion state to publish and no dismissal to publish after.
**Migration**: None.

### Requirement: Adapters receive the authenticated session through a fixed optional parameter
**Reason**: The ABI is general dispatcher behaviour, not dismiss-specific, and is specified independently by `webclient-action-dispatch` ("Adapters may receive the authenticated session through a fixed optional third parameter").
**Migration**: See `webclient-action-dispatch`; the dispatcher and every surviving adapter keep the three-argument signature.
