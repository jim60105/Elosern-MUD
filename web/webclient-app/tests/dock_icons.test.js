import { describe, expect, it } from "vitest";
import { glyphPath } from "../components/dock-icons.js";

describe("dock-icons glyph table (the 拿 chip's get glyph)", () => {
  it('glyphPath("get") returns the reference get-icon path', () => {
    expect(glyphPath("get")).toBe(
      "M6 11V7a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v4M4 11h16v9H4z",
    );
  });

  it("still returns the prior unchanged value for an untouched key", () => {
    // The `character` key is not touched by this change (the sibling
    // icon-fix change owns the other keys).
    expect(glyphPath("character")).toBe(
      "M12 2a5 5 0 1 1 0 10 5 5 0 0 1 0-10zm-7 22v-1c0-3.9 3.1-7 7-7s7 3.1 7 7v1h-14z",
    );
  });
});
