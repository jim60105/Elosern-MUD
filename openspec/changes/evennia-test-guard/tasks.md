# Tasks: OMP Evennia Test Guard

Implement exactly per design.md (D1–D8); the reference plan's `index.ts` and `omp_evennia_count_runner.py` listings are the source of truth. No formatters/linters/project-wide suites beyond the checks listed.

## 1. Count-only runner

- [ ] 1.1 Create `.omp/extensions/evennia-test-guard/omp_evennia_count_runner.py` per design D6/D7: resolve base from `settings.TEST_RUNNER` (import-string; fallback `django.test.runner.DiscoverRunner`; defensive fallback to `DiscoverRunner` if configured equals `omp_evennia_count_runner.CountOnlyRunner`); `CountOnlyRunner.run_tests` = `setup_test_environment()` → `build_suite()` → `print(f"{COUNT_MARKER}{count}", flush=True)` with `COUNT_MARKER = "__OMP_EVENNIA_TEST_COUNT_V1__="` → `return 0` → `finally: teardown_test_environment()`. Verify: `cd /var/home/jim60105/repos/MUD && PYTHONPATH=.omp/extensions/evennia-test-guard MUD_TEST_SETTINGS=1 uv run --locked evennia test --testrunner=omp_evennia_count_runner.CountOnlyRunner <narrow-label>` prints exactly one `__OMP_EVENNIA_TEST_COUNT_V1__=<n>` line, exits 0, and no test-execution output (dots/FAIL) appears; note the count for the task 3 checks.

## 2. Extension

- [ ] 2.1 Create `.omp/extensions/evennia-test-guard/index.ts` exporting `default function evenniaTestGuard(pi: ExtensionAPI)` that registers `pi.on("tool_call", ...)`, per design D1/D8: ignore non-`bash` tools and empty commands; dispatch on `analyzeCommand(command)` result: `not-evennia-test` → `return;`, `unsupported` → `{ block: true, reason: blockedBecauseUnsupported(...) }`, `supported` → discovery path. Verify: restart `omp` from repo root; the extension loads with no load error (it registers silently; no config.yml needed).
- [ ] 2.2 Implement `scanShell` + `analyzeCommand` exactly per design D3: top-level `&&` splitting with quote/escape tracking; reject `;` `|` `<` `>` `` ` `` `$(` (also inside `"`), newline/CR, single `&`, empty segments, unterminated quote/escape; require exactly one `EVENNIA_TEST_START` segment as the final segment, `cd`-only prefixes, reject caller `--testrunner`; build `countCommand` by substituting `--testrunner=omp_evennia_count_runner.CountOnlyRunner` per D4. Verify: unit-run the pure functions against the supported/blocked example lists (e.g. a throwaway `node --experimental-strip-types`/`tsx` script asserting classification per example).
- [ ] 2.3 Implement discovery execution per D2/D5: `resolveWorkingDirectory` (session cwd + `~`/`~/`/absolute/relative input cwd), `readEnvironment` (identifier-shaped string keys only), `buildEnvironmentScript` (export lines with single-quote escaping; `PYTHONPATH` = extension dir prepended to Bash-call or process value); run `pi.exec("bash", ["-lc", "set -e\n<exports>\n<countCommand>"], { cwd, timeout: 60_000 })`. Verify: covered behaviorally in 3.x.
- [ ] 2.4 Implement outcome logic per D7/D8: parse last `__OMP_EVENNIA_TEST_COUNT_V1__=(\d+)` from stdout+stderr; block on exec throw, non-zero exit (include tailed output), missing marker, or count not a non-negative safe integer; `count > 100` → `blockedBecauseTooManyTests` (count, max, "Run Focus Test.", label examples, "Do not retry the broad test command."); `count <= 100` → `ctx.ui.notify("Evennia test guard: <n>/100 tests — allowed", "info")` when `ctx.hasUI` and return undefined so the original command runs. Verify: covered in 3.x.

## 3. End-to-end verification (run in a restarted `omp` session from repo root)

- [ ] 3.1 Allow path: ask the agent to run `uv run --locked evennia test <narrow-label>` whose count (from 1.1) is ≤ 100 → observe the guard notify `<n>/100 — allowed` and the tests actually execute once.
- [ ] 3.2 Block path: ask the agent to run the broad `evennia test` (repo root label; count > 100) → observe `{ block: true }` with the too-many-tests reason and no test execution; confirm the reason contains "Run Focus Test" and narrowed examples.
- [ ] 3.3 Fail-closed matrix: run each blocked example from design D3 (`evennia test && true`, `evennia test | tee /tmp/t.log`, `evennia test > /tmp/t.log`, `true && evennia test`, `bash -lc 'evennia test'`, `evennia test --testrunner=x`, multiline variant) → each blocked with its specific unsupported reason and nothing executed.
- [ ] 3.4 Pass-through: `echo evennia-test-check` and a non-test command (e.g. `uv run --locked evennia version`) → no guard interference, no discovery subprocess.
- [ ] 3.5 Discovery-failure path: temporarily break discovery (e.g. request `evennia test nonexistent.package_label`) → command blocked with discovery error tail, never executed.

## 4. Wrap-up

- [ ] 4.1 Confirm no game-code, settings, or test files changed (`git status` shows only `.omp/extensions/evennia-test-guard/`); remove any throwaway verification scripts from 2.2/3.x.
