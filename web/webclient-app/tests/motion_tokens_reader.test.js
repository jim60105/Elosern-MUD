// webclient-combat-beat-queue (design D1/D9): the script-side motion-token
// reader. It is the reader C11a's "Presentation timing never gates committed
// state or input" contract promised, and its whole contract is that an
// unusable token reads as 0 — a missing token must never hold anything.
//
// jsdom resolves an unset custom property to "", which is exactly the
// "missing token" case the contract cares about; the parse cases stub
// `getComputedStyle` so a `ms`/`s`/fractional/garbage value can be pinned
// without a real stylesheet.
import { afterEach, describe, expect, it, vi } from "vitest";

import { readMotionMs } from "../lib/motion_tokens.js";

// A root whose one custom property resolves to `value`.
function rootWith(value) {
  vi.stubGlobal("getComputedStyle", () => ({
    getPropertyValue: (name) => (name === "--motion-beat" ? value : ""),
  }));
  return document.documentElement;
}

describe("readMotionMs (webclient-combat-beat-queue design D1)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parses a millisecond token", () => {
    expect(readMotionMs("--motion-beat", rootWith("400ms"))).toBe(400);
  });

  it("parses a second token, including a fractional one", () => {
    expect(readMotionMs("--motion-beat", rootWith("0.4s"))).toBe(400);
    expect(readMotionMs("--motion-beat", rootWith("1s"))).toBe(1000);
  });

  it("parses a value with surrounding whitespace", () => {
    expect(readMotionMs("--motion-beat", rootWith("  400ms\n"))).toBe(400);
  });

  it("reads an empty token as zero", () => {
    // The real jsdom answer for a custom property no stylesheet declared.
    expect(readMotionMs("--motion-beat", rootWith(""))).toBe(0);
    expect(readMotionMs("--motion-beat", rootWith("   "))).toBe(0);
  });

  it("reads an unparsable token as zero, never as Infinity or NaN", () => {
    for (const raw of ["400", "auto", "400ms 0s", "s", "calc(1s)", "0"]) {
      expect(readMotionMs("--motion-beat", rootWith(raw)), raw).toBe(0);
    }
  });

  it("reads zero when there is no document to read from", () => {
    expect(readMotionMs("--motion-beat", null)).toBe(0);
    expect(readMotionMs("--motion-beat", undefined)).toBe(0);
    // No `document` at all (a Node gate): the default root is undefined too.
    vi.stubGlobal("document", undefined);
    expect(readMotionMs("--motion-beat")).toBe(0);
  });

  it("defaults to the document element when no root is given", () => {
    vi.stubGlobal("getComputedStyle", (element) => {
      expect(element).toBe(document.documentElement);
      return { getPropertyValue: () => "400ms" };
    });
    expect(readMotionMs("--motion-beat")).toBe(400);
  });
});
