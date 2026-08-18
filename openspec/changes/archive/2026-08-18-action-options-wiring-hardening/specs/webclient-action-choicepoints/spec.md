## MODIFIED Requirements

### Requirement: The choice-point is a movable stream-end block owned by the narrative facade
The choice-point SHALL be attached to the narrative stream through the
`window.Elosern.narrativeInput` facade and SHALL NOT create a separate append path. The narrative
facade's `StreamEndBlock.appendNode()` path SHALL place every newly committed narrative text node
before a mounted choice-point block, so the block remains the final stream node within the same
single scroll/unread decision. The existing scroll-keep and polite unread-marker behavior SHALL
count each committed narrative text event exactly once, unaffected by a mounted block. The facade
SHALL expose attach, replace-in-place, and remove operations as the single owner of choice-point
geometry; it SHALL NOT expose a separate move-to-end operation, and no other module SHALL mutate
the narrative container directly for the choice-point.

#### Scenario: Text appended after a ready commit stays before the block
- **WHEN** `ready` cards are committed at the stream end and the server then appends a look
  output, a talk reply, or a scene-flavor push
- **THEN** the newer text appears between the stream's older content and the choice-point block,
  the block remains last without a second relocation call, and the player can still click the cards

#### Scenario: The block never splits the stream unexpectedly
- **WHEN** multiple narrative appends and one choice-point insertion happen in any order
- **THEN** the narrative reads as exactly one ordered sequence with the choice-point always last,
  and remove leaves the remaining narrative contiguous with no empty placeholder
