# webclient-publication-settlements Specification

## Purpose
Group committed presentation effects causally for every watcher while preserving independent overlapping text and graphical command execution.

## Requirements

### Requirement: Independent pending ingress retains ordinary execution semantics
Overlapping text commands and graphical work SHALL execute under existing command/domain admission. Presentation grouping SHALL NOT reject or serialize text execution behind a pending Deferred. Each completed operation SHALL publish against current canonical state in completion order without leaking another operation's presentation context.

#### Scenario: Two text commands settle in reverse order
- **WHEN** two independently pending text commands complete second then first
- **THEN** both preserve their original values/Failures and their current-state refreshes enqueue in that completion order

#### Scenario: Text during graphical pending work
- **WHEN** a graphical adapter is pending while a text command commits and explicit sync arrives
- **THEN** text and sync remain available; neither uses the graphical operation's context or interleaves a completed send batch

#### Scenario: Deferred context does not leak
- **WHEN** one callback returns a pending Deferred and another actor operation runs
- **THEN** the second operation cannot inherit the first causal group

### Requirement: Every watcher receives one final checkpoint publication per committed group
Ordinary pushes and checkpoint facts from one committed group SHALL coalesce for every lawful watcher before any group frames send, independent of callback order and initiating-session presence. A qualifying group SHALL publish one fresh complete snapshot instead of an intermediate delta.

#### Scenario: Two watchers see push before fact
- **WHEN** one committed group invokes ordinary push callbacks before its checkpoint callback for two WebClient watchers
- **THEN** each independently receives one final fresh full snapshot and no preceding group delta

#### Scenario: Fact before push also coalesces
- **WHEN** the checkpoint callback executes before ordinary push callbacks
- **THEN** the same one-snapshot outcome holds for all watchers

#### Scenario: Out-of-ingress completion coalesces
- **WHEN** an asynchronous sleep/dream completion commits without a pending command on its watchers
- **THEN** its ordinary push and checkpoint callbacks coalesce regardless of order

#### Scenario: Later asynchronous change is distinct
- **WHEN** an options or art generation completes after the earlier group drained
- **THEN** it forms a separate ordered publication and never reuses the earlier group to suppress it

### Requirement: Queued publication returns its actual completion outcome
Every public queueing publication entry SHALL return the same deferred-completion contract. Actual receipt resolves after full presentation/result send, retirement resolves no publication, and preflight/send/overflow failure SHALL be explicit. No synchronous guessed receipt or receipt/deferred union SHALL be exposed.

#### Scenario: Reentrant sync receives actual receipt
- **WHEN** sync enqueues while a presentation/result batch is being sent
- **THEN** it resolves with the actual later revision or explicit retirement/failure without interleaving that batch

#### Scenario: Bounded group queue overflows
- **WHEN** the pending group/waiter ceiling is exceeded
- **THEN** baseline is invalidated and the caller receives an explicit safe failure rather than silent completion loss
