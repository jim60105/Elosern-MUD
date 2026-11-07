## REMOVED Requirements

### Requirement: The exploration dock renders the suggestions section from the validated v5 panel
**Reason**: The AI action-suggestions feature is retired end to end. The `context_actions` panel no longer carries a `suggestions` envelope, the exploration dock no longer renders a suggestions section or card, and no 建議 pill exists to open one.
**Migration**: None. The exploration command panel keeps the exit compass and the shared readout; exploration actions are reached through the exit compass, the presence rail, the verb card, and the place card.

### Requirement: One shared card component renders every suggestion card
**Reason**: There is no suggestion card left to render; `ChoiceCard` remains the shared shell for the dialogue picks, the verb card, the presence overflow card, the wait card, and the rest entry, and none of those consume suggestion cards.
**Migration**: None.

### Requirement: Suggestion cards execute exact envelopes through the action client
**Reason**: With no suggestion card and no `options.dismiss` action, the client emits no suggestion envelope and no dismissal envelope; the one action client and its envelope contract are unchanged for every other surface.
**Migration**: None.

### Requirement: A degraded payload with zero cards renders the defined empty-state
**Reason**: A degraded suggestions payload no longer exists, so the zero-card empty state has no producer and no surface.
**Migration**: None.
