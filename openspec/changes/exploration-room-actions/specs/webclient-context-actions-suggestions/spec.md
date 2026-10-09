## RENAMED Requirements

- FROM: `### Requirement: The dock suggestion pane is the single suggestion surface`
- TO: `### Requirement: The suggestions card is the single suggestion surface`

## MODIFIED Requirements

### Requirement: The suggestions card is the single suggestion surface
The 建議 pill in the exploration command panel SHALL open the centred suggestions card, which SHALL be the only surface rendering `suggestions.cards`, and its presentation SHALL follow the committed `suggestions.status` exactly, per the status scenarios below. The narrative stream SHALL render no suggestion line, card group, or stream-end block under any status, including a ready group followed by appended narrative.

#### Scenario: Generating then ready replaces in place inside the pane
- **WHEN** the trigger service publishes `suggestions.status = "generating"` and a later commit
  reports `ready` with 3–5 cards
- **THEN** the card shows the muted generating state first and then exactly one card group with
  no duplicated or stacked cards, and the narrative stream shows no suggestion content

#### Scenario: The narrative stream never carries suggestion cards
- **WHEN** a `ready` card group is committed while narrative lines continue to append
- **THEN** no card, generating line, or stream-end block appears anywhere outside the suggestions card

#### Scenario: A pane card dispatches the shared contract
- **WHEN** the player activates a `ready` card row in the suggestions card
- **THEN** the dispatch is the shared dock card's `ui_action` envelope for that card, and a
  `freeform` card dispatches `explore.talk_freeform` with `speech: label` and exactly one echo

#### Scenario: Degraded rule cards appear only in the pane
- **WHEN** the AI service is offline and the committed status is `degraded`
- **THEN** the card shows the rule cards with the muted note and no suggestion content renders
  anywhere else

#### Scenario: Dismiss keeps the committed-state invariant
- **WHEN** the player activates `✕ 清除建議` while a mutation is in flight or the request is
  rejected as stale/busy
- **THEN** no `options.dismiss` is admitted and the card remains exactly as last committed;
  only the next accepted commit decides removal

#### Scenario: Transport reset retires the card presentation
- **WHEN** the browser begins a new transport generation while a `ready` group is displayed
- **THEN** the retired epoch's cards stop being clickable within that same store notification,
  and a later commit presents fresh cards only from the new epoch's snapshot

#### Scenario: Generating renders the muted state in the pane
- **WHEN** the committed status is `generating`
- **THEN** the card renders the muted `AI 正在構思建議…` state without cards

#### Scenario: Ready replaces the muted state in place through the shared component
- **WHEN** the committed status becomes `ready`
- **THEN** the committed card group replaces the muted state in place, rendered as `ChoiceCard` rows carrying the card's label, optional hint, action-code semantics, and digit-key pick affordance

#### Scenario: Degraded renders rule cards with the note
- **WHEN** the committed status is `degraded`
- **THEN** the card renders the derived rule cards with the muted unavailable-AI note

#### Scenario: Non-ready states and off-contract panels render no cards
- **WHEN** the status is `unavailable`, or the panel's kind is not exploration, or the panel is absent, or the suggestions section is out of contract
- **THEN** the card renders no cards

#### Scenario: Pane cards dispatch the shared component's envelope
- **WHEN** a card row is activated
- **THEN** the dispatch is exactly the `ui_action` envelope the shared dock card component dispatches (`action_code` + params for `known_action`; `explore.talk_freeform` with `speech: label` for `freeform`), with the existing rejection/stale/busy toast surface and the existing input-line echo behavior applying unchanged

#### Scenario: The pane carries dismiss and the chip names the count
- **WHEN** the suggestions card is presented and the 建議 pill is rendered
- **THEN** the card carries the `✕ 清除建議` row, above the trailing `✕ 返回` row, dispatching `options.dismiss` under the existing confirmation contract, and the pill names the committed card count (`建議 N`) whenever that count is positive

#### Scenario: A transport reset retires the epoch's cards
- **WHEN** a transport generation reset (`beginTransport`) occurs
- **THEN** the card presentation is retired with the epoch: no card from a retired epoch remains clickable before the first new snapshot arrives
