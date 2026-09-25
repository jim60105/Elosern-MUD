// webclient-typewriter-reading-prefs (task 2.3): the pure reveal lib — reveal
// units, the per-fragment reveal, the map-art snap, the offset/units
// conversions of the re-page anchor, and the auto-advance rules.
import { describe, expect, it } from "vitest";
import {
  TEXT_SPEEDS,
  TEXT_SPEED_CPS,
  autoAdvanceAllowed,
  autoAdvanceDelayMs,
  cpsFor,
  fragmentReveal,
  offsetAtUnits,
  pageUnits,
  snapUnits,
  unitsAtOffset,
} from "../lib/message_reveal.js";

function frag(start, end, extra = {}) {
  return { kind: "out", seq: 1, mapArt: false, first: true, tokens: [], start, end, ...extra };
}

// Two fragments with a dropped-break gap between them: offsets 0..5 then
// 7..10 (offset 5 and 6 were breaks dropped at a page cut).
const GAPPED = { blocks: [frag(0, 5), frag(7, 10, { first: false })], oversize: false };
// A text fragment, a 6-unit map, and a text fragment.
const WITH_MAP = {
  blocks: [frag(0, 3), frag(3, 9, { mapArt: true, kind: "out" }), frag(9, 12)],
  oversize: false,
};

describe("speeds", () => {
  it("names four speeds and the three typing rates", () => {
    expect(TEXT_SPEEDS).toEqual(["slow", "normal", "fast", "instant"]);
    expect(TEXT_SPEED_CPS).toEqual({ slow: 20, normal: 45, fast: 90 });
    expect(cpsFor("normal")).toBe(45);
    expect(cpsFor("instant")).toBe(Infinity);
  });
});

describe("units", () => {
  it("sums fragment lengths, not the page's offset span", () => {
    expect(pageUnits(GAPPED)).toBe(8);
    expect(pageUnits({ blocks: [] })).toBe(0);
    expect(pageUnits(null)).toBe(0);
  });

  it("reveals each fragment in order at 0, mid-fragment, and the end", () => {
    expect(fragmentReveal(GAPPED, 0)).toEqual([0, 0]);
    expect(fragmentReveal(GAPPED, 3)).toEqual([3, 0]);
    expect(fragmentReveal(GAPPED, 5)).toEqual([5, 0]);
    expect(fragmentReveal(GAPPED, 6)).toEqual([5, 1]);
    expect(fragmentReveal(GAPPED, 8)).toEqual([5, 3]);
    expect(fragmentReveal(GAPPED, 99)).toEqual([5, 3]);
  });

  it("snaps a count inside a map fragment to the map's end", () => {
    expect(snapUnits(WITH_MAP, 2)).toBe(2);
    expect(snapUnits(WITH_MAP, 3)).toBe(3);
    expect(snapUnits(WITH_MAP, 4)).toBe(9);
    expect(snapUnits(WITH_MAP, 8)).toBe(9);
    expect(snapUnits(WITH_MAP, 10)).toBe(10);
    expect(snapUnits(WITH_MAP, 40)).toBe(12);
    expect(snapUnits(WITH_MAP, -1)).toBe(0);
  });
});

describe("offset conversions", () => {
  it("maps a count to the offset of the next unit and the end to the page end", () => {
    expect(offsetAtUnits(GAPPED, 0)).toBe(0);
    expect(offsetAtUnits(GAPPED, 4)).toBe(4);
    // The first unit of the second fragment sits after the dropped breaks.
    expect(offsetAtUnits(GAPPED, 5)).toBe(7);
    expect(offsetAtUnits(GAPPED, 7)).toBe(9);
    expect(offsetAtUnits(GAPPED, 8)).toBe(10);
  });

  it("maps an offset back to a page-local count, a gap counting as the next fragment", () => {
    expect(unitsAtOffset(GAPPED, 0)).toBe(0);
    expect(unitsAtOffset(GAPPED, 4)).toBe(4);
    expect(unitsAtOffset(GAPPED, 5)).toBe(5);
    expect(unitsAtOffset(GAPPED, 6)).toBe(5);
    expect(unitsAtOffset(GAPPED, 7)).toBe(5);
    expect(unitsAtOffset(GAPPED, 9)).toBe(7);
    expect(unitsAtOffset(GAPPED, 10)).toBe(8);
    expect(unitsAtOffset(GAPPED, 50)).toBe(8);
    // A page that starts later: an earlier offset counts 0.
    expect(unitsAtOffset({ blocks: [frag(20, 30)] }, 3)).toBe(0);
  });

  it("round-trips every count", () => {
    for (let n = 0; n <= pageUnits(GAPPED); n += 1) {
      expect(unitsAtOffset(GAPPED, offsetAtUnits(GAPPED, n))).toBe(n);
    }
  });
});

describe("auto-advance rules", () => {
  it("waits 1.2s plus 60ms per unit", () => {
    expect(autoAdvanceDelayMs({ blocks: [frag(0, 100)] })).toBe(7200);
    expect(autoAdvanceDelayMs({ blocks: [] })).toBe(1200);
  });

  it("never advances an oversize page or a page that holds map art", () => {
    expect(autoAdvanceAllowed({ blocks: [frag(0, 10)], oversize: false })).toBe(true);
    expect(autoAdvanceAllowed({ blocks: [frag(0, 10)], oversize: true })).toBe(false);
    expect(autoAdvanceAllowed(WITH_MAP)).toBe(false);
    expect(autoAdvanceAllowed(null)).toBe(false);
  });
});
