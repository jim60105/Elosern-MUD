## Purpose

Defines the pre-execution guard that inspects Bash-tool invocations of `evennia test`, counts discovered tests through a count-only discovery run, and blocks any invocation whose discovered test count exceeds the configured maximum, directing the caller to run a focused test instead.

## ADDED Requirements

### Requirement: Guard intercepts Evennia test commands before execution
The guard SHALL register a pre-execution `tool_call` handler that inspects every Bash-tool invocation whose command mentions `evennia test`. Invocations of other tools, and Bash commands that do not mention `evennia test`, SHALL pass through untouched. A matching invocation SHALL NOT execute until the guard has either allowed or blocked it.

#### Scenario: Non-test commands are ignored
- **WHEN** the Bash tool is called with a command that contains no `evennia test` text (e.g. `uv run --locked evennia start`)
- **THEN** the guard returns no decision and the command runs normally with no discovery subprocess

#### Scenario: Test commands are intercepted before running
- **WHEN** the Bash tool is called with `evennia test world.tests`
- **THEN** the guard performs count-only discovery first and only allows the original command to run after the count is known to be within the limit

### Requirement: Recognized invocation forms
The guard SHALL treat a command as a supported Evennia test invocation when, after splitting on top-level `&&` only, the final segment starts with `evennia test` optionally preceded by `uv run ` or `poetry run ` (zero or more flag tokens such as `--locked` allowed between `run` and `evennia`), and every earlier segment starts with `cd`. Commands in the supported grammar — `evennia test ...`, `uv run evennia test ...`, `uv run --locked evennia test ...`, `poetry run evennia test ...`, `cd foo && evennia test ...`, `cd projects && cd mygame && evennia test ...` (single line) — SHALL proceed to count-only discovery, with discovery wrapped by the same runner prefix as the original command.

#### Scenario: Wrapped runner prefixes are recognized
- **WHEN** the command is `uv run evennia test world.tests` or `poetry run evennia test world.tests`
- **THEN** the guard treats it as an Evennia test invocation and counts before allowing

