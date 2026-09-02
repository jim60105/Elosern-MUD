## ADDED Requirements

### Requirement: A non-success action result surfaces its message exactly once

When the client recognizes a matching non-success `ui_action_result` — outcome `rejected`, `stale`, or `error`, carrying the same request id and epoch as its in-flight dispatch — and the creation overlay is not the presenting surface, it SHALL make the envelope's server-authored message visible to the player exactly once per recognized result, rendered as one narrative error line carrying that message verbatim through the bounded narrative path. The client SHALL NOT paraphrase, translate, or synthesize replacement text while the envelope carries a message, and SHALL show a single stable fallback line when a recognized non-success result carries none. A successful result SHALL surface no additional line. While the creation overlay is mounted and presenting results, no narrative line SHALL be appended for that result. Surfacing SHALL NOT alter the in-flight lock, the revision-gated release (including the `stale` rule that holds the lock until the recovery snapshot commits), the uncertain-result notice, or the no-automatic-resubmit rule.

#### Scenario: A rejected move explains itself in the feed

- **WHEN** a dispatched action receives a matching rejected result carrying a server-authored message while exploration mode is presented
- **THEN** exactly one narrative line shows that message verbatim, the player keeps keyboard focus without any modal, and no mutation echo accompanies it

#### Scenario: A stale admission speaks through the recovery

- **WHEN** the client dispatches against a superseded `base_revision` and receives a matching `stale` result followed by the recovery snapshot
- **THEN** the stale message appears once as a narrative error line, the lock still releases only when the recovery revision commits, and the client never resubmits automatically

#### Scenario: One recognized result yields one line

- **WHEN** the same non-success result is delivered or re-observed by the client more than once
- **THEN** the narrative shows the message once and a successful result appends no error line

#### Scenario: Creation mode keeps one presenting surface

- **WHEN** a non-success result arrives while the creation overlay is mounted and presenting results
- **THEN** the overlay shows the rejection and the narrative feed gains no duplicate line

#### Scenario: A message-less non-success still speaks

- **WHEN** a recognized non-success result carries no usable message
- **THEN** the narrative shows the single stable fallback line rather than failing silently
