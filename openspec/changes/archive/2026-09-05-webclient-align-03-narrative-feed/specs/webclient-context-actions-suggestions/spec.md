# Delta spec: webclient-context-actions-suggestions (webclient-align-03-narrative-feed)

## ADDED Requirements

### Requirement: The dock suggestion pane is the single suggestion surface
The action dock's 建議 pane SHALL be the only surface rendering `suggestions.cards`. Its
presentation SHALL follow the committed `suggestions.status` exactly: `generating` renders the
muted `AI 正在構思建議…` state in the pane without cards; `ready` replaces it in place with the
committed card group rendered through the shared dock card component (label, optional hint,
action-code semantics, digit-key pick affordance, and the draft's card styling); `degraded`
renders the derived rule cards with the muted unavailable-AI note; `unavailable` — and a panel
whose kind is not exploration, an absent panel, or an out-of-contract suggestions section —
renders no cards. The narrative stream SHALL render no suggestion line, card group, or
stream-end block under any status, including a ready group followed by appended narrative.

Activating a pane card SHALL dispatch exactly the same `ui_action` envelope the shared dock card
component dispatches (`action_code` + params for `known_action`; `explore.talk_freeform` with
`speech: label` for `freeform`), with the existing rejection/stale/busy toast surface and the
existing input-line echo behavior applying unchanged. The pane SHALL carry the `✕ 清除建議`
control dispatching `options.dismiss` under the existing confirmation contract, and the tab's
count badge SHALL equal the committed card count. A transport generation reset
(`beginTransport`) SHALL retire the pane's card presentation with the epoch: no card from a
retired epoch remains clickable before the first new snapshot arrives.

#### Scenario: Generating then ready replaces in place inside the pane
- **WHEN** the trigger service publishes `suggestions.status = "generating"` and a later commit
  reports `ready` with 3–5 cards
- **THEN** the pane shows the muted generating state first and then exactly one card group with
  no duplicated or stacked cards, and the narrative stream shows no suggestion content

#### Scenario: The narrative stream never carries suggestion cards
- **WHEN** a `ready` card group is committed while narrative lines continue to append
- **THEN** no card, generating line, or stream-end block appears anywhere outside the dock pane

#### Scenario: A pane card dispatches the shared contract
- **WHEN** the player activates a `ready` card in the pane
- **THEN** the dispatch is the shared dock card's `ui_action` envelope for that card, and a
  `freeform` card dispatches `explore.talk_freeform` with `speech: label` and exactly one echo

#### Scenario: Degraded rule cards appear only in the pane
- **WHEN** the AI service is offline and the committed status is `degraded`
- **THEN** the pane shows the rule cards with the muted note and no suggestion content renders
  anywhere else

#### Scenario: Dismiss keeps the committed-state invariant
- **WHEN** the player activates `✕ 清除建議` while a mutation is in flight or the request is
  rejected as stale/busy
- **THEN** no `options.dismiss` is admitted and the pane remains exactly as last committed;
  only the next accepted commit decides removal

#### Scenario: Transport reset retires the card presentation
- **WHEN** the browser begins a new transport generation while a `ready` group is displayed
- **THEN** the retired epoch's cards stop being clickable within that same store notification,
  and a later commit presents fresh cards only from the new epoch's snapshot
