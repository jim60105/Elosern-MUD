#!/usr/bin/env node
/*
 * Claude Code PreToolUse adapter for the Evennia test guard.
 *
 * The guard policy lives in `.omp/extensions/evennia-test-guard/index.ts`
 * (an Oh My Pi extension). To keep a single source of truth, this hook loads
 * that module unchanged and drives it through a minimal fake ExtensionAPI:
 * `pi.on("tool_call", ...)` is captured and `pi.exec()` is backed by a real
 * subprocess with a hard timeout. Node >= 24 strips the TypeScript natively.
 *
 * Claude Code treats a hook that crashes (exit != 0/2) or times out as
 * NON-blocking, so every failure path here exits 2 explicitly: this adapter
 * fails closed, like the guard itself.
 */
import { spawn } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HOOK_DIR = dirname(fileURLToPath(import.meta.url));
const GUARD_ENTRY = resolve(
  HOOK_DIR,
  "../../.omp/extensions/evennia-test-guard/index.ts",
);

function deny(reason) {
  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: reason,
      },
    }),
  );
  process.exit(0);
}

function failClosed(message) {
  process.stderr.write(`Evennia test guard hook failed closed: ${message}\n`);
  process.exit(2);
}

function readStdin() {
  return new Promise((resolveInput, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => (data += chunk));
    process.stdin.on("end", () => resolveInput(data));
    process.stdin.on("error", reject);
  });
}

function exec(command, args, { cwd, timeout }) {
  return new Promise((resolveExec, reject) => {
    const child = spawn(command, args, { cwd, stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    let timedOut = false;

    const timer = setTimeout(() => {
      timedOut = true;
      child.kill("SIGKILL");
    }, timeout);

    child.stdout.on("data", (chunk) => (stdout += chunk));
    child.stderr.on("data", (chunk) => (stderr += chunk));
    child.on("error", (error) => {
      clearTimeout(timer);
      reject(error);
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      if (timedOut) {
        reject(new Error(`TimeoutError: discovery timed out after ${timeout}ms`));
        return;
      }
      resolveExec({ stdout, stderr, code: code ?? 1 });
    });
  });
}

async function main() {
  const event = JSON.parse(await readStdin());

  if (event.tool_name !== "Bash") {
    return;
  }

  const notifications = [];
  let handler;
  const guard = await import(pathToFileURL(GUARD_ENTRY).href);

  guard.default({
    on(name, fn) {
      if (name === "tool_call") {
        handler = fn;
      }
    },
    exec,
  });

  if (typeof handler !== "function") {
    failClosed("guard module did not register a tool_call handler");
  }

  const outcome = await handler(
    { toolName: "bash", input: event.tool_input ?? {} },
    {
      cwd: event.cwd ?? process.cwd(),
      hasUI: true,
      ui: { notify: (message) => notifications.push(message) },
    },
  );

  if (outcome?.block) {
    deny(outcome.reason ?? "Evennia test guard blocked this command.");
  }

  if (notifications.length > 0) {
    // No permissionDecision: normal permission rules still apply.
    process.stdout.write(JSON.stringify({ systemMessage: notifications.join("\n") }));
  }
}

// Hard watchdog just above the guard's own 60 s discovery timeout.
setTimeout(() => failClosed("watchdog timeout"), 80_000).unref();

main().then(
  () => process.exit(0),
  (error) => failClosed(error instanceof Error ? error.message : String(error)),
);
