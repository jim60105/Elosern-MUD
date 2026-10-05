import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";

import { homedir } from "node:os";
import {
  delimiter as pathDelimiter,
  dirname,
  isAbsolute,
  resolve,
} from "node:path";
import { fileURLToPath } from "node:url";

const MAX_TESTS = 100;
const DISCOVERY_TIMEOUT_MS = 60_000;

const COUNT_MARKER = "__OMP_EVENNIA_TEST_COUNT_V1__=";
const COUNT_RUNNER =
  "omp_evennia_count_runner.CountOnlyRunner";

/*
 * Count-only twin for the unittest-family entry points (Amendment A6):
 * lives next to this extension and is importable because PYTHONPATH
 * carries the extension dir during discovery.
 */
const UNITTEST_COUNT_RUNNER =
  "omp_unittest_count_runner";

const EXTENSION_DIR = dirname(fileURLToPath(import.meta.url));

/*
 * Supported test-segment grammar (design.md Amendment A1): an optional
 * `uv run` / `poetry run` wrapper, with zero or more flag tokens such as
 * `--locked` between `run` and `evennia` (the repo-canonical form is
 * `uv run --locked evennia test ...`).
 */
const EVENNIA_TEST_START =
  /^(?:(?:uv|poetry)[ \t]+run(?:[ \t]+--[^ \t]+)*[ \t]+)?evennia[ \t]+test(?:[ \t]|$)/;

const EVENNIA_TEST_ANYWHERE =
  /\bevennia[ \t]+test(?![A-Za-z0-9_])/;

/*
 * Accepted execution prefixes inside a test segment (Amendment A6). They
 * never change WHICH tests run, so the count command keeps them and only
 * swaps the module invocation for the count runner: repeated inline env
 * assignments, one `timeout N`, `nice`/`stdbuf`, the `uv run`/`poetry run`
 * wrapper with its flags, and an optional `coverage run`/`coverage run.pth`
 * with its own flags (the CI-canonical browser-shard form).
 *
 * `-m` and `--testrunner*` are NEVER flag-consumable here: `-m` belongs
 * to the final invocation, and a `--testrunner` smuggled into the prologue
 * must fail closed, like the reserved-flag check on the invocation itself.
 */
const PROLOGUE_PREFIXES: RegExp[] = [
  /^[ \t]*[A-Za-z_][A-Za-z0-9_]*=[^ \t]*[ \t]+/,
  /^[ \t]*timeout[ \t]+(?:-[^ \t]+[ \t]+)*\d+[smhd]?(?:[ \t]+|$)/,
  /^[ \t]*nice(?:[ \t]+-n[ \t]+-?\d+)?[ \t]+/,
  /^[ \t]*stdbuf(?:[ \t]+-[^ \t]+)+[ \t]+/,
  /^[ \t]*(?:uv|poetry)[ \t]+run(?:[ \t]+(?!(?:-m|--testrunner)(?:[ \t=]|$))(?:-[^ \t]+|--[^ \t]+=[^\s]+))*[ \t]+/,
  /^[ \t]*coverage[ \t]+run(?:\.pth)?(?:[ \t]+(?!(?:-m|--testrunner)(?:[ \t=]|$))(?:-[^ \t]+|--[^ \t]+=[^\s]+))*[ \t]+/,
];

/*
 * Non-CLI Evennia test entry points (Amendment A6). Every Evennia suite
 * ultimately runs the stdlib unittest machinery, so the guard policy
 * extends to the sibling drivers:
 *
 *   python -m web.tests.browser.unittest_driver  (browser acceptance)
 *   python -m unittest [discover]                (top-level regression)
 *
 * The driver module is matched anywhere after `-m` (a quoted
 * `python -m 'web.tests...driver'` still executes it); plain `-m unittest`
 * is matched only as a whole argv pair so quoted JSON or script text that
 * merely contains `-m unittest` is not mistaken for an invocation.
 */
const DRIVER_ANYWHERE =
  /(?:^|[ \t])-m[ \t]+(?:[\w.]+[ \t]+)*web\.tests\.browser\.unittest_driver(?![\w./-])/;

const UNITTEST_MODULE_ANYWHERE =
  /(?:^|[ \t])-m[ \t]+unittest(?=$|[ \t])/;

