## ADDED Requirements

### Requirement: Facade is the sole game-code log entry point

All game code under `world/`, `typeclasses/`, `commands/`, `server/`, and
`web/` MUST emit operational logs exclusively through the
`world.observability` facade (`log_info`, `log_warn`, `log_error`,
`log_debug`). The facade MUST depend only on the standard library, the
Evennia logger, and Django settings, and MUST NOT import game modules.

#### Scenario: Facade routes levels to the Evennia logger

- **WHEN** `log_info`, `log_warn`, or `log_error` is called with a valid event
- **THEN** the message reaches the Evennia logger at the corresponding level
  (`log_info`, `log_warn`, `log_err`)

#### Scenario: Debug events respect the VERBOSE setting

- **WHEN** `log_debug` is called while `settings.VERBOSE` is false
- **THEN** nothing is written to the log
- **AND** when `VERBOSE` is true the event is written

### Requirement: Facade renders one structured grep-friendly line

Every facade emission MUST be a single line of the form
`[level] event | mod.func:line | k=v ... [ | tb: summary]`. The caller
segment MUST be derived by the facade from its own call stack, never passed
by callers. Context values MUST render with keys sorted, plain
`int`/`float`/`bool` verbatim, strings containing spaces double-quoted,
containers `repr`-truncated to 200 characters, and `None`-valued keys
omitted entirely.

#### Scenario: Context ordering and formatting are deterministic

- **WHEN** the same event is logged twice with the same context
- **THEN** both lines are byte-identical with sorted keys and the truncation
  and quoting rules applied

### Requirement: log_error captures the exception chain in one line and the full traceback separately

`log_error(event, exc=error)` MUST append a `tb:` segment listing every link
of `error`'s exception chain, outermost first, as `Type: msg @ file:line`
joined by ` <- `, and MUST additionally send the full formatted traceback to
the Evennia error log.

#### Scenario: Chained exception is summarized outermost-first

- **WHEN** `log_error` is called with an exception raised `from` another
  exception
- **THEN** the `tb:` segment contains both links in outermost-first order and
  the Evennia error log contains the complete traceback text

### Requirement: The facade never raises

A facade call MUST NOT raise under any circumstance, including internal
import failure or logger failure; on internal failure it MUST fall back to
writing the rendered line to stderr via the standard library.

#### Scenario: Logger failure degrades to stderr

- **WHEN** the Evennia logger raises during a facade call
- **THEN** the caller sees no exception and the line appears on stderr

### Requirement: Command execution emits boundary events

Every repository production command MUST run through the repository command
base class, which emits `cmd_in` (context `char`, `cmd`, truncated `args`)
when a command begins and `cmd_done` (context `char`, `cmd`, `ms`,
`outcome=ok`) when it completes normally. Because the Evennia command
handler invokes the post-command hook only on normal completion, an
aborted command is reconstructed from an unpaired `cmd_in`; the base class
MUST NOT fabricate an error outcome it cannot observe.

#### Scenario: A successful command produces an in/done event pair

- **WHEN** a player command completes without error
- **THEN** exactly one `cmd_in` and one `cmd_done` event are logged with the
  actor pk, command key, and elapsed milliseconds

#### Scenario: Commands from different modules all pass through the seam

- **WHEN** commands originally defined in two different `commands/` modules
  execute through the command handler
- **THEN** both emit the in/done pair, proving full-base coverage rather
  than per-module opt-in

### Requirement: Server startup emits lifecycle events

Each server-startup registration and synchronization step MUST log a
`startup_step` info event with `step` and `ms` context on success, and MUST
log through the facade (not a swallowed free-text warning) on failure or
degradation, so the startup log alone answers which subsystems came up
healthy and which degraded.

#### Scenario: Degraded startup is visible in the log

- **WHEN** a guardrail layer registration is skipped at server start
- **THEN** a facade event identifies the failed step and the reason in
  context
