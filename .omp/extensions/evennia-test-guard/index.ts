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

const ENV_ASSIGNMENT_PREFIX =
  /^[A-Za-z_][A-Za-z0-9_]*=[^ \t]*[ \t]/;

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
  if (!EVENNIA_TEST_ANYWHERE.test(command)) {
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

  const testIndexes = scan.segments
    .map((segment, index) =>
      EVENNIA_TEST_START.test(segment) ? index : -1,
    )
    .filter((index) => index >= 0);

  if (testIndexes.length === 0) {
    /*
     * A segment that mentions `evennia test` but starts with an inline
     * environment assignment (e.g. `MUD_TEST_SETTINGS=1 evennia test ...`)
     * is outside the supported grammar and stays blocked fail-closed,
     * but naming the real cause is more actionable than the generic
     * wrapper message (design.md Amendment A1).
     */
    for (const segment of scan.segments) {
      if (
        EVENNIA_TEST_ANYWHERE.test(segment) &&
        ENV_ASSIGNMENT_PREFIX.test(segment)
      ) {
        return {
          kind: "unsupported",
          reason:
            "inline environment-assignment prefixes before the Evennia test command are not supported; pass environment values through the Bash tool's env input instead",
        };
      }
    }

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
  if (/(?:^|[ \t])--testrunner(?:=|[ \t]|$)/.test(testCommand)) {
    return {
      kind: "unsupported",
      reason:
        "--testrunner is reserved by the Evennia test guard",
    };
  }

  const countTestCommand = testCommand.replace(
    /\bevennia[ \t]+test\b/,
    `evennia test --testrunner=${COUNT_RUNNER}`,
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
    "",
    "Do not retry the broad test command.",
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
