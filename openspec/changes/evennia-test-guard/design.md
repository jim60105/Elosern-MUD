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
1. No `evennia test` text anywhere — detection runs on the quote/backslash-neutralized command (`/\bevennia[ \t]+test(?![A-Za-z0-9_])/`, corrected per Amendments A3/A5) → `not-evennia-test` → pass through.
2. Scan failed → `unsupported` → block.
3. Segments matching `^(?:(?:uv|poetry)[ \t]+run(?:[ \t]+--[^ \t]+)*[ \t]+)?evennia[ \t]+test(?:[ \t]|$)` (runner flags such as `--locked` allowed between `run` and `evennia`; see Amendment A1) on the raw segment text:
   - zero raw matches but the neutralized scan's final segment matches (e.g. `evennia 'test'`) → block, naming quoting/escapes as obscuring the test command (Amendment A5);
   - zero matches otherwise but the text exists somewhere (e.g. `bash -lc 'evennia test'`) → block ("wrapped in an unsupported shell command") — fail closed rather than allow an easy bypass;
   - more than one match → block;
   - the match is not the final segment (e.g. `evennia test && do-something`) → block, because after a successful count the guard would otherwise be unable to replay only the test part without also executing trailing commands;
   - any earlier segment not starting with `cd` (`/^cd(?:[ \t]|$)/`) → block (only `cd ... && evennia test ...` prefixes are supported).
   - a test segment starting with an inline environment assignment (`/^[A-Za-z_][A-Za-z0-9_]*=[^ \t]*[ \t]/`, e.g. `MUD_TEST_SETTINGS=1 evennia test ...`) → block with a dedicated reason naming the env-assignment prefix (pass env via the Bash tool's `env` input) rather than the generic wrapper message; still recognized as an Evennia test so it fails closed (see Amendment A1).
4. The test segment already contains `--testrunner` (`(?:^|[ \t])--testrunner(?:=|[ \t]|$)`, checked on both the raw and the neutralized segment per Amendment A5) → block; the flag is reserved by the guard.

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
- env: only string-valued, identifier-shaped keys from the Bash input's `env` are forwarded as `export KEY='…'` lines (values single-quoted with `'` → `'\''` escaping). `PYTHONPATH` prefers the Bash-call value, else the OMP process `PYTHONPATH`, and a `.` absorber plus the extension directory are prepended so `omp_evennia_count_runner` is importable (see Amendment A4). This means discovery runs under the same environment as the original call (e.g. `MUD_TEST_SETTINGS=1`).

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

- **Amendments to the reference plan's literal listings** (see A1/A2/A3/A4/A5 below): all were reviewed and recorded deliberately; the rest of the plan is implemented verbatim.

- **Static analysis can be fooled in principle.** `evennia\ttest` and quoted/escaped spellings (`evennia 'test'`, `e''vennia test`, …) are detected and fail closed (Amendment A5). Residual gaps where no literal `evennia test` text exists at all — shell `alias`/function indirection, `$VENV/bin/evennia test` (the `$VENV/bin/` prefix means the literal text never matches detection, so it silently passes through), and `${VAR}` word indirection — are NOT blocked; detection is text-based by design and a general shell parser is a non-goal. Accepted: these require deliberately indirect commands; every plainly spellable invocation (the realistic agent output) is covered.
- **Double counting cost**: every allowed `evennia test` pays one bounded (60 s) discovery subprocess. Accepted: discovery dominates even the count run, and it prevents far more expensive wasted full-suite runs.
- **`setup_test_environment()` side effects** (`evennia._init()`): identical to a real test run's first phase, no DB, no server; matches Evennia semantics by design (D6).
- **Only guards the Bash tool within OMP.** Manual terminal use remains governed by AGENTS.md. Out of scope by design.
- **cwd-relative extension discovery**: launching `omp` outside the repo root silently disables the guard. Mitigation: repository-root convention documented (Context) and surfaced in tasks' verification.

## Migration Plan

Purely additive: drop two files under `.omp/extensions/evennia-test-guard/`, restart `omp` from repo root. Rollback = delete the directory.

## Amendments to the reference plan

The reference plan's listings are the implementation source of truth, with these recorded deviations (rubber-duck review findings A1/A2, plus A3 found during implementation against the delta spec's own scenarios):

### A1 — `uv run --locked` must be a supported form (grammar amendment)

The plan's `EVENNIA_TEST_START` (`^(?:(?:uv|poetry)[ \t]+run[ \t]+)?evennia[ \t]+test(?:[ \t]|$)`) rejects flag tokens between `run` and `evennia`, which would block this repo's canonical `uv run --locked evennia test ...` — defeating the guard's purpose (it would block the AGENTS.md-prescribed workflow instead of auditing it). Amendment: allow zero or more `--flag` tokens after `run` — `^(?:(?:uv|poetry)[ \t]+run(?:[ \t]+--[^ \t]+)*[ \t]+)?evennia[ \t]+test(?:[ \t]|$)` — and keep the full `uv run --locked ...` wrapper in the count command. Non-`--` tokens between `run` and `evennia` stay unsupported (fail closed). This is within the plan's settled intent ("Extension must work with `uv run evennia test ...` prefix"; canonical form carries `--locked`).

Related: an inline env-assignment prefix (`MUD_TEST_SETTINGS=1 evennia test ...`) is still blocked fail-closed (it is outside the supported grammar) but is given a dedicated reason naming the env-assignment prefix and pointing to the Bash tool's `env` input, instead of the misleading "wrapped in an unsupported shell command" message.

### A2 — Two transcription defects in the plan listings (fix when implementing)

1. `shellQuote` is missing its closing quote: ``return `'${value.replaceAll("'", "'\\''")}`;`` emits `'foo` for `foo`, so every generated `export KEY='…'` line (PYTHONPATH is always injected) leaves an unterminated quote and the discovery script always fails — which would block even the ≤100 allow path. Corrected: ``return `'${value.replaceAll("'", "'\\''")}'`;`` (matching D5's prose).
2. In `scanShell`'s final empty-segment branch, `reason: "invalid empty shell segment";` uses `;` where object-literal syntax requires `,` — a TypeScript SyntaxError if transcribed verbatim. Corrected to `,`.

### A3 — Detection regex must fire on quoted test text (fix when implementing)

Discovered during implementation. The plan's `EVENNIA_TEST_ANYWHERE` (`/\bevennia[ \t]+test(?:[ \t]|$)/`) only recognizes `evennia test` when followed by whitespace or end-of-string, so `bash -lc 'evennia test'` (closing quote immediately after `test`) is classified `not-evennia-test` and passes through — contradicting this change's own scenario "Shell wrapping is blocked" (the plan's own D3 blocked-example list even names this command). Corrected detection-only regex: `/\bevennia[ \t]+test(?![A-Za-z0-9_])/` — a strict superset of the original matches (word-character continuations such as `evennia testrunner-config` stay unmatched), keeping the guard fail-closed without changing any policy decision. D3's step-1 regex description is updated accordingly.

### A4 — Evennia's launcher destroys the first PYTHONPATH entry (fix when implementing)

Discovered during implementation. `evennia/server/evennia_launcher.py` executes `sys.path[1] = EVENNIA_ROOT` at import time: `sys.path[1]` is exactly the first PYTHONPATH entry, and CPython de-duplicates PYTHONPATH, so the plan's `PYTHONPATH = EXTENSION_DIR:<existing>` injection is overwritten before Django resolves `--testrunner=omp_evennia_count_runner` — the count subprocess fails with `ModuleNotFoundError: No Module named 'omp_evennia_count_runner'` even though the plain env var is preserved (verified against Evennia 6.1.0: a second PYTHONPATH entry survives, a doubled single entry is de-duplicated away). Corrected D5 injection: `PYTHONPATH = .:<EXTENSION_DIR>:<existing>` — the leading `.` absorbs the launcher's overwrite with a harmless entry (the game dir is inserted at `sys.path[0]` by `init_game_directory` anyway), keeping the extension dir importable. The count-only discovery command therefore needs the absorber when run manually as well.

### A5 — Detection must survive shell quoting/escapes (fix when implementing)

Found by post-implementation review. The plan (and the A3-corrected) detection regexes run on the raw command text, so `evennia 'test'`, `evennia "test"`, `'evennia' test`, `evennia \test`, `e''vennia test` — all of which bash tokenizes into a real `evennia test` invocation (the first, with no label, is the full 8032-test suite) — were classified `not-evennia-test` and passed through completely unguarded, violating spec Requirement 1 ("inspects every Bash-tool invocation whose command mentions `evennia test`"). The `--testrunner` reservation check had the same hole (`--testrunner="x"` evaded it; Django's `store` semantics let the caller's last flag win inside the count subprocess, redirecting "count-only" discovery into a real DB-creating run). Corrected: classification runs on the raw segments, but the detection gate, the quoting-obscured fallback reason, and the `--testrunner` check additionally evaluate a conservative quote/backslash-neutralized view (stripping `"` `'` `\`), which can only route more commands into the fail-closed path, never fewer. Supported commands still execute/replay only the raw segment text.

## Open Questions

None — the reference plan settled all policy decisions (fail-closed set, marker protocol, timeout, MAX_TESTS, runner base-class resolution); the recorded deviations are A1/A2/A3/A4/A5 above.
