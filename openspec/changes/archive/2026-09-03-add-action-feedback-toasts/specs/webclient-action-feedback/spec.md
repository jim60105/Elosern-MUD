## ADDED Requirements

### Requirement: The client owns a bounded action-feedback toast queue
The WebClient store SHALL maintain a client-local toast queue as the sole writer of toast state:
each entry carries a monotonically increasing id, a title, an optional subtitle, and a tone of
`info` or `crit`; the queue holds at most four entries and appending a fifth evicts the oldest
immediately (FIFO); every entry disappears automatically after roughly five seconds unless
dismissed earlier, and clicking an entry dismisses it. The queue SHALL NOT be persisted anywhere,
SHALL NOT enter the narrative feed, and its entries SHALL present only client-composed text or a
verbatim server-authored action message — never data invented for a surface that has no backing
read model. The rendered queue SHALL anchor above every overlay so a toast stays visible while the
creation overlay is mounted, and its surface SHALL use the `feedback-` test-id prefix family.

#### Scenario: The queue bounds at four entries FIFO
- **WHEN** a fifth toast is pushed onto a full queue
- **THEN** the oldest entry leaves immediately, the four newest remain, and order is preserved

#### Scenario: Toasts self-dismiss and answer clicks
- **WHEN** a toast remains untouched
- **THEN** it fades out after the bounded lifetime, and clicking it removes it at once

#### Scenario: A toast survives the creation overlay
- **WHEN** a toast is surfaced while the creation overlay is mounted
- **THEN** the toast renders above the overlay and is fully visible and clickable

#### Scenario: Toast state never leaks to persistence or the feed
- **WHEN** any number of toasts are pushed and dismissed
- **THEN** no storage write occurs, the narrative feed gains no line from the toast path, and a
  reload shows an empty queue

### Requirement: The concept apply surfaces exactly one confirmation or one failure toast
When the client applies the proposal delivered by a recognized matching successful
`creation.concept` result, it SHALL surface exactly one info-toned toast confirming the apply;
when it recognizes a matching non-success `creation.concept` result, it SHALL surface exactly one
crit-toned toast whose title is the envelope's server-authored message verbatim (or the single
stable fallback line when none is carried). Each tone SHALL have exactly one writer, and a
recognized completion SHALL never yield two toasts of either tone for the same success or the
same failure. Toasts SHALL be additive: the existing narrative single-line channel outside the
creation overlay and the overlay's own result region keep their current behaviour unchanged.

#### Scenario: A successful concept apply confirms once
- **WHEN** a dispatched `creation.concept` settles with the applied success code and its
  proposal is applied to the creation form
- **THEN** exactly one info toast naming the applied proposal appears and the narrative feed gains
  no success line

#### Scenario: A failed concept apply speaks critically once
- **WHEN** a dispatched `creation.concept` settles with a rejected result carrying a
  server-authored message
- **THEN** exactly one crit toast shows that message verbatim while the overlay's result region
  still shows its own line unchanged

#### Scenario: A message-less failure still announces
- **WHEN** a matching `creation.concept` failure carries no usable message
- **THEN** the crit toast shows the single stable fallback line instead of nothing
