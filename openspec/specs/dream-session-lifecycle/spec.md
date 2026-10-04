# dream-session-lifecycle Specification

## Purpose
Tracks bounded, resumable dream collaboration exchanges and explicit confirm-or-draft departure without dependence on additional generation.

## Requirements

### Requirement: Only completed exchanges consume the six-exchange budget

An exchange SHALL consist of one player message and one successfully delivered validated response. The session SHALL persist at most six completed exchanges and display remaining count. Opening text, confirmation actions, transport failures, validation retries and duplicate submission SHALL NOT consume exchanges. Rendered input SHALL have an independent hard bound.

#### Scenario: Retry and duplicate do not consume
- **WHEN** one message retries validation and is submitted twice
- **THEN** one successfully delivered response increments the persisted count once

#### Scenario: Reconnect after five
- **WHEN** a player reconnects with five completed exchanges
- **THEN** one remains and reconnect does not reset the count

#### Scenario: Oversized player message
- **WHEN** one message exceeds the rendered-input bound
- **THEN** it rejects without generation or budget consumption

### Requirement: Convergence and exit require explicit choices

Exchange five SHALL begin convergence. Exchange six SHALL summarize spoiler-free direction with no new question. At six, free text SHALL stop and confirmation or draft preservation SHALL be offered. Early departure SHALL offer the same choices. Only explicit valid-version confirmation SHALL submit; incomplete/unconfirmed content SHALL remain a draft.

#### Scenario: Sixth completes
- **WHEN** the sixth validated response is delivered
- **THEN** free-text input closes and confirm/draft choices appear without a seventh exchange

#### Scenario: Exit before cap
- **WHEN** the player leaves after two exchanges
- **THEN** the same explicit choices are available and draft preservation schedules nothing

### Requirement: Failures preserve progress and permit offline awakening

Cancellation, disconnect and model failure SHALL preserve saved session progress and the independently committed sleep outcome. Ending/awakening SHALL require no further model call. Later entry SHALL resume saved discussion without duplicate request submission or repeated settlement of the original sleep.

#### Scenario: Failure after five
- **WHEN** generation fails while the player has five completed exchanges
- **THEN** the count stays five and draft/awakening remains possible offline

#### Scenario: Restart during delivery
- **WHEN** the same response-delivery identity is replayed after restart
- **THEN** presentation can recover it without a second completed exchange