/*
 * Module invocation forms a test segment must END its accepted prologue
 * with (Amendment A6). The `python` lead is optional because the
 * CI-canonical shard form is `coverage run -m web.tests...` with no
 * interpreter token. Matching requires the test module immediately after
 * `-m`, so `-m time -m web.tests...` (an unrelated leading module) is not
 * a recognized segment and fails closed.
 */
const PY_DRIVER_START =
  /^(?:python[23]?(?:[.]\d+)*[ \t]+)?-m[ \t]+web\.tests\.browser\.unittest_driver(?=$|[ \t])/;

const PY_UNITTEST_START =
  /^(?:python[23]?(?:[.]\d+)*[ \t]+)?-m[ \t]+unittest(?=$|[ \t])/;

const TESTRUNNER_FLAG =
  /(?:^|[ \t])--testrunner(?:=|[ \t]|$)/;

/*
 * Quote/backslash-neutralized view of the command, used for DETECTION
 * only. Shell quoting such as `evennia 'test'` still runs the real
 * `evennia test`, so literal-text detection must not be evadable with
 * quotes or escapes. Stripping them is a conservative
 * over-approximation, and the detection gate tests BOTH the raw and the
 * neutralized view (union), so detection is a strict superset of
 * raw-text detection. Classification of the executed text always uses
 * the raw segments.
 *
 * A `$` directly before a quote is stripped first so ANSI-C quoting
 * (`evennia $'test'`) is neutralized too — at argv level `$'test'`
 * tokenizes to the `test` subcommand.
 */
