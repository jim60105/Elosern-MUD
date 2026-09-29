// webclient-motion-level (design D7): the duration guard.
//
// Every component duration, delay, and travel distance must come from the
// client's motion tokens, so no component may declare a literal time in a
// `transition*` or `animation*` declaration. This is the cheap source-level
// guard that keeps the `reduced` level honest — the `off` level has its own
// `!important` safety rule in `styles/tokens.css`, but `reduced` deliberately
// keeps the short fades and so depends on every declaration being
// token-gated.
//
// It also pins the token vocabulary: the three level blocks must exist and
// each must declare exactly the level-dependent tokens, so a level can never
// silently lose one.
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const APP_ROOT = join(process.cwd(), "web/webclient-app");

// The level-dependent tokens (design D3). `--motion-shift-sm/-lg` and the
// `--ease-*` tokens are level-independent, so they are not in the blocks.
const LEVEL_TOKENS = [
  "--motion-fast",
  "--motion-base",
  "--motion-slow",
  "--motion-beat",
  // The combat beat gestures (webclient-combat-beat-choreography design D1).
  "--motion-beat-step",
  "--motion-beat-hit",
  "--motion-beat-float",
  "--motion-beat-defeat",
  "--motion-pulse",
  "--motion-hp-pulse",
  "--motion-spin",
  "--motion-pending",
  "--motion-trail",
  "--motion-trail-delay",
  "--motion-scene",
  "--motion-portrait",
  "--motion-actor",
  "--motion-panel",
  "--motion-reveal",
  "--motion-clear",
  "--motion-flash",
  "--motion-stagger",
  "--motion-marker-bob",
  "--motion-playback-sweep",
  "--motion-travel",
  "--motion-flash-peak",
];

const MOTION_DECLARATION =
  /(?:^|[;{\s])((?:-webkit-)?(?:transition|animation)(?:-duration|-delay)?)\s*:\s*([^;}]+)/g;

// A time literal: `0.6s`, `120ms`, `.2s`, `1s`, and a negative delay
// `-250ms`. Case-insensitive, so an uppercase `1S` cannot slip through. A
// bare `0` is not a time.
const TIME_LITERAL = /(?<![\w-])[+-]?\d*\.?\d+m?s\b/i;

function scannedFiles() {
  const files = [];
  for (const dir of ["components", "styles"]) {
    const walk = (relative) => {
      for (const entry of readdirSync(join(APP_ROOT, relative), { withFileTypes: true })) {
        const path = join(relative, entry.name);
        if (entry.isDirectory()) {
          walk(path);
        } else if (/\.(vue|css)$/.test(entry.name)) {
          files.push(path);
        }
      }
    };
    walk(dir);
  }
  files.push("AppClient.vue");
  return files.sort();
}

// Blank out comments while preserving every offset, so a line number stays
// true and a comment that mentions a duration cannot trip the guard.
function withoutComments(source) {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, (match) => match.replace(/[^\n]/g, " "))
    .replace(/(^|[^:])\/\/[^\n]*/g, (match, prefix) => prefix + " ".repeat(match.length - prefix.length));
}

function lineAt(source, index) {
  let line = 1;
  for (let i = 0; i < index; i += 1) {
    if (source[i] === "\n") {
      line += 1;
    }
  }
  return line;
}

// The rule bodies that may legitimately carry a literal duration in
// `styles/tokens.css`: the `:root` token definitions and the `off` level's
// `0s !important` rule. Identified by selector, never by line number.
function exemptRanges(source) {
  const ranges = [];
  const blockRe = /([^{}]*)\{([^{}]*)\}/g;
  let match;
  while ((match = blockRe.exec(source)) !== null) {
    const selector = match[1].trim().replace(/\s+/g, " ");
    const isTokenDefinition = selector === ":root";
    const isOffSafetyRule =
      selector.startsWith(':root[data-motion="off"] *') &&
      /(transition-duration|animation-duration)\s*:\s*0s/.test(match[2]);
    if (isTokenDefinition || isOffSafetyRule) {
      const start = match.index + match[1].length;
      ranges.push([start, start + match[2].length]);
    }
  }
  return ranges;
}

function levelBlockBody(source, pattern) {
  const match = source.match(pattern);
  return match ? match[1] : null;
}

