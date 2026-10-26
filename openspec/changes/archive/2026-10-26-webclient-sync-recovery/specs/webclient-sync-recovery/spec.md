# Spec Delta

## Purpose

Repair presentation baseline mismatches and incomplete delivery with one bounded complete synchronization attempt while preserving safe text play.

## ADDED Requirements

### Requirement: Recovery coalesces failures and remains bounded
Incompatible base, invalid publication, incomplete assembly or an unadopted claimed result revision SHALL lock graphical mutations and request one complete repair per failure episode. Recovery SHALL NOT replay actions or historical deltas. A failed repair SHALL not automatically retry.

#### Scenario: Multiple failures coalesce
- **WHEN** base mismatch and assembly failure occur while one repair is requested
- **THEN** one ui_sync is sent and the last complete presentation remains unchanged

#### Scenario: Failed complete response does not loop
- **WHEN** the repair snapshot fails validation or its bounded response deadline expires
- **THEN** mutations remain locked and repeated parts/errors/time passage send no further automatic sync

#### Scenario: Successful full repair reestablishes all eager data
- **WHEN** a valid newer live-sequence complete snapshot arrives
- **THEN** all eager data and metadata replace atomically, recovery clears and normal mutation gates may release

#### Scenario: Unrelated delta cannot rearm failed episode
- **WHEN** a valid delta or partial snapshot arrives after failed repair
- **THEN** failed recovery remains locked until a valid complete snapshot, explicit retry or new transport lifecycle

#### Scenario: Manual recovery stays explicit
- **WHEN** the player explicitly synchronizes after a failed automatic repair
- **THEN** one further complete request may occur without resubmitting any mutation

### Requirement: Action results cannot claim synchronization before adoption
A matching action result newer than committed presentation SHALL initiate complete recovery and retain the mutation lock. Results at or below committed revision SHALL NOT roll back state. Existing request deduplication, foreign/busy-result isolation and uncertain disconnect handling SHALL remain.

#### Scenario: Future claimed revision initiates repair
- **WHEN** matching result claims12 while committed state remains11
- **THEN** the result is recorded once, controls remain locked and one complete sync is requested

#### Scenario: Older result follows newer presentation
- **WHEN** matching result claims10 while complete state is12
- **THEN** presentation stays12 and only the matched in-flight action may complete

#### Scenario: Lost result never causes automatic replay
- **WHEN** transport closes after submit before observed result
- **THEN** reconnect synchronizes canonical state and marks uncertainty without resending the action
