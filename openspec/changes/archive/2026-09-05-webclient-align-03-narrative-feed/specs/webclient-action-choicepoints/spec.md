# Delta spec: webclient-action-choicepoints (webclient-align-03-narrative-feed)

## REMOVED Requirements

### Requirement: The choice-point renders generating and ready states at the stream end
**Reason**: The design draft has exactly one suggestion surface — the action dock's 建議 pane.
The duplicate stream-end block produced two live card groups for one committed payload; the
dock pane's generating → ready lifecycle stays specified under
`webclient-context-actions-suggestions`.
**Migration**: Suggestion status presentation is governed by the suggestions capability's
suggestion-pane requirement; the dock pane replaces every stream-end rendering.

### Requirement: The choice-point is a movable stream-end block owned by the narrative facade
**Reason**: With the stream block removed there is no stream-end block to own; the facade's
single-owner contract loses its only consumer.
**Migration**: No narrative-side block ownership remains; the dock pane renders from committed
panel state through the existing dock surface.

### Requirement: Choice-point cards share the dock card component and click path
**Reason**: There is no stream card twin any more; one card surface dispatches the one
`ui_action` envelope contract already specified for dock suggestion cards.
**Migration**: Card dispatch identity and the `options.dismiss` contract are asserted against
the dock pane's cards by the suggestions capability's suggestion-pane requirement.

### Requirement: Degraded rule cards never enter the stream
**Reason**: The stream renders no suggestion surface at all, so the stream-side exclusion became
vacuous; the surviving rule — degraded cards present only through the dock pane — moves to the
suggestions capability.
**Migration**: See the suggestions capability's suggestion-pane requirement's degraded
scenario.

### Requirement: The choice-point recovers deterministically across sessions
**Reason**: Block-state recovery was the stream block's transport lifecycle; the dock pane's
committed-state-only presentation and the protocol's epoch retirement already specify the same
guarantee for the surviving surface.
**Migration**: Transport-reset clearing of suggestion presentation is asserted through the
dock pane under the suggestions capability's suggestion-pane requirement.