describe("motion tokens (webclient-motion-level)", () => {
  it("no component or stylesheet declares a literal transition/animation duration", () => {
    const offenders = [];
    for (const file of scannedFiles()) {
      const raw = readFileSync(join(APP_ROOT, file), "utf-8");
      const source = withoutComments(raw);
      const exempt = file === "styles/tokens.css" ? exemptRanges(source) : [];
      MOTION_DECLARATION.lastIndex = 0;
      let match;
      while ((match = MOTION_DECLARATION.exec(source)) !== null) {
        const value = match[2];
        if (!TIME_LITERAL.test(value)) {
          continue;
        }
        const index = match.index + match[0].indexOf(match[1]);
        if (exempt.some(([start, end]) => index >= start && index <= end)) {
          continue;
        }
        offenders.push(`${file}:${lineAt(source, index)}: ${match[1]}: ${value.trim()}`);
      }
    }
    expect(
      offenders,
      "every transition/animation duration and delay must come from a --motion-* token",
    ).toEqual([]);
  });

  it("styles/tokens.css defines the three level blocks with the full vocabulary", () => {
    const tokens = readFileSync(join(APP_ROOT, "styles/tokens.css"), "utf-8");
    const bodies = {
      reduced: levelBlockBody(tokens, /:root\[data-motion="reduced"\]\s*\{([^}]*)\}/),
      off: levelBlockBody(tokens, /:root\[data-motion="off"\]\s*\{([^}]*)\}/),
      fallback: levelBlockBody(
        tokens,
        /@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{\s*:root:not\(\[data-motion\]\)\s*\{([^}]*)\}/,
      ),
    };
    for (const [level, body] of Object.entries(bodies)) {
      expect(body, `the ${level} level block must exist`).not.toBeNull();
      const declared = (body.match(/--motion-[a-z-]+(?=\s*:)/g) || []).sort();
      expect(declared, `the ${level} level block declares exactly the level tokens`).toEqual(
        [...LEVEL_TOKENS].sort(),
      );
    }
    // The fallback is gated on the attribute being absent: without `:not()`
    // the OS preference would override an explicit `full` or `off`.
    expect(tokens).toContain("@media (prefers-reduced-motion: reduce) {");
    expect(tokens).toContain(":root:not([data-motion]) {");
  });

  it("the off level forces every duration and delay to 0s on every element", () => {
    const tokens = readFileSync(join(APP_ROOT, "styles/tokens.css"), "utf-8");
    const rule = tokens.match(/:root\[data-motion="off"\] \*,[\s\S]*?\{([^}]*)\}/);
    expect(rule, "the off level's universal safety rule must exist").not.toBeNull();
    for (const declaration of [
      "animation-delay: 0s !important",
      "animation-duration: 0s !important",
      "transition-delay: 0s !important",
      "transition-duration: 0s !important",
    ]) {
      expect(rule[1]).toContain(declaration);
    }
    // `reduced` must NOT carry the universal rule: it would kill the
    // permitted short fades.
    const reducedBlock = tokens.match(/:root\[data-motion="reduced"\][\s\S]*?(?=:root\[data-motion="off"\])/);
    expect(reducedBlock[0]).not.toContain("!important");
  });

  it("the root vocabulary carries the travel multiplier, distances, and easings", () => {
    const tokens = readFileSync(join(APP_ROOT, "styles/tokens.css"), "utf-8");
    const root = tokens.match(/:root\s*\{([\s\S]*?)\n\}/)[1];
    for (const declaration of [
      // The combat beat pause (webclient-combat-beat-queue design D2): only
      // the script reads it, so it is not a transition duration. Its `full`
      // and `reduced` value is 400ms and its `off` value is 0ms.
      "--motion-beat: 400ms;",
      // The combat beat gestures and distances (webclient-combat-beat-
      // choreography design D1) and the trail's 300ms delay (AVG stage
      // design §10.2).
      "--motion-beat-step: 240ms;",
      "--motion-beat-hit: 180ms;",
      "--motion-beat-float: 600ms;",
      "--motion-beat-defeat: 350ms;",
      "--motion-beat-lunge: 24px;",
      "--motion-beat-shake: 6px;",
      "--motion-beat-rise: 48px;",
      "--motion-trail-delay: 300ms;",
      "--motion-travel: 1;",
      "--motion-shift-sm: 12px;",
      "--motion-shift-lg: 32px;",
      "--ease-standard: cubic-bezier(0.2, 0.8, 0.2, 1);",
      "--ease-enter: cubic-bezier(0, 0, 0.2, 1);",
      "--ease-exit: cubic-bezier(0.4, 0, 1, 1);",
    ]) {
      expect(root).toContain(declaration);
    }
    // The travel multiplier is what lets `reduced` keep a fade and drop a move.
    expect(tokens).toContain("transform: translateY(calc(6px * var(--motion-travel)))");
  });
});
