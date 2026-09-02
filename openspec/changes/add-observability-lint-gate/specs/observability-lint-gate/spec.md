## ADDED Requirements

### Requirement: The lint gate enforces the facade as the sole log writer

`tools.observability_lint` SHALL scan `world/`, `typeclasses/`, `commands/`,
`server/`, and `web/` (excluding any `tests/` directory or `test_*.py` file)
with AST-based rules and exit non-zero on any violation. R1 SHALL reject
every access path to the Evennia logger in scanned files: `Import` or
`ImportFrom` of module `evennia.utils.logger` (any imported name, including
direct function imports such as `log_warn`), `from evennia import logger`,
`from evennia.utils import logger` (with or without alias), and attribute
calls `evennia.logger.*` after `import evennia`. The only permanent
whitelist member is `world/observability/`. Unparseable files SHALL be
reported as violations, never skipped.

#### Scenario: A direct Evennia logger import fails the gate

- **WHEN** a scanned non-test file contains `from evennia import logger`
- **THEN** the check reports an R1 violation naming the file and line and
  exits non-zero

#### Scenario: A direct logger-function import fails the gate

- **WHEN** a scanned non-test file contains
  `from evennia.utils.logger import log_warn`
- **THEN** the check reports an R1 violation for that import

#### Scenario: An unparseable file cannot smuggle past the gate

- **WHEN** a scanned file fails Python parsing
- **THEN** the check reports a violation for that file and exits non-zero

### Requirement: Exception handlers must re-raise, log, or carry a reasoned exemption

R2 SHALL require every `except` body to contain, anywhere in its AST
subtree (recursively, excluding nested function/lambda definitions), a
`raise` (bare re-raise, a new raise, or `raise ... from`), or a facade log
call — or to carry an exemption comment
`# observability: ignore <rule-id>: <reason>` with a non-empty reason,
located on the `except` header line or immediately before the first body
statement (resolved via tokenization, since comments are absent from the
AST). An `except` body that silently swallows an exception without any of
the three SHALL be a violation.

#### Scenario: A bare swallowed exception fails the gate

- **WHEN** a scanned file contains `except Exception:` whose body is only
  `pass`
- **THEN** the check reports an R2 violation at that handler

#### Scenario: A raise nested in a with-block satisfies R2

- **WHEN** a handler's body wraps its `raise` inside a `with` or nested
  `try` statement
- **THEN** the handler is not an R2 violation

#### Scenario: A reasoned exemption passes and is counted

- **WHEN** the same handler carries `# observability: ignore R2: cache-reset
  must never mask the original error` on the `except` header line or
  immediately before its first body statement
- **THEN** the check passes for that handler and the JSON report's exemption
  count includes it

### Requirement: Facade log calls must carry context

R3 SHALL reject any facade call without a `context=` argument (other than a
literal `None`), and SHALL reject `log_error` that provides neither `exc=`
nor a `raise` anywhere in the enclosing handler. The gate validates presence
statically, never the semantic depth of the values. R3 exemptions attach to
the call line (trailing comment or the immediately preceding line).

#### Scenario: A contextless facade call fails the gate

- **WHEN** a scanned file calls `log_warn("some_event")` with no context
- **THEN** the check reports an R3 violation at that call site

### Requirement: The freeze list is a shrink-only transition ratchet

The gate SHALL read `tools/observability_freeze.json`; files named there are
exempt while unmigrated. The list SHALL only shrink: an entry naming a file
that no longer exists, or that no longer has any violation, SHALL itself be
reported as a violation. The final migration batch SHALL drive the list to
empty.

#### Scenario: A zombie freeze entry fails the gate

- **WHEN** a frozen file has been migrated and no longer violates any rule
  but remains listed
- **THEN** the check reports a freeze-list violation for the stale entry and
  exits non-zero

#### Scenario: Migrated files must be removed from the list to pass

- **WHEN** a file with live violations is removed from the freeze list
- **THEN** its violations surface in the report and the check exits non-zero

### Requirement: The gate exposes a deterministic CLI report

The tool SHALL run as `python -m tools.observability_lint check` with an
optional `--json` machine report listing violations and exemption counts,
using only the standard library, and exit `0`/`1` for pass/fail.

#### Scenario: JSON report is stable and machine-readable

- **WHEN** `check --json` runs against a tree with one R2 violation
- **THEN** stdout is valid JSON containing the violation's file, rule id, and
  line, and the process exits 1
