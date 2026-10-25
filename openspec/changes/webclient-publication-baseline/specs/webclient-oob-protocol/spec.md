# Spec Delta

## MODIFIED Requirements

### Requirement: WebClient text commands refresh presentation after completion
The project `text` input function SHALL preserve Evennia's ordinary command semantics and SHALL observe both callback and errback settlement without replacing the original Deferred value or Failure. It SHALL compare all eager candidates from then-current canonical state only after a WebClient command settles and use a fresh complete snapshot when a semantic checkpoint or recovery requires it and SHALL NOT emit graphical state for Telnet commands. Idle handling, nickname replacement, command output, session counters, and text access SHALL remain functional.

#### Scenario: A completed WebClient command refreshes state
- **WHEN** a puppeted WebClient submits an ordinary synchronous text command that changes canonical state
- **THEN** normal command output is delivered and changed content/metadata is published after command completion using a delta, a qualifying checkpoint uses one fresh full snapshot, and wholly unchanged presentation consumes no revision

#### Scenario: A Telnet command remains text-only
- **WHEN** a Telnet player executes the same command
- **THEN** normal output and state change occur without an Elosern graphical snapshot

#### Scenario: Idle input remains idle handling
- **WHEN** the WebClient sends Evennia's configured idle command
- **THEN** the session idle counter is updated without command execution or a fabricated gameplay refresh

#### Scenario: Command errback preserves failure semantics
- **WHEN** a WebClient command handler Deferred settles through its errback path
- **THEN** the wrapper preserves the original Failure and ordinary error output while attempting at most one safe post-settlement refresh

#### Scenario: Presentation failure never consumes a command failure
- **WHEN** the post-settlement publication attempt fails
- **THEN** the presentation failure SHALL be logged separately and SHALL NOT consume a command failure
