# correspondence-player-surface Specification

## Purpose
Provides branch-only letter sending and acquisition while keeping collected letters portable and collection separate from first-reading knowledge.

## Requirements

### Requirement: Sending and collection require any branch

Players SHALL send bounded free text to established recipients only at a 銀羽驛站 branch. At any branch they SHALL collect all due letters for their identity with no home-city restriction. Away from branches the personal surface SHALL expose only previously collected letters, never uncollected bodies.

#### Scenario: Collect at another settlement
- **WHEN** a player has due letters and visits a different branch
- **THEN** all due letters are collected without changing their unread state

#### Scenario: Remote personal list
- **WHEN** a player opens personal letters away from a branch
- **THEN** only collected letters and their bodies are accessible

#### Scenario: Invalid send
- **WHEN** recipient resolution is invalid/ambiguous or body bounds fail
- **THEN** no send, deadline or narrative source commits

### Requirement: Collection and reading remain distinct

Collection SHALL NOT establish content knowledge. First authorized opening of a collected letter SHALL record first-read exactly once and a durable read source. Previously collected letters SHALL be readable anywhere; rereading SHALL NOT duplicate read events or cognition.

#### Scenario: Collected remains unread
- **WHEN** a letter is collected but never opened
- **THEN** its content remains unknown and first-read tick is absent

#### Scenario: Read and reread remotely
- **WHEN** the player opens a collected letter twice away from a branch
- **THEN** first opening records one read occurrence and subsequent opening changes no first-read state

### Requirement: Browser and text channels share authoritative permissions

Finite letter operations SHALL use server-authorized actions with text-client equivalents; text fields SHALL remain free-form. Actual command keys/syntax/context SHALL be documented in both player command references with contract tests. Requesting another player letter or uncollected body SHALL reject server-side.

#### Scenario: Forged letter access
- **WHEN** a browser or text request names another identity letter or an uncollected body
- **THEN** the owner/collection gate rejects without text leakage
