# Design: OMP Evennia Test Guard

This design faithfully reflects the settled reference implementation plan (user-approved trade-offs). It is prescriptive: implement as written unless the plan is contradicted by harness behavior discovered during implementation.

## Context

- Repo: Evennia 6.1.0 / Python 3.13, uv-managed. Canonical invocation: `uv run --locked evennia test ...`; common flags `MUD_TEST_SETTINGS=1`, `--settings test_settings.py`, `--keepdb`, `--parallel 16`.
- AGENTS.md already mandates: run the smallest focused test label; local commands estimated above 10 minutes are forbidden; full suite only once with `--parallel 16 --noinput`. This guard mechanizes that rule inside the OMP harness rather than relying on agent discipline.
- OMP auto-discovers project extensions under `<cwd>/.omp/extensions/` (one subdirectory containing `index.ts` is loadable without `config.yml`). Discovery is relative to the directory where `omp` is launched → working convention: launch `omp` from the repository root.

## Goals / Non-Goals

**Goals**
- Block Bash-tool `evennia test` invocations whose Django test discovery finds more than 100 tests; require "Run Focus Test" with a narrower label.
- Count via real project discovery (same `TEST_RUNNER` environment) without creating databases or executing tests.
- Fail closed on anything the guard cannot statically prove safe.

**Non-Goals**
- No recursion guard, no config file, no allowlist/bypass mechanism, no DB-touching dry run, no general shell parser, no enforcement outside the Bash tool (manual terminal runs are out of scope).

## Decisions

### D1 — ExtensionAPI extension, not legacy hooks
An `ExtensionAPI` extension registers a `tool_call` (pre-execution) listener. `tool_call` handlers can return `{ block: true, reason }`, which cancels the tool invocation and surfaces the reason to the agent — exactly the required primitive. OMP treats Extensions as the primary interface for new functionality.

Layout:

```text
.omp/
└── extensions/
    └── evennia-test-guard/
        ├── index.ts                      # TypeScript extension
        └── omp_evennia_count_runner.py   # count-only Django runner
```

### D2 — `pi.exec()` for discovery; no recursion guard needed
The count subprocess is launched with `pi.exec("bash", ["-lc", script], { cwd, timeout })`, which starts a subprocess directly through the Extension runtime. It does NOT route through the Bash tool, so the `tool_call` handler is not re-entered; no recursion marker is needed. Timeout: `DISCOVERY_TIMEOUT_MS = 60_000`.

