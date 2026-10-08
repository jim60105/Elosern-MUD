## Purpose

Define the structured logging facade (`world/observability`) that is the sole game-code log entry point, its one-line structured rendering and exception-chain rules, and the boundary lifecycle events (command, startup) it emits.

## Requirements

### Requirement: Facade is the sole game-code log entry point
All game code under world/, typeclasses/, commands/, server/ and web/ MUST emit operational logs exclusively through world.observability (log_info/log_warn/log_error/log_debug). The facade MUST depend only on stdlib, Evennia logger, Django settings and observability-local modules; it MUST NOT import other game modules.

#### Scenario: Facade routes levels to the Evennia logger
- **WHEN** log_info, log_warn or log_error emits a valid event
- **THEN** the corresponding Evennia level receives its operational line before recent-sink delivery

#### Scenario: Debug events respect the VERBOSE setting
- **WHEN** log_debug is called with VERBOSE false or true
- **THEN** false emits nothing and true emits the operational event

#### Scenario: Sink containment
- **WHEN** the recent-event sink raises
- **THEN** the facade returns normally and the previously written line remains available

#### Scenario: Written lines feed the recent sink
- **WHEN** a log line is written for an llm_call or warn/error event
- **THEN** it also feeds the observability-local recent sink

#### Scenario: Sink failures stay inside the never-raises boundary
- **WHEN** the recent sink fails
- **THEN** the failure remains inside the never-raises boundary and does not erase or prevent the
  already-written operational line

### Requirement: Facade renders one structured grep-friendly line
Every facade emission MUST be a single line of the form `[level] event | mod.func:line | k=v ... [ | tb: summary]`. The caller segment MUST be derived by the facade from its own call stack, never passed by callers. Events MUST remain stable English snake_case identifiers.

#### Scenario: Context ordering and formatting are deterministic
- **WHEN** the same event is logged twice with the same context
- **THEN** both lines are byte-identical with sorted keys and the truncation and quoting rules applied

#### Scenario: Long multiline player prose
- **WHEN** a context string contains more than 200 characters and embedded newlines
- **THEN** its bounded representation occupies one operational line without blanket prose redaction

#### Scenario: Context rendering rules
- **WHEN** a context mapping is rendered
- **THEN** keys are sorted, None-valued keys are omitted, numeric and boolean values render verbatim,
  strings with spaces are double-quoted, and containers render with repr

#### Scenario: Context values are bounded
- **WHEN** any context value is rendered
- **THEN** it is truncated at 200 characters and embedded newlines are escaped

#### Scenario: Prose allowed, credentials forbidden
- **WHEN** deciding what may enter logs
- **THEN** player prose and prompt content MAY enter logs, while credentials MUST NOT

#### Scenario: Full LLM payloads live in the transcript
- **WHEN** a full LLM payload would otherwise be logged
- **THEN** it lives in the transcript referenced by call_id rather than being duplicated unbounded in
  operational lines

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

A facade call MUST NOT propagate operational (`Exception`) failures —
including caller-frame lookup, context rendering, exception formatting,
Evennia-logger import failure, or logger write failure. Each stage is
guarded: on any internal failure the facade MUST fall back to writing a
best-effort rendered line to stderr via the standard library, and even if
the fallback itself fails the facade call MUST return normally.
`BaseException` (interrupt/signal) is not swallowed.

#### Scenario: Logger failure degrades to stderr

- **WHEN** the Evennia logger raises during a facade call
- **THEN** the caller sees no exception and the line appears on stderr

#### Scenario: Broken context rendering still emits a line

- **WHEN** a context value's `repr` raises
- **THEN** the facade call returns without raising and some line (possibly
  degraded) reaches the logger or stderr

#### Scenario: Unconfigured settings does not emit debug noise

- **WHEN** `log_debug` is called in a process without configured Django
  settings
- **THEN** nothing is written to any sink and nothing is raised

#### Scenario: Django settings unavailability maps to VERBOSE false

- **WHEN** Django settings are unavailable during a facade call
- **THEN** that counts as `VERBOSE` false (debug writes nothing) and never triggers the fallback

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

Each server-startup step in the composition-root catalog MUST log a
`startup_step` info event with `step` and `ms` context on success, and MUST
log through the facade (not a swallowed free-text warning) on failure or
degradation, so the startup log alone answers which subsystems came up
healthy and which degraded.

#### Scenario: Every catalog step logs exactly one success event

- **WHEN** server startup runs with all operations stubbed and a fixed
  clock
- **THEN** the log contains exactly one `startup_step` event per catalog
  step, in catalog order, each with `step` and `ms`

#### Scenario: Degraded startup is visible in the log

- **WHEN** a guardrail layer registration is skipped at server start
- **THEN** a facade event identifies the failed step and the reason in
  context

#### Scenario: A failing fail-loud step still aborts startup

- **WHEN** a fail-loud synchronization step raises
- **THEN** the step logs a facade error with `exc` and the exception keeps
  propagating so the server does not partially boot

#### Scenario: Step failure semantics are preserved by the wrapping

- **WHEN** startup steps are wrapped in facade logging
- **THEN** fail-loud steps keep propagate-on-failure semantics (log with `exc` then re-raise) and
  boot-tolerant steps keep their tolerance but log structured degradation with `step` context

#### Scenario: The catalog is fixed and its order is preserved

- **WHEN** the wrapping is applied
- **THEN** the catalog is the ordered list of startup operations named in the change design, and
  wrapping MUST NOT re-order steps

#### Scenario: Startup-order guard tests migrate

- **WHEN** this change lands
- **THEN** existing startup-order guard tests are migrated to behavioral assertions in the same
  change

### Requirement: LLM and narrative diagnostic correlation
llm_call, llm_call_retry, and llm_cached_tokens_reported SHALL include the guarded call_id. Failures before a guarded call exists SHALL not fabricate an identifier.

#### Scenario: Letter and dream failures explainable
- **WHEN** guarded generation fails for a letter reply or dream input
- **THEN** the operational event includes bounded body or player input and the actual call_id that retrieves the transcript

#### Scenario: Letter command and cached usage
- **WHEN** a letter command begins or provider cached-token usage is reported
- **THEN** cmd_in contains bounded args rather than args_count and cached usage carries its guarded call_id

#### Scenario: Logging does not widen narrative access
- **WHEN** an actor attempts private memory, recall, or thread access previously denied
- **THEN** the same denial remains in force despite prose being permitted in logs

#### Scenario: Letter command records truncated args
- **WHEN** the letter command's cmd_in event is logged
- **THEN** it records truncated args rather than args_count

#### Scenario: Correspondence events carry the letter body
- **WHEN** correspondence_reply_captured or correspondence_reply_failed is logged
- **THEN** the event carries the letter body

#### Scenario: Generation-failure events carry call_id and input
- **WHEN** correspondence_reply_failed or dream_surface_generation_failed is logged and generation was
  attempted
- **THEN** the event carries call_id, and dream failures additionally carry player input

#### Scenario: Full prompts stay in the transcript
- **WHEN** a failure event would need the full prompt
- **THEN** it is retrieved through the transcript, not duplicated into the failure event

#### Scenario: Logging stays on named facade imports
- **WHEN** game-code operational logging is written
- **THEN** it continues through named facade imports with caller-binding patches in tests

#### Scenario: Narrative boundaries are untouched
- **WHEN** this logging change lands
- **THEN** private visibility, PRIVATE_AUTHORING_CATEGORIES, memory/recall/thread access controls and
  all in-world knowledge boundaries remain unchanged