function neutralizeQuoting(command: string): string {
  return command
    .replace(/\$(?=['"])/g, "")
    .replace(/["'\\]/g, "");
}

/*
 * Commands that can only display or search text. A segment led by one of
 * these, whose "evennia test" text lives entirely inside quotes, can never
 * execute an Evennia test, so it is inert and must not trip the guard
 * (e.g. a commit message or grep pattern merely mentioning the words).
 */
const INERT_LEAD_COMMANDS = new Set([
  "git",
  "echo",
  "printf",
  "grep",
  "egrep",
  "fgrep",
  "rg",
  "cat",
  "sort",
  "uniq",
  "wc",
  "head",
  "tail",
  "diff",
  "cmp",
  "comm",
  "stat",
]);

/**
 * Strip every quoted span (and every escape) from a segment, leaving only
 * text the shell would treat as unquoted command structure.
 */
function unquotedView(segment: string): string {
  let out = "";
  let quote: "'" | '"' | null = null;
  let escaped = false;

  for (const ch of segment) {
    if (escaped) {
      escaped = false;
      continue;
    }

    if (quote === "'") {
      if (ch === "'") {
        quote = null;
      }
      continue;
    }

    if (quote === '"') {
      if (ch === "\\") {
        escaped = true;
        continue;
      }
      if (ch === '"') {
        quote = null;
      }
      continue;
    }

    if (ch === "'" || ch === '"') {
      quote = ch;
      continue;
    }

    if (ch === "\\") {
      escaped = true;
      continue;
    }

    out += ch;
  }

  return out;
}

/**
 * Lead word of a segment with inline environment assignments removed,
 * e.g. `FOO=1 git commit -m '...'` leads with `git`.
 */
function leadCommand(unquoted: string): string {
  const tokens = unquoted.trim().split(/[ \t]+/);

  while (
    tokens.length > 0 &&
    /^[A-Za-z_][A-Za-z0-9_]*=/.test(tokens[0])
  ) {
    tokens.shift();
  }

  return tokens[0] ?? "";
}

/*
 * A segment is an inert mention when its unquoted structure (after
 * quote/escape stripping) mentions an Evennia test — so the real text is
 * present — but every actual occurrence of the words sits inside quotes
 * and the segment is led by a display/search command. Detection uses the
 * same raw ∪ neutralized union as the gate itself, so a segment like
 * `echo "evennia" 'test' x` whose neutralized form reads as an unquoted
 * mention stays guarded.
 */
function isInertMentionSegment(segment: string): boolean {
  const unquoted = unquotedView(segment);

  if (
    !EVENNIA_TEST_ANYWHERE.test(segment) &&
    !EVENNIA_TEST_ANYWHERE.test(unquoted)
  ) {
    return false;
  }

  if (
    EVENNIA_TEST_ANYWHERE.test(unquoted) ||
    EVENNIA_TEST_ANYWHERE.test(neutralizeQuoting(unquoted))
  ) {
    return false;
  }

  return INERT_LEAD_COMMANDS.has(leadCommand(unquoted));
}

/*
 * Same inert-mention policy for the unittest-driver entry points: a
 * display/search command whose driver text lives entirely inside quotes
 * (a commit message or grep pattern) can never run the driver, but any
 * unquoted occurrence — e.g. `python -c '... -m web.tests...'` style
 * python leads, which are NOT inert leads — stays guarded.
 */
function isInertDriverMentionSegment(segment: string): boolean {
  const unquoted = unquotedView(segment);

  if (
    !DRIVER_ANYWHERE.test(segment) &&
    !DRIVER_ANYWHERE.test(unquoted) &&
    !DRIVER_ANYWHERE.test(neutralizeQuoting(segment)) &&
    !UNITTEST_MODULE_ANYWHERE.test(segment) &&
    !UNITTEST_MODULE_ANYWHERE.test(unquoted) &&
    !UNITTEST_MODULE_ANYWHERE.test(neutralizeQuoting(segment))
  ) {
    return false;
  }

  /*
   * An occurrence surviving quote-stripping is unquoted command text,
   * hence execution-capable — never inert.
   */
  if (
    DRIVER_ANYWHERE.test(unquoted) ||
    UNITTEST_MODULE_ANYWHERE.test(unquoted)
  ) {
    return false;
  }

  return INERT_LEAD_COMMANDS.has(leadCommand(unquoted));
}

type TestInvocation = {
  kind: "evennia" | "driver" | "unittest";
  /*
   * Byte offset in the ORIGINAL segment where the final invocation body
   * begins, so the count rewrite is anchored to the body start instead
   * of searching the whole segment (a test label argument must never be
   * rewritten by accident).
   */
  bodyStart: number;
};

/*
 * Classify a raw segment: consume the accepted execution prefixes
 * (PROLOGUE_PREFIXES, repeated until none matches), then require the
 * remainder to start with one of the recognized final invocations.
 * Returns the invocation kind plus the prologue boundary, or null when
 * the segment leads with anything else — including an unknown wrapper
 * such as `bash -lc`, which must fail closed.
 */
function parseTestInvocation(
  segment: string,
): TestInvocation | null {
  let rest = segment;
  let progressed = true;

  while (progressed) {
    progressed = false;

    for (const prefix of PROLOGUE_PREFIXES) {
      const match = prefix.exec(rest);

      if (match) {
        rest = rest.slice(match[0].length);
        progressed = true;
      }
    }
  }

  rest = rest.replace(/^[ \t]+/, "");

  const kind = (
    [
      ["evennia", EVENNIA_TEST_START],
      ["driver", PY_DRIVER_START],
      ["unittest", PY_UNITTEST_START],
    ] as const
  ).find(([, pattern]) => pattern.test(rest))?.[0];

  if (kind === undefined) {
    return null;
  }

  return {
    kind,
    bodyStart: segment.length - rest.length,
  };
}

/*
 * Rewrite only the invocation body (from bodyStart) to its count-only
 * twin, anchored to the body's own start so no test-label argument can
 * ever be substituted (Amendment A6).
 */
function rewriteCountInvocation(
  segment: string,
  invocation: TestInvocation,
): string {
  const prologue = segment.slice(0, invocation.bodyStart);
  const body = segment.slice(invocation.bodyStart);

  const bodyPattern =
    invocation.kind === "evennia"
      ? /^evennia[ \t]+test/
      : invocation.kind === "driver"
        ? PY_DRIVER_START
        : PY_UNITTEST_START;

  const moduleMatch = bodyPattern.exec(body);

  if (moduleMatch === null) {
    /*
     * Unreachable: parseTestInvocation just matched this body. Fail
     * closed loudly rather than emit a silently-miscounted command.
     */
    throw new Error("unparseable test invocation body");
  }

  const moduleName =
    invocation.kind === "evennia"
      ? null
      : invocation.kind === "driver"
        ? "web.tests.browser.unittest_driver"
        : "unittest";

  const head =
    moduleName === null
      ? "evennia test"
      : moduleMatch[0].slice(
          0,
          moduleMatch[0].length - moduleName.length,
        ) + UNITTEST_COUNT_RUNNER;

  return (
    prologue +
    head +
    (invocation.kind === "evennia"
      ? ` --testrunner=${COUNT_RUNNER}`
      : "") +
    body.slice(moduleMatch[0].length)
  );
}

type ShellScanResult =
  | {
      ok: true;
      segments: string[];
    }
  | {
      ok: false;
      reason: string;
    };

type CommandAnalysis =
  | {
      kind: "not-evennia-test";
    }
  | {
      kind: "unsupported";
      reason: string;
    }
  | {
      kind: "supported";
      countCommand: string;
    };

/**
 * Split a shell command on top-level `&&`.
 *
 * We intentionally support only a narrow shell grammar:
 *
 *   evennia test ...
 *   uv run evennia test ...
 *   uv run --locked evennia test ...
 *   poetry run evennia test ...
 *   cd foo && evennia test ...
 *   cd foo && uv run evennia test ...
 *
 * Other shell composition around an Evennia test is blocked fail-closed.
 */
function scanShell(command: string): ShellScanResult {
  const segments: string[] = [];

  let start = 0;
  let quote: "'" | '"' | null = null;
  let escaped = false;

  for (let i = 0; i < command.length; i += 1) {
    const ch = command[i];
    const next = command[i + 1];

    if (escaped) {
      escaped = false;
      continue;
    }

    if (quote === "'") {
      if (ch === "'") {
        quote = null;
      }

      continue;
    }

    if (quote === '"') {
      if (ch === "\\") {
        escaped = true;
        continue;
      }

      if (ch === '"') {
        quote = null;
        continue;
      }

      // These execute commands even inside double quotes.
      if (ch === "`" || (ch === "$" && next === "(")) {
        return {
          ok: false,
          reason: "shell command substitution is not supported",
        };
      }

      continue;
    }

    if (ch === "\\") {
      escaped = true;
      continue;
    }

    if (ch === "'" || ch === '"') {
      quote = ch;
      continue;
    }

    if (ch === "`" || (ch === "$" && next === "(")) {
      return {
        ok: false,
        reason: "shell command substitution is not supported",
      };
    }

    if (ch === "\n" || ch === "\r") {
      return {
        ok: false,
        reason: "multi-line shell commands are not supported",
      };
    }

    if (ch === "&") {
      if (next !== "&") {
        return {
          ok: false,
          reason: "background shell execution is not supported",
        };
      }

      const segment = command.slice(start, i).trim();

      if (!segment) {
        return {
          ok: false,
          reason: "invalid empty shell segment",
        };
      }

      segments.push(segment);

      i += 1;
      start = i + 1;
      continue;
    }

    if (
      ch === ";" ||
      ch === "|" ||
      ch === "<" ||
      ch === ">"
    ) {
      return {
        ok: false,
        reason: `shell operator '${ch}' is not supported`,
      };
    }
  }

  if (quote !== null) {
    return {
      ok: false,
      reason: "unterminated shell quote",
    };
  }

  if (escaped) {
    return {
      ok: false,
      reason: "unterminated shell escape",
    };
  }

  const last = command.slice(start).trim();

  if (!last) {
    return {
      ok: false,
      reason: "invalid empty shell segment",
    };
  }

  segments.push(last);

  return {
    ok: true,
    segments,
  };
}

/**
 * Determine whether this is an Evennia test invocation that can be
 * safely inspected.
 *
 * Tests must be the final command. Prefix commands may only be `cd`.
 */
function analyzeCommand(command: string): CommandAnalysis {
  const neutralized = neutralizeQuoting(command);

  if (
    !EVENNIA_TEST_ANYWHERE.test(neutralized) &&
    !EVENNIA_TEST_ANYWHERE.test(command) &&
    !(
      DRIVER_ANYWHERE.test(neutralized) ||
      DRIVER_ANYWHERE.test(command) ||
      UNITTEST_MODULE_ANYWHERE.test(neutralized) ||
      UNITTEST_MODULE_ANYWHERE.test(command)
    )
  ) {
    return {
      kind: "not-evennia-test",
    };
  }

  const scan = scanShell(command);

  if (!scan.ok) {
    return {
      kind: "unsupported",
      reason: scan.reason,
    };
  }

  /*
   * Classify every segment on its RAW text (the count rewrite must be
   * replayable verbatim); the neutralized view is consulted only for the
   * inert-mention and obscuration decisions below.
   */
  const testIndexes = scan.segments
    .map((segment, index) =>
      parseTestInvocation(segment) !== null ? index : -1,
    )
    .filter((index) => index >= 0);

  /*
   * A mention is inert when no segment parses as a test invocation and
   * every segment whose text resembles a test command (raw or
   * neutralized) is either an inert display/search mention of the CLI
   * form or an inert mention of the unittest-driver forms.
   */
  if (
    testIndexes.length === 0 &&
    scan.segments.every(
      (segment) =>
        parseTestInvocation(neutralizeQuoting(segment)) === null,
    ) &&
    scan.segments.every(
      (segment) =>
        !(
          EVENNIA_TEST_ANYWHERE.test(segment) ||
          EVENNIA_TEST_ANYWHERE.test(neutralizeQuoting(segment))
        ) || isInertMentionSegment(segment),
    ) &&
    scan.segments.every(
      (segment) =>
        !(
          DRIVER_ANYWHERE.test(segment) ||
          DRIVER_ANYWHERE.test(neutralizeQuoting(segment)) ||
          UNITTEST_MODULE_ANYWHERE.test(segment) ||
          UNITTEST_MODULE_ANYWHERE.test(neutralizeQuoting(segment))
        ) || isInertDriverMentionSegment(segment),
    )
  ) {
    return {
      kind: "not-evennia-test",
    };
  }

  /*
   * The neutralized view parses as a runnable test command but no raw
   * segment does (e.g. `evennia 'test' world.tests` or
   * `python -m 'web.tests.browser.unittest_driver'`). The real
   * invocation is unambiguous but its quoting cannot be proven
   * replay-safe, so it is blocked fail-closed with a specific reason
   * instead of passing through unguarded.
   */
  if (testIndexes.length === 0) {
    const neutralizedSegments = scanShell(neutralized);

    if (
      neutralizedSegments.ok &&
      neutralizedSegments.segments.some((segment, index) =>
        parseTestInvocation(segment) !== null &&
        index === neutralizedSegments.segments.length - 1,
      )
    ) {
      return {
        kind: "unsupported",
        reason:
          "the Evennia test command is obscured by shell quoting or escapes; run it as a plain standalone command",
      };
    }
  }

  if (testIndexes.length === 0) {
    /*
     * There is text resembling "evennia test", but it is wrapped in
     * another shell construct that this guard can't reason about.
     *
     * Fail closed rather than allowing an easy guard bypass such as:
     *
     *   bash -lc 'evennia test'
     */
    return {
      kind: "unsupported",
      reason:
        "Evennia test is wrapped in an unsupported shell command",
    };
  }

  if (testIndexes.length !== 1) {
    return {
      kind: "unsupported",
      reason:
        "multiple Evennia test commands in one shell invocation are not supported",
    };
  }

  const testIndex = testIndexes[0];

  if (testIndex !== scan.segments.length - 1) {
    return {
      kind: "unsupported",
      reason:
        "Evennia test must be the final shell command",
    };
  }

  for (const prefix of scan.segments.slice(0, testIndex)) {
    if (!/^cd(?:[ \t]|$)/.test(prefix)) {
      return {
        kind: "unsupported",
        reason:
          "only `cd ... && evennia test ...` prefixes are supported",
      };
    }
  }

  const testCommand = scan.segments[testIndex];

  /*
   * Don't permit callers to supply their own runner. The guard owns
   * --testrunner while performing discovery.
   */
  if (
    TESTRUNNER_FLAG.test(testCommand) ||
    TESTRUNNER_FLAG.test(neutralizeQuoting(testCommand))
  ) {
    return {
      kind: "unsupported",
      reason:
        "--testrunner is reserved by the Evennia test guard",
    };
  }

  /*
   * Swap only the final invocation for its count-only twin (Amendment
   * A6); every accepted execution prefix (`cd` segments, inline env
   * assignments, `timeout`, `uv run --locked`, `coverage run`) rides
   * along verbatim, and the extension dir is on PYTHONPATH so plain
   * `python`/`coverage` can import the count module.
   */
  const invocation = parseTestInvocation(testCommand);

  if (invocation === null) {
    return {
      kind: "unsupported",
      reason:
        "Evennia test is wrapped in an unsupported shell command",
    };
  }

  const countTestCommand = rewriteCountInvocation(
    testCommand,
    invocation,
  );

  const countCommand = [
    ...scan.segments.slice(0, testIndex),
    countTestCommand,
  ].join(" && ");

  return {
    kind: "supported",
    countCommand,
  };
}

function shellQuote(value: string): string {
  return `'${value.replaceAll("'", "'\\''")}'`;
}

/**
 * Preserve environment values supplied to the original Bash tool call.
 */
function readEnvironment(
  value: unknown,
): Record<string, string> {
  if (
    value === null ||
    typeof value !== "object" ||
    Array.isArray(value)
  ) {
    return {};
  }

  const result: Record<string, string> = {};

  for (const [key, rawValue] of Object.entries(value)) {
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) {
      continue;
    }

    if (typeof rawValue !== "string") {
      continue;
    }

    result[key] = rawValue;
  }

  return result;
}

function resolveWorkingDirectory(
  sessionCwd: string,
  requestedCwd: unknown,
): string {
  if (typeof requestedCwd !== "string" || !requestedCwd) {
    return sessionCwd;
  }

  if (requestedCwd === "~") {
    return homedir();
  }

  if (requestedCwd.startsWith("~/")) {
    return resolve(
      homedir(),
      requestedCwd.slice(2),
    );
  }

  if (isAbsolute(requestedCwd)) {
    return requestedCwd;
  }

  return resolve(sessionCwd, requestedCwd);
}

function buildEnvironmentScript(
  inputEnvironment: Record<string, string>,
): string {
  const environment = {
    ...inputEnvironment,
  };

  /*
   * Preserve the explicit Bash-tool PYTHONPATH first, otherwise the
   * OMP process PYTHONPATH.
   */
  const existingPythonPath =
    inputEnvironment.PYTHONPATH ??
    process.env.PYTHONPATH ??
    "";

  /*
   * Evennia's launcher overwrites sys.path[1] (the first PYTHONPATH
   * entry) with its own root on import, and CPython de-duplicates
   * PYTHONPATH, so a lone prepended extension dir is destroyed before
   * the count runner is imported. The leading "." absorbs that
   * overwrite (it resolves to the game dir evennia re-adds anyway),
   * keeping the extension dir — and the caller's remaining entries —
   * importable (design.md Amendment A4).
   */
  environment.PYTHONPATH = [
    ".",
    EXTENSION_DIR,
    existingPythonPath,
  ]
    .filter(Boolean)
    .join(pathDelimiter);

  return Object.entries(environment)
    .map(
      ([key, value]) =>
        `export ${key}=${shellQuote(value)}`,
    )
    .join(";\n");
}

function tail(value: string, maxLength = 3000): string {
  if (value.length <= maxLength) {
    return value;
  }

  return `…${value.slice(-maxLength)}`;
}

/*
 * Output capture inside a guarded command is impossible by design: the
 * shell grammar rejects pipes and redirects around a test invocation,
 * because a trailing `; python3 -c ...` trailer hides which output the
 * agent actually depends on. The Bash tool already persists the full
 * output of truncated runs, so point callers at that instead of teaching
 * them a blocked syntax.
 */
const OUTPUT_CAPTURE_GUIDANCE =
  "Do not wrap the test command in pipes, redirects, or `;` trailers " +
  "(they are blocked). Run it standalone; if the tool truncates the " +
  "output, read the complete log from the reported artifact:// path.";

function blockedBecauseTooManyTests(count: number): string {
  return [
    `Evennia test guard blocked this command: ${count} tests were discovered.`,
    `Maximum allowed: ${MAX_TESTS} tests.`,
    "",
    "Run Focus Test.",
    "",
    "Narrow the Evennia test label until discovery finds no more than " +
      `${MAX_TESTS} tests.`,
    "",
    "Examples:",
    "  evennia test world.tests",
    "  evennia test world.tests.TestSomething",
    "  evennia test world.tests.TestSomething.test_specific_behavior",
    "  uv run --locked python -m web.tests.browser.unittest_driver <module>",
    "",
    "Do not retry the broad test command.",
    "",
    OUTPUT_CAPTURE_GUIDANCE,
  ].join("\n");
}

function blockedBecauseUnsupported(reason: string): string {
  return [
    "Evennia test guard blocked this command.",
    "",
    `Reason: ${reason}.`,
    "",
    "Run Focus Test using a standalone supported command:",
    "  evennia test <focused-test-label>",
    "  uv run evennia test <focused-test-label>",
    "  poetry run evennia test <focused-test-label>",
    "  cd <game-dir> && evennia test <focused-test-label>",
    "  cd <game-dir> && UV_PROJECT_ENVIRONMENT=<venv> timeout <n> uv run --locked python -m web.tests.browser.unittest_driver <focused-module>",
    "  uv run --locked python -m unittest <focused.module>",
    "",
    OUTPUT_CAPTURE_GUIDANCE,
    "",
    `The discovered test count must be <= ${MAX_TESTS}.`,
  ].join("\n");
}

export default function evenniaTestGuard(
  pi: ExtensionAPI,
): void {
  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName !== "bash") {
      return;
    }

    const input = event.input as Record<string, unknown>;

    const command =
      typeof input.command === "string"
        ? input.command.trim()
        : "";

    if (!command) {
      return;
    }

    const analysis = analyzeCommand(command);

    if (analysis.kind === "not-evennia-test") {
      return;
    }

    if (analysis.kind === "unsupported") {
      return {
        block: true,
        reason: blockedBecauseUnsupported(
          analysis.reason,
        ),
      };
    }

    const cwd = resolveWorkingDirectory(
      ctx.cwd,
      input.cwd,
    );

    const inputEnvironment = readEnvironment(
      input.env,
    );

    const environmentScript =
      buildEnvironmentScript(inputEnvironment);

    const script = [
      "set -e",
      environmentScript,
      analysis.countCommand,
    ]
      .filter(Boolean)
      .join("\n");

    let result;

    try {
      /*
       * pi.exec() executes a subprocess directly through the Extension
       * runtime. It does NOT invoke the Bash tool, so this doesn't
       * recursively trigger this tool_call handler.
       */
      result = await pi.exec(
        "bash",
        ["-lc", script],
        {
          cwd,
          timeout: DISCOVERY_TIMEOUT_MS,
        },
      );
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : String(error);

      return {
        block: true,
        reason: [
          "Evennia test guard failed while discovering tests.",
          "",
          tail(message),
          "",
          "The test command was blocked because the guard fails closed.",
          "Run Focus Test with a narrower test target after fixing the discovery error.",
        ].join("\n"),
      };
    }

    const combinedOutput = [
      result.stdout,
      result.stderr,
    ].join("\n");

    if (result.code !== 0) {
      return {
        block: true,
        reason: [
          "Evennia test guard could not complete test discovery.",
          `Discovery process exited with code ${result.code}.`,
          "",
          tail(combinedOutput),
          "",
          "The original test command was not executed.",
          "Run Focus Test after fixing the discovery error.",
        ].join("\n"),
      };
    }

    const matches = [
      ...combinedOutput.matchAll(
        new RegExp(
          `${COUNT_MARKER}(\\d+)`,
          "g",
        ),
      ),
    ];

    const lastMatch = matches.at(-1);

    if (!lastMatch) {
      return {
        block: true,
        reason: [
          "Evennia test guard could not determine the discovered test count.",
          "",
          tail(combinedOutput),
          "",
          "The original test command was blocked.",
          "Run Focus Test with a narrower test target.",
        ].join("\n"),
      };
    }

    const count = Number.parseInt(
      lastMatch[1],
      10,
    );

    if (!Number.isSafeInteger(count) || count < 0) {
      return {
        block: true,
        reason:
          "Evennia test guard received an invalid test count and blocked the command.",
      };
    }

    if (count > MAX_TESTS) {
      return {
        block: true,
        reason: blockedBecauseTooManyTests(count),
      };
    }

    if (ctx.hasUI) {
      ctx.ui.notify(
        `Evennia test guard: ${count}/${MAX_TESTS} tests — allowed`,
        "info",
      );
    }

    /*
     * undefined => allow the ORIGINAL Bash tool invocation.
     *
     * The count-only command above was only discovery. The user's
     * original `evennia test ...` now runs normally.
     */
    return;
  });
}