### D3 — Narrow shell grammar, fail-closed
`scanShell()` splits the command on top-level `&&` only, tracking single/double quotes and backslash escapes. While scanning it hard-rejects (each producing a distinct reason):
- command substitution: `` ` `` or `$(` — also inside double quotes (they still execute there);
- multi-line (`\n`/`\r`);
- single `&` (background execution);
- `;`, `|`, `<`, `>` operators;
- empty `&&` segments;
- unterminated quote or trailing escape.

`analyzeCommand()` then classifies:
1. No `evennia test` text anywhere (`/\bevennia[ \t]+test(?:[ \t]|$)/`) → `not-evennia-test` → pass through.
2. Scan failed → `unsupported` → block.
3. Segments matching `^(?:(?:uv|poetry)[ \t]+run(?:[ \t]+--[^ \t]+)*[ \t]+)?evennia[ \t]+test(?:[ \t]|$)` (runner flags such as `--locked` allowed between `run` and `evennia`; see Amendment A1):
   - zero matches but the text exists somewhere (e.g. `bash -lc 'evennia test'`) → block ("wrapped in an unsupported shell command") — fail closed rather than allow an easy bypass;
   - more than one match → block;
   - the match is not the final segment (e.g. `evennia test && do-something`) → block, because after a successful count the guard would otherwise be unable to replay only the test part without also executing trailing commands;
   - any earlier segment not starting with `cd` (`/^cd(?:[ \t]|$)/`) → block (only `cd ... && evennia test ...` prefixes are supported).
   - a test segment starting with an inline environment assignment (`/^[A-Za-z_][A-Za-z0-9_]*=[^ \t]*[ \t]/`, e.g. `MUD_TEST_SETTINGS=1 evennia test ...`) → block with a dedicated reason naming the env-assignment prefix (pass env via the Bash tool's `env` input) rather than the generic wrapper message; still recognized as an Evennia test so it fails closed (see Amendment A1).
4. The test segment already contains `--testrunner` (`(?:^|[ \t])--testrunner(?:=|[ \t]|$)`) → block; the flag is reserved by the guard.

Supported forms:

```bash
evennia test world.tests
uv run evennia test world.tests
uv run --locked evennia test world.tests   # repo-canonical
poetry run evennia test world.tests
cd mygame && evennia test world.tests
cd projects && cd mygame && evennia test world.tests   # single line only
```

Intentionally blocked (fail closed):

```bash
evennia test && do-something
evennia test | tee test.log
evennia test > test.log
foo && evennia test
MUD_TEST_SETTINGS=1 evennia test world.tests   # env via the Bash tool's env input instead
bash -lc 'evennia test'
evennia test --testrunner=some.OtherRunner
```

### D4 — Count command construction
For a supported invocation, the guard rewrites only the test segment: `evennia test` → `evennia test --testrunner=omp_evennia_count_runner.CountOnlyRunner`, re-joins the `cd` prefixes with ` && `, and runs it via a generated script:

```bash
set -e
export KEY='value'   # one per preserved env var
cd mygame && evennia test --testrunner=omp_evennia_count_runner.CountOnlyRunner world.tests
```

The original command is never rewritten for execution — the count run is discovery only; if allowed, the untouched original Bash invocation proceeds (`handler returns undefined`).

### D5 — Environment/cwd preservation
- cwd: `ctx.cwd` with the Bash input's `cwd` resolved (`~`, `~/…`, absolute, relative-to-session-cwd).
- env: only string-valued, identifier-shaped keys from the Bash input's `env` are forwarded as `export KEY='…'` lines (values single-quoted with `'` → `'\''` escaping). `PYTHONPATH` prefers the Bash-call value, else the OMP process `PYTHONPATH`, and the extension directory is prepended so `omp_evennia_count_runner` is importable. This means discovery runs under the same environment as the original call (e.g. `MUD_TEST_SETTINGS=1`).

### D6 — Count-only runner semantics
`CountOnlyRunner` subclasses the configured `TEST_RUNNER` (import-string resolution; defensive fallback to `DiscoverRunner` if someone permanently configures this runner as `TEST_RUNNER`) and overrides `run_tests`:

1. `self.setup_test_environment()` — deliberately performed first: Evennia's default `TEST_RUNNER` is `evennia.server.tests.testrunner.EvenniaTestSuiteRunner`, whose `setup_test_environment()` calls `evennia._init()` and sets `settings.TEST_ENVIRONMENT = True`. Skipping it would make discovery diverge from the real `evennia test` collection.
2. `suite = self.build_suite(test_labels, **kwargs)` — Django converts labels to a `TestSuite` here; everything after this point (test DB setup, system checks, execution) is skipped.
3. `print(f"{COUNT_MARKER}{count}", flush=True)` where `COUNT_MARKER = "__OMP_EVENNIA_TEST_COUNT_V1__="` and `count = suite.countTestCases()`; return `0` (Django expects failure count from `run_tests`).
4. `finally: self.teardown_test_environment()`.

### D7 — Count marker protocol
`__OMP_EVENNIA_TEST_COUNT_V1__=<n>` printed on stdout (captured with stderr). The guard takes the LAST match of `__OMP_EVENNIA_TEST_COUNT_V1__=(\d+)` over combined output (later project logging cannot shadow it with an earlier partial line; versioned tag allows future protocol changes). No match, or a value that is not a non-negative safe integer → block (fail closed).

### D8 — Decision outcomes
- `count ≤ 100` → return `undefined` (allow original); if `ctx.hasUI`, `ctx.ui.notify("Evennia test guard: <n>/100 tests — allowed", "info")`.
- `count > 100` → block with: discovered count, `Maximum allowed: 100 tests.`, the line `Run Focus Test.`, narrowing instructions, examples (`evennia test world.tests`, `…TestSomething`, `…TestSomething.test_specific_behavior`), and "Do not retry the broad test command."
- unsupported shell / discovery exception / non-zero exit / missing or invalid marker → block with a reason naming the cause, the tailed (≤3000 chars) discovery output where available, and guidance to fix the error and Run Focus Test with a standalone supported command (`evennia test <focused-test-label>`, `uv run …`, `poetry run …`, `cd <game-dir> && …`).

### Policy flow

```text
evennia test ...
       │
       ▼
count-only discovery
       │
       ├── 0..100  → allow original command
       │
       ├── >100    → BLOCK → "Run Focus Test."
       │
       └── discovery error / unsupported shell
              → BLOCK (fail closed)
```

## Risks / Trade-offs

- **Amendments to the reference plan's literal listings** (see A1/A2 below): both were reviewed and recorded deliberately; the rest of the plan is implemented verbatim.

- **Static analysis can be fooled in principle** (e.g. `evennia\ttest` variants are covered, but exotic aliasing like `alias` files or `$VENV/bin/evennia test` is treated as unsupported text and fails closed — blocked, not silently allowed). Accepted: fail-closed errs toward visible friction, not silent long runs.
- **Double counting cost**: every allowed `evennia test` pays one bounded (60 s) discovery subprocess. Accepted: discovery dominates even the count run, and it prevents far more expensive wasted full-suite runs.
- **`setup_test_environment()` side effects** (`evennia._init()`): identical to a real test run's first phase, no DB, no server; matches Evennia semantics by design (D6).
- **Only guards the Bash tool within OMP.** Manual terminal use remains governed by AGENTS.md. Out of scope by design.
- **cwd-relative extension discovery**: launching `omp` outside the repo root silently disables the guard. Mitigation: repository-root convention documented (Context) and surfaced in tasks' verification.

## Migration Plan

Purely additive: drop two files under `.omp/extensions/evennia-test-guard/`, restart `omp` from repo root. Rollback = delete the directory.

## Amendments to the reference plan

The reference plan's listings are the implementation source of truth, with these two recorded deviations (rubber-duck review findings, both verified against the plan's own text):

### A1 — `uv run --locked` must be a supported form (grammar amendment)

The plan's `EVENNIA_TEST_START` (`^(?:(?:uv|poetry)[ \t]+run[ \t]+)?evennia[ \t]+test(?:[ \t]|$)`) rejects flag tokens between `run` and `evennia`, which would block this repo's canonical `uv run --locked evennia test ...` — defeating the guard's purpose (it would block the AGENTS.md-prescribed workflow instead of auditing it). Amendment: allow zero or more `--flag` tokens after `run` — `^(?:(?:uv|poetry)[ \t]+run(?:[ \t]+--[^ \t]+)*[ \t]+)?evennia[ \t]+test(?:[ \t]|$)` — and keep the full `uv run --locked ...` wrapper in the count command. Non-`--` tokens between `run` and `evennia` stay unsupported (fail closed). This is within the plan's settled intent ("Extension must work with `uv run evennia test ...` prefix"; canonical form carries `--locked`).

Related: an inline env-assignment prefix (`MUD_TEST_SETTINGS=1 evennia test ...`) is still blocked fail-closed (it is outside the supported grammar) but is given a dedicated reason naming the env-assignment prefix and pointing to the Bash tool's `env` input, instead of the misleading "wrapped in an unsupported shell command" message.

### A2 — Two transcription defects in the plan listings (fix when implementing)

1. `shellQuote` is missing its closing quote: ``return `'${value.replaceAll("'", "'\\''")}`;`` emits `'foo` for `foo`, so every generated `export KEY='…'` line (PYTHONPATH is always injected) leaves an unterminated quote and the discovery script always fails — which would block even the ≤100 allow path. Corrected: ``return `'${value.replaceAll("'", "'\\''")}'`;`` (matching D5's prose).
2. In `scanShell`'s final empty-segment branch, `reason: "invalid empty shell segment";` uses `;` where object-literal syntax requires `,` — a TypeScript SyntaxError if transcribed verbatim. Corrected to `,`.

## Open Questions

None — the reference plan settled all policy decisions (fail-closed set, marker protocol, timeout, MAX_TESTS, runner base-class resolution); the two recorded deviations are A1/A2 above.