#### Scenario: Runner flags are recognized
- **WHEN** the command is `uv run --locked evennia test world.tests` (the repository's canonical invocation)
- **THEN** the guard treats it as a supported Evennia test invocation and counts before allowing, running discovery with the same `uv run --locked` wrapper

#### Scenario: cd prefixes are recognized
- **WHEN** the command is `cd mygame && evennia test world.tests`
- **THEN** the guard counts discovery relative to the resulting working directory and allows or blocks the original command as a whole

### Requirement: Count-only discovery without executing tests
For a supported invocation, the guard SHALL run a count-only discovery by re-invoking the same command with `--testrunner=omp_evennia_count_runner.CountOnlyRunner` substituted for `evennia test`, executed as a direct subprocess (not through the Bash tool, so it does not re-enter the guard). The count runner SHALL call `setup_test_environment()` before `build_suite()` and `countTestCases()`, SHALL NOT create or modify databases, and SHALL NOT execute any test method. Discovery SHALL run under the same environment and working directory as the original Bash call, preserving caller-supplied environment entries and injecting the extension directory into `PYTHONPATH` so the runner module is importable.

#### Scenario: Discovery sets up the Evennia test environment
- **WHEN** count-only discovery runs against an Evennia project whose configured test runner initializes the Evennia environment during `setup_test_environment()`
- **THEN** discovery performs that same setup before building the suite, so the discovered count matches what the real `evennia test` would collect

#### Scenario: No tests execute during counting
- **WHEN** count-only discovery completes successfully
- **THEN** no database is created, no test method has run, and only the count marker plus runner diagnostics have been produced

#### Scenario: Caller environment is preserved
- **WHEN** the original Bash call supplies environment overrides such as `MUD_TEST_SETTINGS`
- **THEN** the discovery subprocess observes the same values

### Requirement: Discovery count marker protocol
The count runner SHALL emit the discovered count as `__OMP_EVENNIA_TEST_COUNT_V1__=<n>` on its output, and the guard SHALL read the count from the last such marker in the combined output. A missing marker, or a value that is not a non-negative safe integer, SHALL be treated as a failed discovery and block the original command.

#### Scenario: Marker is parsed from the final match
- **WHEN** discovery output contains multiple marker lines
- **THEN** the guard uses the last `__OMP_EVENNIA_TEST_COUNT_V1__=<n>` occurrence as the count

#### Scenario: Missing marker blocks
- **WHEN** the discovery process exits successfully but its output contains no count marker
- **THEN** the guard blocks the original command and says discovery could not determine the count

### Requirement: Allow at or below the maximum
When discovery reports a count of at most `MAX_TESTS` (100) — including zero — the guard SHALL allow the original Bash command to run unchanged and SHALL surface the count to the user interface when interactive (e.g. `Evennia test guard: 42/100 tests — allowed`).

#### Scenario: Focused suite is allowed
- **WHEN** discovery reports 42 tests for `evennia test world.tests.TestSomething`
- **THEN** the original command executes normally and the UI notes the count

### Requirement: Block above the maximum with Run Focus Test guidance
When discovery reports more than 100 tests, the guard SHALL block the original command and return a reason that states the discovered count and the maximum, instructs the caller to Run Focus Test, gives progressively narrowed test-label examples (package, test class, test method), and tells the caller not to retry the broad command.

#### Scenario: Broad suite is blocked
- **WHEN** `evennia test` (no label) discovers 480 tests
- **THEN** the original command does not run and the reason contains the count (480), the maximum (100), the phrase "Run Focus Test", and narrowed-label examples

### Requirement: Fail-closed policy for unsupported shell composition
The guard SHALL NOT attempt to reason about shell semantics beyond the supported grammar. Any Bash command that mentions `evennia test` but cannot be proven to be a single supported test invocation SHALL be blocked with a reason explaining the unsupported construct and a pointer to a standalone supported focused-test command. This includes at minimum: `;`, `|`, `<`, `>` operators; multi-line commands; background `&`; command substitution (backtick or `$(`, including inside double quotes); unterminated quotes, trailing escapes, or empty `&&` segments; `evennia test` not being the final `&&` segment (e.g. `evennia test && do-something`); non-`cd` prefix segments (e.g. `foo && evennia test`); inline environment-assignment prefixes (e.g. `MUD_TEST_SETTINGS=1 evennia test ...` — caller environment must be supplied through the Bash tool's `env` input instead); wrapping in another shell (e.g. `bash -lc 'evennia test'`); more than one `evennia test` segment; and a caller-supplied `--testrunner` flag (reserved by the guard). The reason SHALL name the specific unsupported construct rather than reporting a generic wrapper failure where the guard can distinguish one.

#### Scenario: Chained post-command is blocked
- **WHEN** the command is `evennia test world.tests && do-something`
- **THEN** the guard blocks the entire command rather than replaying the trailing segment after a successful count

#### Scenario: Shell wrapping is blocked
- **WHEN** the command is `bash -lc 'evennia test'`
- **THEN** the guard blocks it as an unsupported wrapper instead of letting a bypassing form through

#### Scenario: Inline environment prefix is blocked
- **WHEN** the command is `MUD_TEST_SETTINGS=1 evennia test world.tests`
- **THEN** the guard blocks it and names the environment-assignment prefix as the unsupported construct, pointing the caller to the Bash tool's env input

#### Scenario: Caller-supplied testrunner is rejected
- **WHEN** the command includes `--testrunner=some.OtherRunner` alongside `evennia test`
- **THEN** the guard blocks the command and states that `--testrunner` is reserved by the guard

### Requirement: Discovery failure blocks the command
If the discovery subprocess raises, exceeds its bounded timeout (60 s), or exits with a non-zero code, the guard SHALL block the original command and include the tail of the discovery output in the reason, instructing the caller to fix the discovery error and Run Focus Test with a narrower target. The original test command SHALL never run when its count could not be established.

#### Scenario: Broken settings block the test run
- **WHEN** discovery exits non-zero because settings fail to import
- **THEN** the original `evennia test` command does not run and the reason includes the discovery error output and the fix-then-focus guidance
